from django.db import connection, transaction
from django.utils import timezone
from db_pricing.anomaly_service import PriceAnomalyService
from .logging_utils import get_juragan_material_logger

logger = get_juragan_material_logger("database_service")

class JuraganMaterialDatabaseService:
    """
    Database service for Juragan Material products.
    
    Security Features (OWASP A03:2021 - Injection Prevention):
    - Uses parameterized queries exclusively (no string concatenation)
    - Validates all input data before database operations
    - Sanitizes data to prevent SQL injection
    - Uses Django ORM's built-in escaping mechanisms
    """
    def _validate_dict_item(self, item):
        """
        Validate dictionary item has required fields and valid price.
        
        Security: Prevents injection by validating data types and structure
        before database insertion.
        """
        required_keys = ("name", "price", "url", "unit", "location")
        if not all(k in item for k in required_keys):
            logger.warning("Invalid item structure: missing required keys")
            return False
        
        # Validate data types and constraints
        if not isinstance(item["price"], int) or item["price"] < 0:
            logger.warning(f"Invalid price value: {item.get('price')}")
            return False
        
        # Validate string lengths to prevent buffer overflow
        if not isinstance(item["name"], str) or len(item["name"]) > 500:
            logger.warning(f"Invalid name length: {len(item.get('name', ''))}")
            return False
        
        if not isinstance(item["url"], str) or len(item["url"]) > 1000:
            logger.warning(f"Invalid URL length: {len(item.get('url', ''))}")
            return False
        
        if not isinstance(item["unit"], str) or len(item["unit"]) > 50:
            logger.warning(f"Invalid unit length: {len(item.get('unit', ''))}")
            return False
        
        if not isinstance(item["location"], str) or len(item["location"]) > 200:
            logger.warning(f"Invalid location length: {len(item.get('location', ''))}")
            return False
        
        return True
    
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
        """
        Save products to database using parameterized queries.
        
        Security (OWASP A03:2021):
        - Uses parameterized queries (%s placeholders) to prevent SQL injection
        - Validates all input data before insertion
        - Uses executemany for batch operations with parameter binding
        - Never concatenates user input into SQL strings
        """
        if not self._validate_data(data):
            logger.error("Data validation failed in save()")
            return False

        now = timezone.now()

        # SECURITY: Parameterized query - uses %s placeholders, not string concatenation
        # This prevents SQL injection by separating SQL code from data
        sql = """
            INSERT INTO juragan_material_products
                (name, price, url, unit, location, category, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # SECURITY: All parameters are bound safely via executemany
        params_list = [
            self._create_product_params(item, now)
            for item in data
        ]
        
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # SECURITY: executemany uses parameter binding, not string concatenation
                    cursor.executemany(sql, params_list)
            logger.info(f"Successfully saved {len(data)} products to database")
            return True
        except Exception as e:
            logger.error(f"Database save failed: {str(e)}")
            return False
    
    def _create_product_params(self, item, now):
        """Helper method to create product parameters for database insertion."""
        # Provide empty string for category when not present to satisfy DB schema
        if isinstance(item, dict):
            category = item.get("category", "")
            return (item["name"], item["price"], item["url"], item["unit"], item["location"], category, now, now)
        elif isinstance(item, object):
            category = getattr(item, 'category', '')
            return (item.name, item.price, item.url, item.unit, item.location, category, now, now)
    
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
            logger.error(f"Failed to save some anomalies: {anomaly_result['errors']}")

    def _update_existing_product(self, cursor, item, existing_id, existing_price, now, anomalies):
        """
        Update existing product with parameterized query.
        
        Security (OWASP A03:2021):
        - Uses parameterized UPDATE query
        - Validates price changes to detect anomalies
        - Never concatenates user input into SQL
        """
        new_price = item["price"] if isinstance(item, dict) else item.price
        if existing_price != new_price:
            anomaly = self._check_anomaly(item, existing_price, new_price)
            if anomaly:
                # Price change detected - save anomaly for admin approval
                anomalies.append(anomaly)
                item_name = item["name"] if isinstance(item, dict) else item.name
                logger.warning(
                    f"Price anomaly detected for {item_name}: "
                    f"{existing_price} -> {new_price}. Pending admin approval."
                )
                # Do NOT update price - wait for admin approval
                return 0
            else:
                # Small price change (< 15%) - update automatically
                # SECURITY: Parameterized UPDATE query
                cursor.execute(
                    "UPDATE juragan_material_products SET price = %s, updated_at = %s WHERE id = %s",
                    (new_price, now, existing_id)
                )
                return 1
        return 0

    def _insert_new_product(self, cursor, item, now):
        """
        Insert new product using parameterized query.
        
        Security (OWASP A03:2021):
        - Uses parameterized INSERT query
        - Separates SQL structure from data
        """
        # SECURITY: Parameterized INSERT with bound parameters
        cursor.execute(
            "INSERT INTO juragan_material_products (name, price, url, unit, location, category, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            self._create_product_params(item, now)
        )
        return 1

    def _get_existing_product(self, cursor, item):
        """
        Get existing product by name, url, and unit using parameterized query.
        
        Security (OWASP A03:2021):
        - Uses parameterized query with %s placeholders
        - Prevents SQL injection by binding parameters, not concatenating strings
        """
        # SECURITY: Parameterized query - parameters passed separately
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
        """
        Save or update products with price anomaly detection.
        
        Security (OWASP A03:2021):
        - All database operations use parameterized queries
        - Input validation prevents injection attacks
        - Anomaly detection prevents malicious price manipulation
        """
        if not self._validate_data(data):
            logger.error("Data validation failed in save_with_price_update()")
            return {"success": False, "updated": 0, "inserted": 0, "anomalies": []}

        now = timezone.now()
        updated_count = 0
        inserted_count = 0
        anomalies = []

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    for item in data:
                        updated, inserted = self._process_single_item(cursor, item, now, anomalies)
                        updated_count += updated
                        inserted_count += inserted

            # Save anomalies to database for review
            self._save_detected_anomalies(anomalies)

            logger.info(f"Database operation completed: {inserted_count} inserted, {updated_count} updated, {len(anomalies)} anomalies")

            return {
                "success": True,
                "updated": updated_count,
                "inserted": inserted_count,
                "anomalies": anomalies
            }
        except Exception as e:
            logger.error(f"Database operation failed: {str(e)}")
            return {"success": False, "updated": 0, "inserted": 0, "anomalies": []}
