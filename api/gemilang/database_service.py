from django.db import connection, transaction
from django.utils import timezone
from typing import List, Dict, Any, Tuple
import logging
from db_pricing.anomaly_service import PriceAnomalyService

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
    
    def _validate_basic_structure(self, data: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Validate basic data structure."""
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

    def _save_detected_anomalies(self, anomalies: List[Dict[str, Any]]) -> None:
        """Save detected anomalies to database for admin review"""
        if not anomalies:
            return
        
        anomaly_result = PriceAnomalyService.save_anomalies('gemilang', anomalies)
        if not anomaly_result['success']:
            logger.error(f"Failed to save some anomalies: {anomaly_result['errors']}")

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
            
            # Save anomalies to database for review
            self._save_detected_anomalies(anomalies)
            
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
