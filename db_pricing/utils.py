from django.db import connection
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


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
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'gemilang_products'")
            result = cursor.fetchone()
            
            if not result:
                return {
                    'exists': False,
                    'columns': [],
                    'error': 'Table gemilang_products does not exist'
                }
            
            cursor.execute("DESCRIBE gemilang_products")
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
