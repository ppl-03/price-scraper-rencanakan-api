from django.test import TestCase
from django.db import connection
from db_pricing.utils import (
    check_database_connection, 
    check_tokopedia_table_exists,
    TokopediaTableChecker,
    _validate_table_name
)
from db_pricing.models import TokopediaProduct
from unittest.mock import Mock, patch, MagicMock


class TestTokopediaDatabaseConnectionChecker(TestCase):
    """Test database connection checker utility functions for Tokopedia"""
    
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
    
    def test_check_tokopedia_table_exists_returns_true(self):
        result = check_tokopedia_table_exists()
        self.assertTrue(result['exists'])
        self.assertIsNone(result['error'])
    
    def test_check_tokopedia_table_exists_returns_column_info(self):
        result = check_tokopedia_table_exists()
        self.assertIn('columns', result)
        self.assertIsInstance(result['columns'], list)
        self.assertGreater(len(result['columns']), 0)
    
    def test_check_tokopedia_table_has_required_columns(self):
        result = check_tokopedia_table_exists()
        column_names = [col['name'] for col in result['columns']]
        
        self.assertIn('id', column_names)
        self.assertIn('name', column_names)
        self.assertIn('price', column_names)
        self.assertIn('url', column_names)
        self.assertIn('unit', column_names)
        self.assertIn('location', column_names)
        self.assertIn('created_at', column_names)
        self.assertIn('updated_at', column_names)
    
    def test_check_database_connection_handles_errors_gracefully(self):
        result = check_database_connection()
        self.assertIn('connected', result)
        self.assertIn('error', result)
    
    def test_check_tokopedia_table_exists_handles_errors_gracefully(self):
        result = check_tokopedia_table_exists()
        self.assertIn('exists', result)
        self.assertIn('error', result)
    
    def test_tokopedia_table_column_types(self):
        result = check_tokopedia_table_exists()
        columns = {col['name']: col for col in result['columns']}
        
        # Check that required columns exist and have correct structure
        self.assertIn('type', columns['id'])
        self.assertIn('type', columns['name'])
        self.assertIn('type', columns['price'])
        self.assertIn('type', columns['url'])
    
    def test_tokopedia_table_has_timestamps(self):
        result = check_tokopedia_table_exists()
        column_names = [col['name'] for col in result['columns']]
        
        self.assertIn('created_at', column_names)
        self.assertIn('updated_at', column_names)
    
    def test_check_tokopedia_table_returns_correct_column_structure(self):
        TokopediaProduct.objects.create(
            name='Test Product',
            price=10000,
            url='https://example.com/product',
            location='Jakarta'
        )
        
        result = check_tokopedia_table_exists()
        
        column_names = [col['name'] for col in result['columns']]
        
        self.assertIn('id', column_names)
        self.assertIn('name', column_names)
        self.assertIn('price', column_names)
        self.assertIn('url', column_names)
        self.assertIn('unit', column_names)
        self.assertIn('location', column_names)
        self.assertIn('created_at', column_names)
        self.assertIn('updated_at', column_names)
    
    def test_uses_mysql_for_tokopedia_table(self):
        engine = connection.settings_dict.get('ENGINE', '')
        self.assertIn('mysql', engine)


class TestTokopediaTableChecker(TestCase):
    """Test TokopediaTableChecker class and its methods"""
    
    def test_table_checker_initialization(self):
        checker = TokopediaTableChecker(connection)
        self.assertIsNotNone(checker)
        self.assertEqual(checker.TABLE_NAME, 'tokopedia_products')
    
    def test_table_checker_check_method_success(self):
        checker = TokopediaTableChecker(connection)
        result = checker.check()
        self.assertTrue(result['exists'])
        self.assertIsNone(result['error'])
        self.assertIsInstance(result['columns'], list)
    
    def test_table_checker_performs_check(self):
        checker = TokopediaTableChecker(connection)
        result = checker._perform_check()
        self.assertTrue(result['exists'])
        self.assertGreater(len(result['columns']), 0)
    
    def test_table_checker_table_exists_method(self):
        checker = TokopediaTableChecker(connection)
        with connection.cursor() as cursor:
            exists = checker._table_exists(cursor)
            self.assertTrue(exists)
    
    def test_table_checker_fetch_columns(self):
        checker = TokopediaTableChecker(connection)
        with connection.cursor() as cursor:
            columns = checker._fetch_columns(cursor)
            self.assertIsInstance(columns, list)
            self.assertGreater(len(columns), 0)
            # Verify column structure
            for col in columns:
                self.assertIn('name', col)
                self.assertIn('type', col)
                self.assertIn('null', col)
                self.assertIn('key', col)
    
    def test_table_checker_build_success_response(self):
        checker = TokopediaTableChecker(connection)
        test_columns = [{'name': 'id', 'type': 'int'}]
        result = checker._build_success_response(test_columns)
        self.assertTrue(result['exists'])
        self.assertEqual(result['columns'], test_columns)
        self.assertIsNone(result['error'])
    
    def test_table_checker_build_not_exists_response(self):
        checker = TokopediaTableChecker(connection)
        result = checker._build_not_exists_response()
        self.assertFalse(result['exists'])
        self.assertEqual(result['columns'], [])
        self.assertIn('does not exist', result['error'])
    
    def test_table_checker_handle_error(self):
        checker = TokopediaTableChecker(connection)
        test_exception = Exception("Test error")
        result = checker._handle_error(test_exception)
        self.assertFalse(result['exists'])
        self.assertEqual(result['columns'], [])
        self.assertEqual(result['error'], "Test error")
    
    @patch('db_pricing.utils.connection')
    def test_table_checker_handles_database_error(self, mock_connection):
        # Simulate database error
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_connection.cursor.return_value = mock_cursor
        
        checker = TokopediaTableChecker(mock_connection)
        result = checker.check()
        
        self.assertFalse(result['exists'])
        self.assertEqual(result['error'], "Database error")


