from django.db import connection
from typing import Dict, List, Any, Protocol
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection(Protocol):
    def cursor(self): ...
    settings_dict: Dict[str, Any]


class Mitra10TableChecker:
    TABLE_NAME = 'mitra10_products'
    
    def __init__(self, db_connection: DatabaseConnection):
        self._connection = db_connection
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def check(self) -> Dict[str, Any]:
        try:
            return self._perform_check()
        except Exception as e:
            return self._handle_error(e)
    
    def _perform_check(self) -> Dict[str, Any]:
        with self._connection.cursor() as cursor:
            if not self._table_exists(cursor):
                return self._build_not_exists_response()
            
            columns = self._fetch_columns(cursor)
            return self._build_success_response(columns)
    
    def _table_exists(self, cursor) -> bool:
        cursor.execute("SHOW TABLES LIKE %s", [self.TABLE_NAME])
        return cursor.fetchone() is not None
    
    def _fetch_columns(self, cursor) -> List[Dict[str, Any]]:
        table_name = self.TABLE_NAME
        if not table_name.replace('_', '').isalnum():
            raise ValueError(f"Invalid table name: {table_name}")
        cursor.execute(f"DESCRIBE `{table_name}`")
        columns_data = cursor.fetchall()
        
        return [
            {
                'name': col[0],
                'type': col[1],
                'null': col[2],
                'key': col[3],
                'default': col[4],
                'extra': col[5]
            }
            for col in columns_data
        ]
    
    def _build_not_exists_response(self) -> Dict[str, Any]:
        return {
            'exists': False,
            'columns': [],
            'error': f'Table {self.TABLE_NAME} does not exist'
        }
    
    def _build_success_response(self, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            'exists': True,
            'columns': columns,
            'error': None
        }
    
    def _handle_error(self, exception: Exception) -> Dict[str, Any]:
        self._logger.error(f"Table existence check failed: {str(exception)}")
        return {
            'exists': False,
            'columns': [],
            'error': str(exception)
        }


def check_database_connection() -> Dict[str, Any]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                return {
                    'connected': True,
                    'database': connection.settings_dict.get('NAME'),
                    'host': connection.settings_dict.get('HOST'),
                    'error': None
                }
            else:
                return {
                    'connected': False,
                    'database': None,
                    'host': None,
                    'error': 'Failed to execute test query'
                }
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return {
            'connected': False,
            'database': None,
            'host': None,
            'error': str(e)
        }


def check_gemilang_table_exists() -> Dict[str, Any]:
    table_name = 'gemilang_products'
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE %s", [table_name])
            result = cursor.fetchone()
            
            if not result:
                return {
                    'exists': False,
                    'columns': [],
                    'error': f'Table {table_name} does not exist'
                }
            
            if not table_name.replace('_', '').isalnum():
                raise ValueError(f"Invalid table name: {table_name}")
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns_data = cursor.fetchall()
            
            columns = []
            for col in columns_data:
                columns.append({
                    'name': col[0],
                    'type': col[1],
                    'null': col[2],
                    'key': col[3],
                    'default': col[4],
                    'extra': col[5]
                })
            
            return {
                'exists': True,
                'columns': columns,
                'error': None
            }
    except Exception as e:
        logger.error(f"Table existence check failed: {str(e)}")
        return {
            'exists': False,
            'columns': [],
            'error': str(e)
        }


def check_mitra10_table_exists() -> Dict[str, Any]:
    checker = Mitra10TableChecker(connection)
    return checker.check()
