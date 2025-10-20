from django.test import TestCase
from django.db import connection
from django.conf import settings
import re


def _validate_table_name(table_name):
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


class MySQLTestCase(TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass


def get_table_columns_mysql(table_name):
    table_name = _validate_table_name(table_name)
    with connection.cursor() as cursor:
        query = "DESCRIBE {}".format(table_name)
        cursor.execute(query)
        columns = cursor.fetchall()
        return [col[0] for col in columns]


def get_table_columns_sqlite(table_name):
    table_name = _validate_table_name(table_name)
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
    table_name = _validate_table_name(table_name)
    db_engine = settings.DATABASES['default']['ENGINE']
    
    with connection.cursor() as cursor:
        if 'mysql' in db_engine:
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        elif 'sqlite' in db_engine:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s", (table_name,))
        else:
            raise Exception(f"Unsupported database engine: {db_engine}")
        
        result = cursor.fetchone()
        return result is not None
