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
            return {"success": False, "product_ids": []}

        now = timezone.now()
        product_ids = []

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
                for params in params_list:
                    cursor.execute(sql, params)
                    product_ids.append(cursor.lastrowid)

        return {"success": True, "product_ids": product_ids}
    
    def _check_anomaly(self, item, existing_price, new_price):
        if existing_price == 0:
            return None
        price_diff_pct = ((new_price - existing_price) / existing_price) * 100
        if abs(price_diff_pct) >= 15:
            return {
                "name": item["name"],
                "url": item["url"],
                "unit": item["unit"],
                "old_price": existing_price,
                "new_price": new_price,
                "change_percent": round(price_diff_pct, 2)
            }
        return None

    def _update_existing_product(self, cursor, item, existing_id, existing_price, now, anomalies):
        new_price = item["price"]
        if existing_price != new_price:
            anomaly = self._check_anomaly(item, existing_price, new_price)
            if anomaly:
                anomalies.append(anomaly)
            cursor.execute(
                "UPDATE gemilang_products SET price = %s, updated_at = %s WHERE id = %s",
                (new_price, now, existing_id)
            )
            return 1
        return 0

    def _insert_new_product(self, cursor, item, now):
        cursor.execute(
            "INSERT INTO gemilang_products (name, price, url, unit, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (item["name"], item["price"], item["url"], item["unit"], now, now)
        )
        return cursor.lastrowid

    def save_with_price_update(self, data):
        if not self._validate_data(data):
            return {"success": False, "updated": 0, "inserted": 0, "anomalies": [], "product_ids": []}

        now = timezone.now()
        updated_count = 0
        inserted_count = 0
        anomalies = []
        product_ids = []

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
                        if self._update_existing_product(cursor, item, existing_id, existing_price, now, anomalies):
                            updated_count += 1
                        product_ids.append(existing_id)
                    else:
                        new_id = self._insert_new_product(cursor, item, now)
                        if new_id:
                            inserted_count += 1
                            product_ids.append(new_id)

        return {
            "success": True,
            "updated": updated_count,
            "inserted": inserted_count,
            "anomalies": anomalies,
            "product_ids": product_ids
        }
