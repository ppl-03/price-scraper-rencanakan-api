from api.gemilang.table_validator import GemilangTableValidator
from .test_base import MySQLTestCase

class TestGemilangTableValidator(MySQLTestCase):
    def setUp(self):
        self.validator = GemilangTableValidator()
    
    def test_table_exists(self):
        result = self.validator.check_table_exists()
        self.assertTrue(result)
    
    def test_table_schema_has_id_column(self):
        schema = self.validator.get_table_schema()
        self.assertIn('id', schema)
        self.assertTrue(schema['id']['primary_key'])
    
    def test_table_schema_has_name_column(self):
        schema = self.validator.get_table_schema()
        self.assertIn('name', schema)
    
    def test_table_schema_has_price_column(self):
        schema = self.validator.get_table_schema()
        self.assertIn('price', schema)
    
    def test_table_schema_has_url_column(self):
        schema = self.validator.get_table_schema()
        self.assertIn('url', schema)
    
    def test_table_schema_has_unit_column(self):
        schema = self.validator.get_table_schema()
        self.assertIn('unit', schema)
    
    def test_table_schema_has_created_at_column(self):
        schema = self.validator.get_table_schema()
        self.assertIn('created_at', schema)
    
    def test_table_schema_has_updated_at_column(self):
        schema = self.validator.get_table_schema()
        self.assertIn('updated_at', schema)
    
    def test_get_record_count_empty_table(self):
        count = self.validator.get_record_count()
        self.assertEqual(count, 0)
    
    def test_get_all_records_empty_table(self):
        records = self.validator.get_all_records()
        self.assertEqual(len(records), 0)
        self.assertIsInstance(records, list)
    
    def test_get_record_by_name_not_found(self):
        record = self.validator.get_record_by_name("Nonexistent")
        self.assertIsNone(record)
    
    def test_get_record_by_name_found(self):
        GemilangProduct.objects.create(
            name="Findable Product",
            price=15000,
            url="https://test.com/findable",
            unit="PCS"
        )
        
        record = self.validator.get_record_by_name("Findable Product")
        
        self.assertIsNotNone(record)
        self.assertIsInstance(record, dict)
        self.assertEqual(record['name'], "Findable Product")
        self.assertEqual(record['price'], 15000)
        self.assertEqual(record['url'], "https://test.com/findable")
        self.assertEqual(record['unit'], "PCS")
        self.assertIn('id', record)
        self.assertIn('created_at', record)
        self.assertIn('updated_at', record)
    
    def test_get_all_tables_mysql(self):
        tables = self.validator.get_all_tables()
        self.assertIsInstance(tables, list)
        self.assertIn('gemilang_products', tables)


from unittest.mock import patch, MagicMock
from django.db import connection
from db_pricing.models import GemilangProduct


class TestTableValidatorCoverage(MySQLTestCase):
    
    def setUp(self):
        self.validator = GemilangTableValidator()
    
    @patch('api.gemilang.table_validator.connection')
    @patch('django.conf.settings')
    def test_check_table_exists_with_sqlite(self, mock_settings, mock_connection):
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3'
            }
        }
        
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('gemilang_products',)
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        validator = GemilangTableValidator()
        result = validator.check_table_exists()
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0][0]
        self.assertIn("sqlite_master", call_args)
    
    @patch('django.conf.settings')
    def test_check_table_exists_with_unsupported_engine(self, mock_settings):
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql'
            }
        }
        
        validator = GemilangTableValidator()
        
        with self.assertRaises(Exception) as context:
            validator.check_table_exists()
        
        self.assertIn("Unsupported database engine", str(context.exception))
    
    @patch('api.gemilang.table_validator.connection')
    @patch('django.conf.settings')
    def test_get_table_schema_with_sqlite(self, mock_settings, mock_connection):
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3'
            }
        }
        
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (0, 'id', 'INTEGER', 0, None, 1),
            (1, 'name', 'VARCHAR(500)', 1, None, 0),
            (2, 'price', 'INTEGER', 1, None, 0),
        ]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        validator = GemilangTableValidator()
        schema = validator.get_table_schema()
        
        self.assertIsInstance(schema, dict)
        self.assertIn('id', schema)
        self.assertIn('name', schema)
        self.assertIn('type', schema['id'])
        self.assertIn('primary_key', schema['id'])
        self.assertTrue(schema['id']['primary_key'])
    
    @patch('django.conf.settings')
    def test_get_table_schema_with_unsupported_engine(self, mock_settings):
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql'
            }
        }
        
        validator = GemilangTableValidator()
        
        with self.assertRaises(Exception) as context:
            validator.get_table_schema()
        
        self.assertIn("Unsupported database engine", str(context.exception))
    
    def test_clear_table(self):
        GemilangProduct.objects.create(
            name="Product to Clear 1",
            price=10000,
            url="https://test.com/1",
            unit="PCS"
        )
        GemilangProduct.objects.create(
            name="Product to Clear 2",
            price=20000,
            url="https://test.com/2",
            unit="BOX"
        )
        
        count_before = GemilangProduct.objects.count()
        self.assertGreater(count_before, 0)
        
        self.validator.clear_table()
        
        count_after = GemilangProduct.objects.count()
        self.assertEqual(count_after, 0)
    
    @patch('api.gemilang.table_validator.connection')
    @patch('django.conf.settings')
    def test_get_all_tables_with_sqlite(self, mock_settings, mock_connection):
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3'
            }
        }
        
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('gemilang_products',),
            ('auth_user',),
            ('django_session',),
        ]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        validator = GemilangTableValidator()
        tables = validator.get_all_tables()
        
        self.assertIsInstance(tables, list)
        self.assertIn('gemilang_products', tables)
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0][0]
        self.assertIn("sqlite_master", call_args)
    
    @patch('django.conf.settings')
    def test_get_all_tables_with_unsupported_engine(self, mock_settings):
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql'
            }
        }
        
        validator = GemilangTableValidator()
        
        with self.assertRaises(Exception) as context:
            validator.get_all_tables()
        
        self.assertIn("Unsupported database engine", str(context.exception))


