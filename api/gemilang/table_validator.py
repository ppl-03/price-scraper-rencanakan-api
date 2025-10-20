from django.db import connection

class GemilangTableValidator:
    def check_table_exists(self):
        from django.conf import settings
        
        with connection.cursor() as cursor:
            db_engine = settings.DATABASES['default']['ENGINE']
            
            if 'sqlite' in db_engine:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gemilang_products'")
            elif 'mysql' in db_engine:
                cursor.execute("SHOW TABLES LIKE 'gemilang_products'")
            else:
                raise Exception(f"Unsupported database engine: {db_engine}")
            
            result = cursor.fetchone()
            return result is not None
    
    def get_table_schema(self):
        from django.conf import settings
        
        with connection.cursor() as cursor:
            db_engine = settings.DATABASES['default']['ENGINE']
            
            if 'sqlite' in db_engine:
                cursor.execute("PRAGMA table_info(gemilang_products)")
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
                cursor.execute("DESCRIBE gemilang_products")
                columns = cursor.fetchall()
                # MySQL DESCRIBE returns: Field, Type, Null, Key, Default, Extra
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
                raise Exception(f"Unsupported database engine: {db_engine}")
    
    def get_record_count(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM gemilang_products")
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_all_records(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, price, url, unit, created_at, updated_at FROM gemilang_products")
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_record_by_name(self, name):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, price, url, unit, created_at, updated_at FROM gemilang_products WHERE name = %s", [name])
            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def clear_table(self):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM gemilang_products")
    
    def get_all_tables(self):
        """Get all tables in the database (works for both SQLite and MySQL)"""
        from django.conf import settings
        
        with connection.cursor() as cursor:
            db_engine = settings.DATABASES['default']['ENGINE']
            
            if 'sqlite' in db_engine:
                # SQLite syntax
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            elif 'mysql' in db_engine:
                # MySQL syntax
                cursor.execute("SHOW TABLES")
            else:
                raise Exception(f"Unsupported database engine: {db_engine}")
            
            tables = cursor.fetchall()
            return [table[0] for table in tables]
