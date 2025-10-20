from django.db import connection, transaction
from django.utils import timezone

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
