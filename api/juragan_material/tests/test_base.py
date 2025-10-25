"""
Test utilities for juragan_material module.
Imports from local db_test_utils to avoid code duplication.
"""
from ..db_test_utils import (
    MySQLTestCase,
    get_table_columns_mysql,
    get_table_columns_sqlite, 
    get_table_columns,
    table_exists
)