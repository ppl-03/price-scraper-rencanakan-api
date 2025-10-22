from django.db import connection

class Mitra10TableValidator:
    def check_table_exists(self):
        from django.conf import settings
        
        with connection.cursor() as cursor:
            db_engine = settings.DATABASES['default']['ENGINE']
            table_name = 'mitra10_products'
            
            if 'sqlite' in db_engine:
                query = "SELECT name FROM sqlite_master WHERE type='table' AND name='{}'".format(table_name)
                cursor.execute(query)
            elif 'mysql' in db_engine:
                query = "SHOW TABLES LIKE '{}'".format(table_name)
                cursor.execute(query)
            else:
                raise NotImplementedError(f"Unsupported database engine: {db_engine}")
            
            result = cursor.fetchone()
            return result is not None
    
    def get_table_schema(self):
        from django.conf import settings
        
        with connection.cursor() as cursor:
            db_engine = settings.DATABASES['default']['ENGINE']
            table_name = 'mitra10_products'
            
            if 'sqlite' in db_engine:
                query = "PRAGMA table_info({})".format(table_name)
                cursor.execute(query)
                columns = cursor.fetchall()
                return {
                    col[1]: {
                        'type': col[2],
                        'not_null': bool(col[3]),
                        'default': col[4],
                        'primary_key': bool(col[5])
                    }
                    for col in columns
                }
            elif 'mysql' in db_engine:
                query = "DESCRIBE {}".format(table_name)
                cursor.execute(query)
                columns = cursor.fetchall()
                return {
                    col[0]: {
                        'type': col[1],
                        'not_null': col[2] == 'NO',
                        'default': col[4],
                        'primary_key': col[3] == 'PRI'
                    }
                    for col in columns
                }
            else:
                raise NotImplementedError(f"Unsupported database engine: {db_engine}")
    
    def validate_schema(self):
        if not self.check_table_exists():
            return False
        
        schema = self.get_table_schema()
        required_columns = ['id', 'name', 'price', 'url', 'unit', 'created_at', 'updated_at']
        
        for col in required_columns:
            if col not in schema:
                return False
        
        return True
