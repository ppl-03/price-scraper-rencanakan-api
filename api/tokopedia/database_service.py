from django.db import connection, transaction
from django.utils import timezone
from db_pricing.anomaly_service import PriceAnomalyService
from typing import List, Dict, Any, Tuple
from .logging_utils import get_tokopedia_logger

logger = get_tokopedia_logger("database_service")


class TokopediaDatabaseService:
    ALLOWED_TABLES = ['tokopedia_products']
    ALLOWED_COLUMNS = {
        'id', 'name', 'price', 'url', 'unit', 'location', 'category', 'created_at', 'updated_at'
    }
    
    def __init__(self):
        self.table_name = 'tokopedia_products'
        self._validate_table_name()
    
    def _validate_table_name(self):
        if self.table_name not in self.ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {self.table_name}")
    
    def _validate_column_names(self, columns: List[str]):
        for col in columns:
            if col not in self.ALLOWED_COLUMNS:
                raise ValueError(f"Invalid column name: {col}")
    def _validate_basic_structure(self, data: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Validate basic data structure."""
        if not data:
            return False, "Data cannot be empty"
        if not isinstance(data, list):
            return False, "Data must be a list"
        return True, ""
    
    def _validate_item_structure(self, item: Any, idx: int) -> Tuple[bool, str]:
        """Validate individual item structure."""
        if not isinstance(item, dict):
            return False, f"Item {idx} must be a dictionary"
        
        required_fields = ["name", "price", "url", "unit", "location"]
        missing_fields = [f for f in required_fields if f not in item]
        if missing_fields:
            return False, f"Item {idx} missing required fields: {missing_fields}"
        return True, ""
    
    def _validate_price(self, price: Any, idx: int) -> Tuple[bool, str]:
        """Validate price field."""
        if not isinstance(price, (int, float)):
            return False, f"Item {idx}: price must be a number"
        if price < 0:
            return False, f"Item {idx}: price must be non-negative"
        if price > 1000000000:
            return False, f"Item {idx}: price exceeds reasonable limit"
        return True, ""
    
    def _validate_name(self, name: Any, idx: int) -> Tuple[bool, str]:
        """Validate name field."""
        if not isinstance(name, str):
            return False, f"Item {idx}: name must be a string"
        if len(name) < 2 or len(name) > 500:
            return False, f"Item {idx}: name length must be between 2 and 500"
        return True, ""
    
    def _validate_url(self, url: Any, idx: int) -> Tuple[bool, str]:
        """Validate URL field with security checks."""
        if not isinstance(url, str):
            return False, f"Item {idx}: url must be a string"
        if not url.startswith('https://'):
            return False, f"Item {idx}: url must use HTTPS protocol for security"
        if any(x in url.lower() for x in ['localhost', '127.0.0.1', '0.0.0.0']):
            logger.critical("SSRF attempt detected: %s", url)
            return False, f"Item {idx}: invalid URL"
        return True, ""
    
    def _validate_unit(self, unit: Any, idx: int) -> Tuple[bool, str]:
        """Validate unit field."""
        if not isinstance(unit, str):
            return False, f"Item {idx}: unit must be a string"
        if len(unit) > 50:
            return False, f"Item {idx}: unit too long"
        return True, ""
    
    def _validate_data_internal(self, data: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Internal validation that returns tuple with error message."""
        is_valid, error_msg = self._validate_basic_structure(data)
        if not is_valid:
            return False, error_msg
        
        for idx, item in enumerate(data):
            is_valid, error_msg = self._validate_item_structure(item, idx)
            if not is_valid:
                return False, error_msg
            
            is_valid, error_msg = self._validate_price(item.get("price"), idx)
            if not is_valid:
                return False, error_msg
            
            is_valid, error_msg = self._validate_name(item.get("name"), idx)
            if not is_valid:
                return False, error_msg
            
            is_valid, error_msg = self._validate_url(item.get("url"), idx)
            if not is_valid:
                return False, error_msg
            
            is_valid, error_msg = self._validate_unit(item.get("unit"), idx)
            if not is_valid:
                return False, error_msg
        
        return True, ""
    
    def _validate_data(self, data: List[Dict[str, Any]]) -> bool:
        """Public validation method for backward compatibility - returns bool only."""
        is_valid, _ = self._validate_data_internal(data)
        return is_valid
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string value, handling None values."""
        if value is None:
            return ""
        value = value.replace('\x00', '')
        value = value[:1000]
        return value
    
    def save(self, data: List[Dict[str, Any]]) -> bool:
        is_valid, error_msg = self._validate_data_internal(data)
        if not is_valid:
            logger.warning("Data validation failed: %s", error_msg)
            return False
        
        try:
            now = timezone.now()
            
            sql = """
                INSERT INTO tokopedia_products
                    (name, price, url, unit, location, category, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self._validate_column_names(['name', 'price', 'url', 'unit', 'location', 'category', 'created_at', 'updated_at'])
            
            params_list = [
                (
                    self._sanitize_string(item["name"]),
                    int(item["price"]),
                    self._sanitize_string(item["url"]),
                    self._sanitize_string(item["unit"]),
                    self._sanitize_string(item.get("location", "")),
                    self._sanitize_string(item.get("category", "")),
                    now,
                    now
                )
                for item in data
            ]
            
            if params_list:
                sample_location = params_list[0][4]
                logger.info(
                    "Saving %s products. Sample location value: '%s' (length: %s)",
                    len(data),
                    sample_location,
                    len(sample_location)
                )
            
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.executemany(sql, params_list)
            
            logger.info("Successfully saved %s products", len(data))
            return True
            
        except Exception as e:
            logger.exception("Database save failed: %s", type(e).__name__)
            return False
    
    def _check_anomaly(
        self, 
        item: Dict[str, Any], 
        existing_price: float, 
        new_price: float
    ) -> Dict[str, Any]:
        if existing_price == 0:
            return None
        
        price_diff_pct = ((new_price - existing_price) / existing_price) * 100
        
        if abs(price_diff_pct) >= 15:
            return {
                "name": item["name"],
                "url": item["url"],
                "unit": item["unit"],
                "location": item.get("location", ""),
                "old_price": existing_price,
                "new_price": new_price,
                "change_percent": round(price_diff_pct, 2)
            }
        return None

    def _save_detected_anomalies(self, anomalies: List[Dict[str, Any]]) -> None:
        """Save detected anomalies to database for admin review"""
        if not anomalies:
            return
        
        anomaly_result = PriceAnomalyService.save_anomalies('tokopedia', anomalies)
        if not anomaly_result['success']:
            logger.error("Failed to save some anomalies: %s", anomaly_result['errors'])

    def _update_existing_product(self, cursor, item, existing_id, existing_price, now, anomalies):
        """
        Update existing product with SQL injection protection.
        """
        new_price = item["price"]
        location = self._sanitize_string(item.get("location", ""))
        
        if existing_price != new_price:
            anomaly = self._check_anomaly(item, existing_price, new_price)
            if anomaly:
                # Price change detected - save anomaly for admin approval
                anomalies.append(anomaly)
                logger.warning(
                    "Price anomaly detected for %s: %s -> %s. Pending admin approval.",
                    item['name'],
                    existing_price,
                    new_price
                )
                # Do NOT update price - wait for admin approval
                return 0
            # Small price change (< 15%) - update automatically
            # SQL injection protection: parameterized query
            cursor.execute(
                "UPDATE tokopedia_products SET price = %s, location = %s, updated_at = %s WHERE id = %s",
                (new_price, location, now, existing_id)
            )
            return 1
        
        # No change needed - price is the same
        return 0

    def _insert_new_product(self, cursor, item, now):
        """
        Insert new product with SQL injection protection.
        """
        name = self._sanitize_string(item["name"])
        url = self._sanitize_string(item["url"])
        unit = self._sanitize_string(item["unit"])
        location = self._sanitize_string(item.get("location", ""))
        category = self._sanitize_string(item.get("category", ""))
        price = int(item["price"])
        
        # SQL injection protection: parameterized query
        cursor.execute(
            """INSERT INTO tokopedia_products 
               (name, price, url, unit, location, category, created_at, updated_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (name, price, url, unit, location, category, now, now)
        )
        return 1

    def save_with_price_update(
        self, 
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        is_valid, error_msg = self._validate_data_internal(data)
        if not is_valid:
            logger.warning("Data validation failed: %s", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "updated": 0,
                "inserted": 0,
                "anomalies": []
            }
        
        try:
            now = timezone.now()
            updated_count = 0
            inserted_count = 0
            anomalies = []
            
            self._validate_column_names(['id', 'name', 'price', 'url', 'unit', 'location', 'category', 'created_at', 'updated_at'])
            
            if data:
                sample_location = data[0].get("location", "")
                logger.info(
                    "save_with_price_update: Processing %s products. Sample location: '%s' (length: %s)",
                    len(data),
                    sample_location,
                    len(sample_location)
                )
            
            with transaction.atomic():
                with connection.cursor() as cursor:
                    for item in data:
                        name = self._sanitize_string(item["name"])
                        url = self._sanitize_string(item["url"])
                        unit = self._sanitize_string(item["unit"])
                        
                        select_sql = """
                            SELECT id, price 
                            FROM tokopedia_products 
                            WHERE name = %s AND url = %s AND unit = %s
                        """
                        cursor.execute(select_sql, (name, url, unit))
                        existing = cursor.fetchone()
                        
                        if existing:
                            existing_id, existing_price = existing
                            updated_count += self._update_existing_product(
                                cursor, item, existing_id, existing_price, now, anomalies
                            )
                        else:
                            inserted_count += self._insert_new_product(cursor, item, now)
            
            logger.info(
                "Save with update completed: %s updated, %s inserted, %s anomalies",
                updated_count,
                inserted_count,
                len(anomalies)
            )
            
            # Save anomalies to database for review
            self._save_detected_anomalies(anomalies)
            
            return {
                "success": True,
                "updated": updated_count,
                "inserted": inserted_count,
                "anomalies": anomalies
            }
            
        except Exception as e:
            logger.exception("Database save_with_price_update failed: %s", type(e).__name__)
            return {
                "success": False,
                "error": "Database operation failed",
                "updated": 0,
                "inserted": 0,
                "anomalies": []
            }