class TestTableValidatorGetAllRecords(MySQLTestCase):
    
    def test_get_all_records_with_data(self):
        validator = GemilangTableValidator()
        
        validator.clear_table()
        
        GemilangProduct.objects.create(
            name="Product A",
            price=10000,
            url="https://test.com/a",
            unit="PCS"
        )
        GemilangProduct.objects.create(
            name="Product B",
            price=20000,
            url="https://test.com/b",
            unit="BOX"
        )
        
        records = validator.get_all_records()
        
        self.assertIsInstance(records, list)
        self.assertEqual(len(records), 2)
        
        first_record = records[0]
        self.assertIn('id', first_record)
        self.assertIn('name', first_record)
        self.assertIn('price', first_record)
        self.assertIn('url', first_record)
        self.assertIn('unit', first_record)
        self.assertIn('created_at', first_record)
        self.assertIn('updated_at', first_record)


class TestTableValidatorMySQLPaths(MySQLTestCase):
    """Test MySQL-specific code paths"""
    
    @patch('api.gemilang.table_validator.connection')
    @patch('django.conf.settings')
    def test_check_table_exists_with_mysql(self, mock_settings, mock_connection):
        """Test check_table_exists with MySQL engine"""
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql'
            }
        }
        
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('gemilang_products',)
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        validator = GemilangTableValidator()
        result = validator.check_table_exists()
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0][0]
        self.assertIn("SHOW TABLES", call_args)
    
    @patch('api.gemilang.table_validator.connection')
    @patch('django.conf.settings')
    def test_get_table_schema_with_mysql(self, mock_settings, mock_connection):
        """Test get_table_schema with MySQL engine"""
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql'
            }
        }
        
        mock_cursor = MagicMock()
        # MySQL DESCRIBE returns: Field, Type, Null, Key, Default, Extra
        mock_cursor.fetchall.return_value = [
            ('id', 'int(11)', 'NO', 'PRI', None, 'auto_increment'),
            ('name', 'varchar(500)', 'NO', '', None, ''),
            ('price', 'int(11)', 'NO', '', None, ''),
        ]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        validator = GemilangTableValidator()
        schema = validator.get_table_schema()
        
        self.assertIsInstance(schema, dict)
        self.assertIn('id', schema)
        self.assertIn('name', schema)
        self.assertIn('price', schema)
        self.assertTrue(schema['id']['primary_key'])
        self.assertTrue(schema['id']['not_null'])
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0][0]
        self.assertIn("DESCRIBE", call_args)
    
    @patch('api.gemilang.table_validator.connection')
    @patch('django.conf.settings')
    def test_get_all_tables_with_mysql(self, mock_settings, mock_connection):
        """Test get_all_tables with MySQL engine"""
        mock_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql'
            }
        }
        
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('gemilang_products',),
            ('auth_user',),
            ('django_session',),
        ]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        validator = GemilangTableValidator()
        tables = validator.get_all_tables()
        
        self.assertIsInstance(tables, list)
        self.assertIn('gemilang_products', tables)
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0][0]
        self.assertIn("SHOW TABLES", call_args)
