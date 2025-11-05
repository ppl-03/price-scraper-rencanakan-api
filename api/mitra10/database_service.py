from django.db import connection, transaction
from django.utils import timezone

class Mitra10DatabaseService:
    """Handles Mitra10 product database operations with validation and anomaly tracking."""

    # =========================
    # Validation
    # =========================
    def _validate_data(self, data):
        """Ensure all required keys exist and price is a valid non-negative integer."""
        if not data:
            return False
        required_keys = {"name", "price", "url", "unit"}
        for item in data:
            if not required_keys.issubset(item.keys()):
                return False
            if not isinstance(item["price"], int) or item["price"] < 0:
                return False
        return True

    # =========================
    # Core Query Helpers
    # =========================
    def _execute_many(self, sql, params_list):
        """Execute multiple insert queries in a single transaction."""
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.executemany(sql, params_list)

    def _execute_single(self, sql, params):
        """Execute a single SQL statement and return results if any."""
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    # =========================
    # Insert / Update Logic
    # =========================
    def _insert_product(self, cursor, item, now):
        cursor.execute(
            """
            INSERT INTO mitra10_products (name, price, url, unit, category, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (item["name"], item["price"], item["url"], item["unit"], item.get("category"), now, now),
        )
        return 1

    def _update_product(self, cursor, item, existing_id, existing_price, now, anomalies):
        new_price = item["price"]
        if existing_price != new_price:
            anomaly = self._detect_anomaly(item, existing_price, new_price)
            if anomaly:
                anomalies.append(anomaly)
            cursor.execute(
                """
                UPDATE mitra10_products
                SET price = %s, category = %s, updated_at = %s
                WHERE id = %s
                """,
                (new_price, item.get("category"), now, existing_id),
            )
            return 1
        return 0

    # =========================
    # Anomaly Detection
    # =========================
    def _detect_anomaly(self, item, old_price, new_price):
        if old_price == 0:
            return None
        change_percent = ((new_price - old_price) / old_price) * 100
        if abs(change_percent) >= 15:
            return {
                "name": item["name"],
                "url": item["url"],
                "unit": item["unit"],
                "old_price": old_price,
                "new_price": new_price,
                "change_percent": round(change_percent, 2),
            }
        return None

    # =========================
    # Public Methods
    # =========================
    def save(self, data):
        """Insert multiple Mitra10 products at once."""
        if not self._validate_data(data):
            return False

        now = timezone.now()
        sql = """
            INSERT INTO mitra10_products (name, price, url, unit, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params_list = [(d["name"], d["price"], d["url"], d["unit"], now, now) for d in data]
        self._execute_many(sql, params_list)
        return True

    def save_with_price_update(self, data):
        """Insert or update products, tracking anomalies when price changes ≥15%."""
        if not self._validate_data(data):
            return {"success": False, "updated": 0, "inserted": 0, "anomalies": []}

        now = timezone.now()
        updated, inserted, anomalies = 0, 0, []

        with transaction.atomic(), connection.cursor() as cursor:
            for item in data:
                result = self._execute_single(
                    "SELECT id, price FROM mitra10_products WHERE name = %s AND url = %s AND unit = %s",
                    (item["name"], item["url"], item["unit"]),
                )
                if result:
                    existing_id, existing_price = result
                    updated += self._update_product(cursor, item, existing_id, existing_price, now, anomalies)
                else:
                    inserted += self._insert_product(cursor, item, now)

        return {"success": True, "updated": updated, "inserted": inserted, "anomalies": anomalies}
