from django.db import connection, transaction
from django.utils import timezone
from db_pricing.anomaly_service import PriceAnomalyService
from .security import SecurityDesignPatterns
import logging

logger = logging.getLogger(__name__)

class Mitra10DatabaseService:
    def _validate_data(self, data):
        """
        Ensure all required keys exist and validate business logic.
        Implements OWASP A04:2021 - Insecure Design Prevention.
        """
        if not data:
            return False, "No data provided"
        
        required_keys = {"name", "price", "url", "unit"}
        for item in data:
            # Check required fields
            if not required_keys.issubset(item.keys()):
                missing_keys = required_keys - item.keys()
                return False, f"Product missing required fields: {', '.join(missing_keys)}"
            
            # Type validation
            if not isinstance(item["price"], (int, float)):
                return False, f"Price for '{item.get('name', 'unknown')}' must be a number"
            
            # Business logic validation using SecurityDesignPatterns
            is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(item)
            if not is_valid:
                logger.warning(f"Business logic validation failed: {error_msg}")
                return False, error_msg
        
        return True, ""

    def _execute_many(self, sql, params_list):
        """Execute multiple insert queries in a single transaction."""
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.executemany(sql, params_list)

    def _execute_single(self, sql, params):
        """Execute a single SQL statement and return results if any."""
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def _insert_product(self, cursor, item, now):
        cursor.execute(
            """
            INSERT INTO mitra10_products (name, price, url, unit, category, location, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                item.get("name"),
                item.get("price"),
                item.get("url"),
                item.get("unit"),
                item.get("category", ""),
                item.get("location", ""),
                now,
                now,
            ),
        )
        return 1

    def _update_product(self, cursor, item, existing_id, existing_price, now, anomalies):
        new_price = item["price"]
        if existing_price != new_price:
            anomaly = self._detect_anomaly(item, existing_price, new_price)
            if anomaly:
                # Price change detected - save anomaly for admin approval
                anomalies.append(anomaly)
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Price anomaly detected for {item['name']}: "
                    f"{existing_price} -> {new_price}. Pending admin approval."
                )
                # Do NOT update price - wait for admin approval
                return 0
            else:
                # Small price change (< 15%) - update automatically
                cursor.execute(
                    """
                    UPDATE mitra10_products
                    SET price = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (new_price, now, existing_id),
                )
                return 1
        return 0

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

    def _save_detected_anomalies(self, anomalies):
        """Save detected anomalies to database for admin review"""
        if not anomalies:
            return
        
        anomaly_result = PriceAnomalyService.save_anomalies('mitra10', anomalies)
        if not anomaly_result['success']:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save some anomalies: {anomaly_result['errors']}")

    # =========================
    # Public Methods
    # =========================
    def save(self, data):
        """Insert multiple Mitra10 products at once."""
        is_valid, error_msg = self._validate_data(data)
        if not is_valid:
            return False, error_msg

        now = timezone.now()
        sql = """
            INSERT INTO mitra10_products (name, price, url, unit, category, location, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_list = [
            (
                d.get("name"),
                d.get("price"),
                d.get("url"),
                d.get("unit"),
                d.get("category", ""),
                d.get("location", ""),
                now,
                now,
            )
            for d in data
        ]
        self._execute_many(sql, params_list)
        return True, ""

    def save_with_price_update(self, data):
        """Insert or update products, tracking anomalies when price changes ≥15%."""
        is_valid, error_msg = self._validate_data(data)
        if not is_valid:
            return {"success": False, "updated": 0, "inserted": 0, "anomalies": [], "error_message": error_msg}

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

        # Save anomalies to database for review
        self._save_detected_anomalies(anomalies)

        return {"success": True, "updated": updated, "inserted": inserted, "anomalies": anomalies, "error_message": ""}
