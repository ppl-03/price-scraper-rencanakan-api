from django.test import TestCase
from db_pricing.utils import check_database_connection, check_gemilang_table_exists


class TestDatabaseConnectionChecker(TestCase):
    
    def test_check_database_connection_returns_true_when_connected(self):
        result = check_database_connection()
        self.assertTrue(result['connected'])
        self.assertIsNone(result['error'])
    
    def test_check_database_connection_returns_database_name(self):
        result = check_database_connection()
        self.assertIn('database', result)
        self.assertIsNotNone(result['database'])
    
    def test_check_database_connection_returns_host(self):
        result = check_database_connection()
        self.assertIn('host', result)
        self.assertIsNotNone(result['host'])
    
    def test_check_gemilang_table_exists_returns_true(self):
        result = check_gemilang_table_exists()
        self.assertTrue(result['exists'])
        self.assertIsNone(result['error'])
    
    def test_check_gemilang_table_exists_returns_column_info(self):
        result = check_gemilang_table_exists()
        self.assertIn('columns', result)
        self.assertIsInstance(result['columns'], list)
        self.assertGreater(len(result['columns']), 0)
    
    def test_check_gemilang_table_has_required_columns(self):
        result = check_gemilang_table_exists()
        column_names = [col['name'] for col in result['columns']]
        
        self.assertIn('id', column_names)
        self.assertIn('name', column_names)
        self.assertIn('price', column_names)
        self.assertIn('url', column_names)
        self.assertIn('unit', column_names)
        self.assertIn('created_at', column_names)
        self.assertIn('updated_at', column_names)
    
    def test_check_database_connection_handles_errors_gracefully(self):
        result = check_database_connection()
        self.assertIn('connected', result)
        self.assertIn('error', result)
    
    def test_check_gemilang_table_exists_handles_errors_gracefully(self):
        result = check_gemilang_table_exists()
        self.assertIn('exists', result)
        self.assertIn('error', result)
