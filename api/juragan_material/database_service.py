from django.db import connection, transaction
from django.utils import timezone
from db_pricing.anomaly_service import PriceAnomalyService

class JuraganMaterialDatabaseService:
    def _validate_dict_item(self, item):
        """Validate dictionary item has required fields and valid price."""
        required_keys = ("name", "price", "url", "unit", "location")
        if not all(k in item for k in required_keys):
            return False
        return isinstance(item["price"], int) and item["price"] >= 0
    
    def _validate_object_item(self, item):
        """Validate object item has required attributes and valid price."""
        required_attrs = ("name", "price", "url", "unit", "location")
        if not all(hasattr(item, attr) for attr in required_attrs):
            return False
        return isinstance(item.price, int) and item.price >= 0
    
    def _validate_single_item(self, item):
        """Validate a single item regardless of type (dict or object)."""
        if isinstance(item, dict):
            return self._validate_dict_item(item)
        elif isinstance(item, object):
            return self._validate_object_item(item)
        return False
    
    def _validate_data(self, data):
        """Validate data array contains valid items."""
        if not data:
            return False
        return all(self._validate_single_item(item) for item in data)
    
    def save(self, data):
        if not self._validate_data(data):
            return False

        now = timezone.now()

        sql = """
            INSERT INTO juragan_material_products
                (name, price, url, unit, location, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s,%s)
        """
        params_list = [
            self._create_product_params(item, now)
            for item in data
        ]
        

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.executemany(sql, params_list)

        return True
    
    def _create_product_params(self, item, now):
        """Helper method to create product parameters for database insertion."""
        if isinstance(item, dict):
            return (item["name"], item["price"], item["url"], item["unit"], item["location"], now, now)
        elif isinstance(item, object):
            return (item.name, item.price, item.url, item.unit,item.location,now, now)
    
    def _extract_product_identifiers(self, item):
        """Helper method to extract product identifiers (name, url, unit) from item."""
        if isinstance(item, dict):
            return (item["name"], item["url"], item["unit"])
        elif isinstance(item, object):
            return (item.name, item.url, item.unit)
    
    def _calculate_price_change_percentage(self, existing_price, new_price):
        """Helper method to calculate price change percentage."""
        if existing_price == 0:
            return None
        return ((new_price - existing_price) / existing_price) * 100
    
    def _create_anomaly_object(self, item, existing_price, new_price, price_diff_pct):
        """Helper method to create anomaly object."""
        if isinstance(item, dict):
            return {
                "name": item["name"],
                "url": item["url"],
                "unit": item["unit"],
                "location": item["location"],
                "old_price": existing_price,
                "new_price": new_price,
                "change_percent": round(price_diff_pct, 2)
            }
        elif isinstance(item, object):
            return {
                "name": item.name,
                "url": item.url,
                "unit": item.unit,
                "location": item.location,
                "old_price": existing_price,
                "new_price": new_price,
                "change_percent": round(price_diff_pct, 2)
            }
    
    def _check_anomaly(self, item, existing_price, new_price):
        price_diff_pct = self._calculate_price_change_percentage(existing_price, new_price)
        if price_diff_pct is None:
            return None
        
        if abs(price_diff_pct) >= 15:
            return self._create_anomaly_object(item, existing_price, new_price, price_diff_pct)
        return None

    def _save_detected_anomalies(self, anomalies):
        """Save detected anomalies to database for admin review"""
        if not anomalies:
            return
        
        anomaly_result = PriceAnomalyService.save_anomalies('juragan_material', anomalies)
        if not anomaly_result['success']:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save some anomalies: {anomaly_result['errors']}")

    def _update_existing_product(self, cursor, item, existing_id, existing_price, now, anomalies):
        new_price = item["price"] if isinstance(item, dict) else item.price
        if existing_price != new_price:
            anomaly = self._check_anomaly(item, existing_price, new_price)
            if anomaly:
                anomalies.append(anomaly)
            cursor.execute(
                "UPDATE juragan_material_products SET price = %s, updated_at = %s WHERE id = %s",
                (new_price, now, existing_id)
            )
            return 1
        return 0

    def _insert_new_product(self, cursor, item, now):
        cursor.execute(
            "INSERT INTO juragan_material_products (name, price, url, unit, location, created_at, updated_at) VALUES (%s, %s, %s, %s. %s, %s, %s)",
            self._create_product_params(item, now)
        )
        return 1

    def _get_existing_product(self, cursor, item):
        """Helper method to get existing product by name, url, and unit."""
        cursor.execute(
            "SELECT id, price FROM juragan_material_products WHERE name = %s AND url = %s AND unit = %s",
            self._extract_product_identifiers(item)
        )
        return cursor.fetchone()

    def _process_single_item(self, cursor, item, now, anomalies):
        """Process a single item for save_with_price_update operation."""
        existing = self._get_existing_product(cursor, item)
        
        if existing:
            existing_id, existing_price = existing
            return self._update_existing_product(cursor, item, existing_id, existing_price, now, anomalies), 0
        else:
            return 0, self._insert_new_product(cursor, item, now)

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
                    updated, inserted = self._process_single_item(cursor, item, now, anomalies)
                    updated_count += updated
                    inserted_count += inserted

        # Save anomalies to database for review
        self._save_detected_anomalies(anomalies)

        return {
            "success": True,
            "updated": updated_count,
            "inserted": inserted_count,
            "anomalies": anomalies
        }
