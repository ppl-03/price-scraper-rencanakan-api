from django.db import connection, transaction
from django.utils import timezone

class GemilangDatabaseService:
    def _validate_data(self, data):
        if not data:
            return False
        for item in data:
            if not all(k in item for k in ("name", "price", "url", "unit")):
                return False
            if not isinstance(item["price"], int) or item["price"] < 0:
                return False
        return True
    
    def save(self, data):
        if not self._validate_data(data):
            return False

        now = timezone.now()

        sql = """
            INSERT INTO gemilang_products
                (name, price, url, unit, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        params_list = [
            (it["name"], it["price"], it["url"], it["unit"], now, now)
            for it in data
        ]

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.executemany(sql, params_list)

        return True
    
    def save_with_price_update(self, data):
        if not self._validate_data(data):
            return {"success": False, "updated": 0, "inserted": 0, "anomalies": []}

        now = timezone.now()
        updated_count = 0
        inserted_count = 0
        anomalies = []

        with transaction.atomic():
            with connection.cursor() as cursor:
                for item in data:
                    cursor.execute(
                        "SELECT id, price FROM gemilang_products WHERE name = %s AND url = %s AND unit = %s",
                        (item["name"], item["url"], item["unit"])
                    )
                    existing = cursor.fetchone()

                    if existing:
                        existing_id, existing_price = existing
                        new_price = item["price"]

                        if existing_price != new_price:
                            price_diff_pct = ((new_price - existing_price) / existing_price * 100) if existing_price > 0 else 0
                            
                            if abs(price_diff_pct) >= 15:
                                anomalies.append({
                                    "name": item["name"],
                                    "url": item["url"],
                                    "unit": item["unit"],
                                    "old_price": existing_price,
                                    "new_price": new_price,
                                    "change_percent": round(price_diff_pct, 2)
                                })

                            cursor.execute(
                                "UPDATE gemilang_products SET price = %s, updated_at = %s WHERE id = %s",
                                (new_price, now, existing_id)
                            )
                            updated_count += 1
                    else:
                        cursor.execute(
                            "INSERT INTO gemilang_products (name, price, url, unit, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                            (item["name"], item["price"], item["url"], item["unit"], now, now)
                        )
                        inserted_count += 1

        return {
            "success": True,
            "updated": updated_count,
            "inserted": inserted_count,
            "anomalies": anomalies
        }