class TestTableNameValidation(TestCase):
    """Test table name validation function"""
    
    def test_validate_table_name_valid(self):
        valid_name = _validate_table_name('tokopedia_products')
        self.assertEqual(valid_name, 'tokopedia_products')
    
    def test_validate_table_name_with_numbers(self):
        valid_name = _validate_table_name('table123')
        self.assertEqual(valid_name, 'table123')
    
    def test_validate_table_name_invalid_with_special_chars(self):
        with self.assertRaises(ValueError) as context:
            _validate_table_name('table-name')
        self.assertIn('Invalid table name', str(context.exception))
    
    def test_validate_table_name_invalid_with_spaces(self):
        with self.assertRaises(ValueError) as context:
            _validate_table_name('table name')
        self.assertIn('Invalid table name', str(context.exception))
    
    def test_validate_table_name_invalid_with_sql_injection(self):
        with self.assertRaises(ValueError) as context:
            _validate_table_name("table'; DROP TABLE users;--")
        self.assertIn('Invalid table name', str(context.exception))


class TestDatabaseConnectionEdgeCases(TestCase):
    """Test edge cases for database connection"""
    
    @patch('db_pricing.utils.connection')
    def test_database_connection_query_returns_wrong_value(self, mock_connection):
        # Simulate query returning unexpected value
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = (0,)  # Wrong value
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.settings_dict = {'NAME': 'test', 'HOST': 'localhost'}
        
        with patch('db_pricing.utils.connection', mock_connection):
            result = check_database_connection()
        
        self.assertFalse(result['connected'])
        self.assertIn('Failed to execute test query', result['error'])
    
    @patch('db_pricing.utils.connection')
    def test_database_connection_exception_handling(self, mock_connection):
        # Simulate database connection error
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(side_effect=Exception("Connection failed"))
        mock_connection.cursor.return_value = mock_cursor
        
        with patch('db_pricing.utils.connection', mock_connection):
            result = check_database_connection()
        
        self.assertFalse(result['connected'])
        self.assertIsNone(result['database'])
        self.assertIsNone(result['host'])
        self.assertIn('Connection failed', result['error'])


class TestTokopediaTableColumnDetails(TestCase):
    """Test detailed column information for Tokopedia table"""
    
    def test_all_columns_have_required_attributes(self):
        result = check_tokopedia_table_exists()
        columns = result['columns']
        
        for col in columns:
            self.assertIn('name', col)
            self.assertIn('type', col)
            self.assertIn('null', col)
            self.assertIn('key', col)
            self.assertIn('default', col)
            self.assertIn('extra', col)
    
    def test_column_nullable_status(self):
        result = check_tokopedia_table_exists()
        columns = {col['name']: col for col in result['columns']}
        
        # ID should not be nullable
        self.assertEqual(columns['id']['null'], 'NO')
        
        # Name, price, url should not be nullable
        self.assertEqual(columns['name']['null'], 'NO')
        self.assertEqual(columns['price']['null'], 'NO')
        self.assertEqual(columns['url']['null'], 'NO')
    
    def test_primary_key_column(self):
        result = check_tokopedia_table_exists()
        columns = {col['name']: col for col in result['columns']}
        
        # ID should be primary key
        self.assertEqual(columns['id']['key'], 'PRI')
        
        # ID should have auto_increment
        self.assertIn('auto_increment', columns['id']['extra'].lower())

