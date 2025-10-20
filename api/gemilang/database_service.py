from django.db import connection
from django.conf import settings

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
            return False
        
        # Get database engine to use correct datetime syntax
        db_engine = settings.DATABASES['default']['ENGINE']
        
        # Use appropriate datetime function for each database
        if 'sqlite' in db_engine:
            datetime_now = "datetime('now')"
        elif 'mysql' in db_engine:
            datetime_now = "NOW()"
        else:
            raise Exception(f"Unsupported database engine: {db_engine}")
        
        with connection.cursor() as cursor:
            for item in data:
                cursor.execute(
                    f"INSERT INTO gemilang_products (name, price, url, unit, created_at, updated_at) VALUES (%s, %s, %s, %s, {datetime_now}, {datetime_now})",
                    [item["name"], item["price"], item["url"], item["unit"]]
                )
        return True
