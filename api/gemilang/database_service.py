from django.db import connection, transaction
from django.utils import timezone
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class GemilangDatabaseService:
    ALLOWED_TABLES = ['gemilang_products']
    ALLOWED_COLUMNS = {
        'id', 'name', 'price', 'url', 'unit', 'created_at', 'updated_at'
    }
    
    def __init__(self):
        self.table_name = 'gemilang_products'
        self._validate_table_name()
    
    def _validate_table_name(self):
        if self.table_name not in self.ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {self.table_name}")
    
    def _validate_column_names(self, columns: List[str]):
        for col in columns:
            if col not in self.ALLOWED_COLUMNS:
                raise ValueError(f"Invalid column name: {col}")
    
    def _validate_data(self, data: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not data:
            return False, "Data cannot be empty"
        
        if not isinstance(data, list):
            return False, "Data must be a list"
        
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                return False, f"Item {idx} must be a dictionary"
            
            required_fields = ["name", "price", "url", "unit"]
            missing_fields = [f for f in required_fields if f not in item]
            if missing_fields:
                return False, f"Item {idx} missing required fields: {missing_fields}"
            
            price = item.get("price")
            if not isinstance(price, (int, float)):
                return False, f"Item {idx}: price must be a number"
            if price < 0:
                return False, f"Item {idx}: price must be non-negative"
            if price > 1000000000:
                return False, f"Item {idx}: price exceeds reasonable limit"
            
            name = item.get("name")
            if not isinstance(name, str):
                return False, f"Item {idx}: name must be a string"
            if len(name) < 2 or len(name) > 500:
                return False, f"Item {idx}: name length must be between 2 and 500"
            
            url = item.get("url")
            if not isinstance(url, str):
                return False, f"Item {idx}: url must be a string"
            if not url.startswith(('http://', 'https://')):
                return False, f"Item {idx}: url must start with http:// or https://"
            if any(x in url.lower() for x in ['localhost', '127.0.0.1', '0.0.0.0']):
                logger.critical(f"SSRF attempt detected: {url}")
                return False, f"Item {idx}: invalid URL"
            
            unit = item.get("unit")
            if not isinstance(unit, str):
                return False, f"Item {idx}: unit must be a string"
            if len(unit) > 50:
                return False, f"Item {idx}: unit too long"
        
        return True, ""
    
    def _sanitize_string(self, value: str) -> str:
        value = value.replace('\x00', '')
        value = value[:1000]
        return value
    
    def save(self, data: List[Dict[str, Any]]) -> Tuple[bool, str]:
        is_valid, error_msg = self._validate_data(data)
        if not is_valid:
            logger.warning(f"Data validation failed: {error_msg}")
            return False, error_msg
        
        try:
            now = timezone.now()
            
            sql = """
                INSERT INTO gemilang_products
                    (name, price, url, unit, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            self._validate_column_names(['name', 'price', 'url', 'unit', 'created_at', 'updated_at'])
            
            params_list = [
                (
                    self._sanitize_string(item["name"]),
                    int(item["price"]),
                    self._sanitize_string(item["url"]),
                    self._sanitize_string(item["unit"]),
                    now,
                    now
                )
                for item in data
            ]
            
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.executemany(sql, params_list)
            
            logger.info(f"Successfully saved {len(data)} products")
            return True, ""
            
        except Exception as e:
            logger.error(f"Database save failed: {type(e).__name__}")
            return False, "Database operation failed"
    
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
                "old_price": existing_price,
                "new_price": new_price,
                "change_percent": round(price_diff_pct, 2)
            }
        return None

    def save_with_price_update(
        self, 
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        is_valid, error_msg = self._validate_data(data)
        if not is_valid:
            logger.warning(f"Data validation failed: {error_msg}")
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
            
            self._validate_column_names(['id', 'name', 'price', 'url', 'unit', 'created_at', 'updated_at'])
            
            with transaction.atomic():
                with connection.cursor() as cursor:
                    for item in data:
                        name = self._sanitize_string(item["name"])
                        url = self._sanitize_string(item["url"])
                        unit = self._sanitize_string(item["unit"])
                        price = int(item["price"])
                        
                        select_sql = """
                            SELECT id, price 
                            FROM gemilang_products 
                            WHERE name = %s AND url = %s AND unit = %s
                        """
                        cursor.execute(select_sql, (name, url, unit))
                        existing = cursor.fetchone()
                        
                        if existing:
                            existing_id, existing_price = existing
                            
                            if existing_price != price:
                                anomaly = self._check_anomaly(item, existing_price, price)
                                if anomaly:
                                    anomalies.append(anomaly)
                                    logger.warning(
                                        f"Price anomaly detected for {name}: "
                                        f"{existing_price} -> {price}"
                                    )
                                
                                update_sql = """
                                    UPDATE gemilang_products 
                                    SET price = %s, updated_at = %s 
                                    WHERE id = %s
                                """
                                cursor.execute(update_sql, (price, now, existing_id))
                                updated_count += 1
                        else:
                            insert_sql = """
                                INSERT INTO gemilang_products 
                                (name, price, url, unit, created_at, updated_at) 
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(
                                insert_sql,
                                (name, price, url, unit, now, now)
                            )
                            inserted_count += 1
            
            logger.info(
                f"Save with update completed: {updated_count} updated, "
                f"{inserted_count} inserted, {len(anomalies)} anomalies"
            )
            
            return {
                "success": True,
                "updated": updated_count,
                "inserted": inserted_count,
                "anomalies": anomalies
            }
            
        except Exception as e:
            logger.error(f"Database save_with_price_update failed: {type(e).__name__}")
            return {
                "success": False,
                "error": "Database operation failed",
                "updated": 0,
                "inserted": 0,
                "anomalies": []
            }
