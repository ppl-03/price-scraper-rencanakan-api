from django.db import connection, transaction
from django.utils import timezone
from db_pricing.anomaly_service import PriceAnomalyService
import logging
logger = logging.getLogger(__name__)


class TokopediaDatabaseService:
    def _validate_data(self, data):
        """Validate input data before database operations."""
        if not data:
            logger.warning("No data to validate")
            return False
        
        for item in data:
            # Check required fields
            required_keys = ("name", "price", "url")
            if not all(k in item for k in required_keys):
                missing = [k for k in required_keys if k not in item]
                logger.warning(f"Missing required keys: {missing}")
                return False
            
            # Validate price
            if not isinstance(item["price"], int) or item["price"] < 0:
                logger.warning(f"Invalid price: {item.get('price')}")
                return False
            
            # Validate types
            if not isinstance(item["name"], str):
                logger.warning(f"Invalid name type: {type(item['name'])}")
                return False
            if not isinstance(item["url"], str):
                logger.warning(f"Invalid url type: {type(item['url'])}")
                return False
            
            # ✅ FIX: Convert None to empty string for optional fields
            if item.get("unit") is None:
                item["unit"] = ''
            if item.get("location") is None:
                item["location"] = ''
            if item.get("category") is None:
                item["category"] = ''
            
            # Now validate types after conversion
            if not isinstance(item["unit"], str):
                logger.warning(f"Invalid unit type: {type(item['unit'])}")
                return False
            if not isinstance(item["location"], str):
                logger.warning(f"Invalid location type: {type(item['location'])}")
                return False
        
        return True
    
    def save(self, data):
        if not self._validate_data(data):
            return False

        now = timezone.now()

        # SQL injection protection: parameterized query with %s placeholders
        sql = """
            INSERT INTO tokopedia_products
                (name, price, url, unit, location, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        # Prepare parameters as tuples - Django DB-API escapes these properly
        params_list = [
            (it["name"], it["price"], it["url"], it["unit"], it["location"], now, now)
            for it in data
        ]

        with transaction.atomic():
            with connection.cursor() as cursor:
                # executemany with parameterized queries - safe from SQL injection
                cursor.executemany(sql, params_list)

        return True
    
    def _check_anomaly(self, item, existing_price, new_price):
        """
        Check for price anomaly (>= 15% change).
        """
        if existing_price == 0:
            return None
        
        price_diff_pct = ((new_price - existing_price) / existing_price) * 100
        
        if abs(price_diff_pct) >= 15:
            return {
                "name": item["name"],
                "url": item["url"],
                "unit": item["unit"],
                "location": item["location"],
                "old_price": existing_price,
                "new_price": new_price,
                "change_percent": round(price_diff_pct, 2)
            }
        
        return None

    def _save_detected_anomalies(self, anomalies):
        """Save detected anomalies to database for admin review"""
        if not anomalies:
            return
        
        anomaly_result = PriceAnomalyService.save_anomalies('tokopedia', anomalies)
        if not anomaly_result['success']:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save some anomalies: {anomaly_result['errors']}")

    def _update_existing_product(self, cursor, item, existing_id, existing_price, now, anomalies):
        """
        Update existing product with SQL injection protection.
        """
        new_price = item["price"]
        
        if existing_price != new_price:
            anomaly = self._check_anomaly(item, existing_price, new_price)
            if anomaly:
                anomalies.append(anomaly)
            
            # SQL injection protection: parameterized query
            cursor.execute(
                "UPDATE tokopedia_products SET price = %s, updated_at = %s WHERE id = %s",
                (new_price, now, existing_id)
            )
            return 1
        
        return 0

    def _insert_new_product(self, cursor, item, now):
        """
        Insert new product with SQL injection protection.
        """
        # SQL injection protection: parameterized query
        cursor.execute(
            """INSERT INTO tokopedia_products 
               (name, price, url, unit, location, created_at, updated_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (item["name"], item["price"], item["url"], item["unit"], item["location"], now, now)
        )
        return 1

    def save_with_price_update(self, data):
        """
        Save or update products with price change detection.
        SQL injection protection: all queries use parameterized statements.
        
        Args:
            data: List of product dictionaries
            
        Returns:
            dict: {
                "success": bool,
                "updated": int,
                "inserted": int,
                "anomalies": list
            }
        """
        if not self._validate_data(data):
            return {"success": False, "updated": 0, "inserted": 0, "anomalies": []}

        now = timezone.now()
        updated_count = 0
        inserted_count = 0
        anomalies = []

        with transaction.atomic():
            with connection.cursor() as cursor:
                for item in data:
                    # SQL injection protection: parameterized SELECT query
                    cursor.execute(
                        """SELECT id, price FROM tokopedia_products 
                           WHERE name = %s AND url = %s AND unit = %s AND location = %s""",
                        (item["name"], item["url"], item["unit"], item["location"])
                    )
                    existing = cursor.fetchone()

                    if existing:
                        existing_id, existing_price = existing
                        updated_count += self._update_existing_product(
                            cursor, item, existing_id, existing_price, now, anomalies
                        )
                    else:
                        inserted_count += self._insert_new_product(cursor, item, now)

        # Save anomalies to database for review
        self._save_detected_anomalies(anomalies)

        return {
            "success": True,
            "updated": updated_count,
            "inserted": inserted_count,
            "anomalies": anomalies
        }
