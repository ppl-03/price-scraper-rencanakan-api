from django.test import TestCase
from django.db import connection
from django.conf import settings


class MySQLTestCase(TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass


def get_table_columns_mysql(table_name):
    with connection.cursor() as cursor:
        query = "DESCRIBE {}".format(table_name)
        cursor.execute(query)
        columns = cursor.fetchall()
        return [col[0] for col in columns]


def get_table_columns_sqlite(table_name):
    with connection.cursor() as cursor:
        query = "PRAGMA table_info({})".format(table_name)
        cursor.execute(query)
        columns = cursor.fetchall()
        return [col[1] for col in columns]


def get_table_columns(table_name):
    db_engine = settings.DATABASES['default']['ENGINE']
    
    if 'mysql' in db_engine:
        return get_table_columns_mysql(table_name)
    elif 'sqlite' in db_engine:
        return get_table_columns_sqlite(table_name)
    else:
        raise Exception(f"Unsupported database engine: {db_engine}")


def table_exists(table_name):
    db_engine = settings.DATABASES['default']['ENGINE']
    
    with connection.cursor() as cursor:
        if 'mysql' in db_engine:
            query = "SHOW TABLES LIKE '{}'".format(table_name)
            cursor.execute(query)
        elif 'sqlite' in db_engine:
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name='{}'".format(table_name)
            cursor.execute(query)
        else:
            raise Exception(f"Unsupported database engine: {db_engine}")
        
        result = cursor.fetchone()
        return result is not None
