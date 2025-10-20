"""
Base test configuration for Gemilang tests
Forces MySQL database connection for all tests
"""
import os

# Force MySQL connection for tests
os.environ['USE_SQLITE_FOR_TESTS'] = 'false'

from django.test import TestCase
from django.db import connection
from django.conf import settings


class MySQLTestCase(TestCase):
    """
    Base test case that ensures MySQL is being used
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Verify we're using MySQL
        db_engine = settings.DATABASES['default']['ENGINE']
        if 'mysql' not in db_engine:
            raise RuntimeError(
                f"Tests must run on MySQL! Currently using: {db_engine}. "
                f"Set USE_SQLITE_FOR_TESTS=false environment variable."
            )
    
    def get_database_engine(self):
        """Helper to get database engine type"""
        return settings.DATABASES['default']['ENGINE']
    
    def is_mysql(self):
        """Check if using MySQL"""
        return 'mysql' in self.get_database_engine()
    
    def is_sqlite(self):
        """Check if using SQLite"""
        return 'sqlite' in self.get_database_engine()


def get_table_columns_mysql(table_name):
    """
    Get table columns for MySQL database
    """
    with connection.cursor() as cursor:
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        # Column name is at index 0 in DESCRIBE output
        return [col[0] for col in columns]


def get_table_columns_sqlite(table_name):
    """
    Get table columns for SQLite database
    """
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        # Column name is at index 1 in PRAGMA output
        return [col[1] for col in columns]


def get_table_columns(table_name):
    """
    Get table columns for any database
    """
    db_engine = settings.DATABASES['default']['ENGINE']
    if 'mysql' in db_engine:
        return get_table_columns_mysql(table_name)
    elif 'sqlite' in db_engine:
        return get_table_columns_sqlite(table_name)
    else:
        raise Exception(f"Unsupported database engine: {db_engine}")


def table_exists(table_name):
    """
    Check if table exists in database
    """
    db_engine = settings.DATABASES['default']['ENGINE']
    
    with connection.cursor() as cursor:
        if 'mysql' in db_engine:
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        elif 'sqlite' in db_engine:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        else:
            raise Exception(f"Unsupported database engine: {db_engine}")
        
        result = cursor.fetchone()
        return result is not None
