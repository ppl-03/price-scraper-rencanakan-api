from django.db import transaction, connection
from django.utils import timezone


class DepoBangunanDatabaseService:
    """Service for saving scraped DepoBangunan products to database
    
    Simple, clean database service matching Mitra10/Juragan pattern.
    """
    
    def _validate_data(self, data):
        """Validate product data before saving
        
        Args:
            data: List of product dictionaries with name, price, url, unit
            
        Returns:
            True if valid, False otherwise
        """
        if not data:
            return False
        for item in data:
            if not all(k in item for k in ("name", "price", "url", "unit")):
                return False
            if not isinstance(item["price"], int) or item["price"] < 0:
                return False
        return True
    
    def _execute_product_query(self, cursor, item):
        """Execute query to find existing product
        
        Args:
            cursor: Database cursor
            item: Product data dictionary
            
        Returns:
            Tuple of (id, price) if found, None otherwise
        """
        cursor.execute(
            "SELECT id, price FROM depobangunan_products WHERE name = %s AND url = %s AND unit = %s",
            (item["name"], item["url"], item["unit"])
        )
        return cursor.fetchone()
    
    def _update_product_price(self, cursor, item, existing_id, existing_price, now, anomalies):
        """Update existing product price if changed
        
        Args:
            cursor: Database cursor
            item: Product data dictionary
            existing_id: ID of existing product
            existing_price: Current price in database
            now: Current timestamp
            anomalies: List to append anomalies to
            
        Returns:
            1 if updated, 0 if price unchanged
        """
        new_price = item["price"]
        if existing_price != new_price:
            anomaly = self._check_anomaly(item, existing_price, new_price)
            if anomaly:
                anomalies.append(anomaly)
            cursor.execute(
                "UPDATE depobangunan_products SET price = %s, updated_at = %s WHERE id = %s",
                (new_price, now, existing_id)
            )
            return 1
        return 0
    
    def _insert_product(self, cursor, item, now):
        """Insert new product into database
        
        Args:
            cursor: Database cursor
            item: Product data dictionary
            now: Current timestamp
            
        Returns:
            1 (always, as one product is inserted)
        """
        cursor.execute(
            "INSERT INTO depobangunan_products (name, price, url, unit, location, category, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (item["name"], item["price"], item["url"], item["unit"], item.get("location", ""), item.get("category", ""), now, now)
        )
        return 1
    
    def _check_anomaly(self, item, existing_price, new_price):
        """Check if price change is anomalous (>=15% change)
        
        Args:
            item: Product data dictionary
            existing_price: Current price in database
            new_price: New price from scraping
            
        Returns:
            Anomaly dictionary if detected, None otherwise
        """
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
    
    def save(self, data):
        """Bulk save products to database
        
        Args:
            data: List of product dictionaries with name, price, url, unit
            
        Returns:
            True if successful, False otherwise
        """
        if not self._validate_data(data):
            return False

        now = timezone.now()

        sql = """
            INSERT INTO depobangunan_products
                (name, price, url, unit, location, category, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        params_list = [
            (it["name"], it["price"], it["url"], it["unit"], it.get("location", ""), it.get("category", ""), now, now)
            for it in data
        ]

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.executemany(sql, params_list)

        return True
    
    def save_with_price_update(self, data):
        """Save products with smart price update and anomaly detection
        
        Updates existing products and inserts new ones. Detects price anomalies
        (changes >= 15%) and returns them for review.
        
        Args:
            data: List of product dictionaries with name, price, url, unit
            
        Returns:
            Dictionary with:
                - success: Boolean indicating success
                - updated_count: Number of products updated
                - new_count: Number of new products inserted
                - anomalies: List of detected price anomalies
        """
        if not self._validate_data(data):
            return {"success": False, "updated_count": 0, "new_count": 0, "anomalies": []}

        now = timezone.now()
        updated_count = 0
        inserted_count = 0
        anomalies = []

        with transaction.atomic():
            with connection.cursor() as cursor:
                for item in data:
                    existing = self._execute_product_query(cursor, item)

                    if existing:
                        existing_id, existing_price = existing
                        updated_count += self._update_product_price(cursor, item, existing_id, existing_price, now, anomalies)
                    else:
                        inserted_count += self._insert_product(cursor, item, now)

        return {
            "success": True,
            "updated_count": updated_count,
            "new_count": inserted_count,
            "anomalies": anomalies
        }

