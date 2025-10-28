from django.test import TestCase
from django.db import connection
from django.conf import settings
import re


def _validate_table_name(table_name):
    if not re.fullmatch(r"\w+", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


class MySQLTestCase(TestCase):
    """Base test case class for MySQL database tests. Inherits from Django's TestCase."""
    
    def setUp(self):
        """Set up test fixtures. Currently no setup required as Django handles test database."""
        pass
    
    def tearDown(self):
        """Clean up after tests. Clear GemilangProduct table to ensure test isolation."""
        from db_pricing.models import GemilangProduct
        GemilangProduct.objects.all().delete()


def get_table_columns_mysql(table_name):
    table_name = _validate_table_name(table_name)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            [table_name],
        )
        return [row[0] for row in cursor.fetchall()]


def get_table_columns_sqlite(table_name):
    table_name = _validate_table_name(table_name)
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM pragma_table_info(?)", [table_name])
        return [row[0] for row in cursor.fetchall()]


def get_table_columns(table_name):
    """Get table column names for the current database engine."""
    db_engine = settings.DATABASES['default']['ENGINE']
    
    if 'mysql' in db_engine:
        return get_table_columns_mysql(table_name)
    elif 'sqlite' in db_engine:
        return get_table_columns_sqlite(table_name)
    else:
        raise NotImplementedError(f"Unsupported database engine: {db_engine}")


def table_exists(table_name):
    """Check if a table exists in the database."""
    table_name = _validate_table_name(table_name)
    db_engine = settings.DATABASES['default']['ENGINE']
    
    with connection.cursor() as cursor:
        if 'mysql' in db_engine:
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        elif 'sqlite' in db_engine:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s", (table_name,))
        else:
            raise NotImplementedError(f"Unsupported database engine: {db_engine}")
        
        result = cursor.fetchone()
        return result is not None
