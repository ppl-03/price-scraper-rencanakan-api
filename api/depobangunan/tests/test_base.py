from django.test import TestCase
from django.db import connection
from django.conf import settings
import re


def _validate_table_name(table_name):
    """Validate table name to prevent SQL injection"""
    if not re.fullmatch(r"\w+", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


def _get_db_engine():
    """Get the current database engine type"""
    return settings.DATABASES['default']['ENGINE']


def _is_mysql():
    """Check if current database is MySQL"""
    return 'mysql' in _get_db_engine()


def _is_sqlite():
    """Check if current database is SQLite"""
    return 'sqlite' in _get_db_engine()


class MySQLTestCase(TestCase):
    """Base test case for MySQL/SQLite compatibility"""
    pass


def get_table_columns(table_name):
    """Get column names for a table (works with MySQL and SQLite)"""
    table_name = _validate_table_name(table_name)
    
    with connection.cursor() as cursor:
        if _is_mysql():
            cursor.execute(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                [table_name],
            )
        elif _is_sqlite():
            cursor.execute("SELECT name FROM pragma_table_info(?)", [table_name])
        else:
            raise NotImplementedError(f"Unsupported database engine: {_get_db_engine()}")
        
        return [row[0] for row in cursor.fetchall()]


def table_exists(table_name):
    """Check if a table exists in the database (works with MySQL and SQLite)"""
    table_name = _validate_table_name(table_name)
    
    with connection.cursor() as cursor:
        if _is_mysql():
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        elif _is_sqlite():
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=%s", 
                (table_name,)
            )
        else:
            raise NotImplementedError(f"Unsupported database engine: {_get_db_engine()}")
        
        return cursor.fetchone() is not None
