from django.test import TestCase
from django.db import connection
from django.conf import settings
import re


def _validate_table_name(table_name):
    if not re.fullmatch(r"\w+", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


class MySQLTestCase(TestCase):
    """Base test class for MySQL and SQLite database operations."""

    def setUp(self):
        """
        Setup method intentionally left empty.
        Django TestCase handles database setup automatically (transaction-based),
        so no manual setup is needed for basic test operations.
        """
        pass

    def tearDown(self):
        """
        Teardown method intentionally left empty.
        Django TestCase handles database cleanup automatically (transaction rollback),
        so no manual teardown is needed for basic test operations.
        """
        pass

    # Shared helper for executing a query
    def _fetch_columns(self, query, params):
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return [row[0] for row in cursor.fetchall()]


def get_table_columns(table_name):
    """Fetches ordered column names for a given table based on DB engine."""
    table_name = _validate_table_name(table_name)
    db_engine = settings.DATABASES["default"]["ENGINE"]

    mysql_query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
    """
    sqlite_query = "SELECT name FROM pragma_table_info(?)"

    with connection.cursor() as cursor:
        if "mysql" in db_engine:
            cursor.execute(mysql_query, [table_name])
        elif "sqlite" in db_engine:
            cursor.execute(sqlite_query, [table_name])
        else:
            raise NotImplementedError(f"Unsupported database engine: {db_engine}")
        return [row[0] for row in cursor.fetchall()]


def table_exists(table_name):
    """Checks whether a table exists in the current database."""
    table_name = _validate_table_name(table_name)
    db_engine = settings.DATABASES["default"]["ENGINE"]

    query_map = {
        "mysql": ("SHOW TABLES LIKE %s", (table_name,)),
        "sqlite": ("SELECT name FROM sqlite_master WHERE type='table' AND name=%s", (table_name,)),
    }

    with connection.cursor() as cursor:
        if "mysql" in db_engine:
            cursor.execute(*query_map["mysql"])
        elif "sqlite" in db_engine:
            cursor.execute(*query_map["sqlite"])
        else:
            raise NotImplementedError(f"Unsupported database engine: {db_engine}")
        return cursor.fetchone() is not None
