from django.test import TestCase
from api.mitra10.table_validator import Mitra10TableValidator
from unittest.mock import patch
from django.conf import settings

class TestMitra10TableValidator(TestCase):
    def test_check_table_exists(self):
        validator = Mitra10TableValidator()
        result = validator.check_table_exists()
        self.assertTrue(result)
    
    def test_get_table_schema(self):
        validator = Mitra10TableValidator()
        schema = validator.get_table_schema()
        self.assertIsInstance(schema, dict)
        self.assertIn('id', schema)
        self.assertIn('name', schema)
        self.assertIn('price', schema)
        self.assertIn('url', schema)
        self.assertIn('unit', schema)
        self.assertIn('created_at', schema)
        self.assertIn('updated_at', schema)
    
    def test_validate_schema(self):
        validator = Mitra10TableValidator()
        result = validator.validate_schema()
        self.assertTrue(result)
    
    def test_schema_structure(self):
        validator = Mitra10TableValidator()
        schema = validator.get_table_schema()
        
        self.assertIn('type', schema['name'])
        self.assertIn('not_null', schema['name'])
        self.assertIn('default', schema['name'])
        self.assertIn('primary_key', schema['name'])
    
    def test_id_is_primary_key(self):
        validator = Mitra10TableValidator()
        schema = validator.get_table_schema()
        self.assertTrue(schema['id']['primary_key'])
    
    def test_required_columns_exist(self):
        validator = Mitra10TableValidator()
        schema = validator.get_table_schema()
        required_columns = ['id', 'name', 'price', 'url', 'unit', 'created_at', 'updated_at']
        for col in required_columns:
            self.assertIn(col, schema)

    def test_get_query_unsupported_database(self):        
        validator = Mitra10TableValidator()
        # Mock an unsupported database engine
        with patch.object(settings, 'DATABASES', {'default': {'ENGINE': 'django.db.backends.postgresql'}}):
            validator.db_engine = 'django.db.backends.postgresql'
            with self.assertRaises(NotImplementedError):
                validator._get_query("exists")

    def test_get_table_schema_empty_result(self):      
        validator = Mitra10TableValidator()
        # Mock _run_query to return empty list
        with patch.object(validator, '_run_query', return_value=[]):
            schema = validator.get_table_schema()
            self.assertEqual(schema, {})  

    def test_validate_schema_table_not_exists(self):       
        validator = Mitra10TableValidator()
        # Mock check_table_exists to return False
        with patch.object(validator, 'check_table_exists', return_value=False):
            result = validator.validate_schema()
            self.assertFalse(result)  

    def test_get_query_mysql_exists_and_schema(self):
        """Ensure MySQL-specific queries are generated correctly."""
        validator = Mitra10TableValidator()
        validator.db_engine = 'django.db.backends.mysql'
        exists_query = validator._get_query("exists")
        schema_query = validator._get_query("schema")
        self.assertEqual(exists_query, "SHOW TABLES LIKE 'mitra10_products'")
        self.assertEqual(schema_query, "DESCRIBE mitra10_products")

    def test_get_table_schema_mysql_mapping(self):
        """Map MySQL DESCRIBE output to expected schema format."""
        validator = Mitra10TableValidator()
        validator.db_engine = 'django.db.backends.mysql'

        # Simulated MySQL DESCRIBE rows: Field, Type, Null, Key, Default, Extra
        mysql_describe_rows = [
            ['id', 'int(11)', 'NO', 'PRI', None, 'auto_increment'],
            ['name', 'varchar(255)', 'NO', '', None, ''],
            ['price', 'decimal(10,2)', 'NO', '', None, ''],
            ['url', 'varchar(255)', 'NO', '', None, ''],
            ['unit', 'varchar(50)', 'YES', '', None, ''],
            ['created_at', 'datetime', 'NO', '', None, ''],
            ['updated_at', 'datetime', 'NO', '', None, ''],
        ]

        with patch.object(validator, '_run_query', return_value=mysql_describe_rows):
            schema = validator.get_table_schema()

        # Basic shape
        self.assertIsInstance(schema, dict)
        self.assertIn('id', schema)
        self.assertTrue(schema['id']['primary_key'])
        self.assertTrue(schema['id']['not_null'])  # 'NO' -> not_null True
        self.assertEqual(schema['id']['type'], 'int(11)')

        # Nullable column
        self.assertIn('unit', schema)
        self.assertFalse(schema['unit']['not_null'])  # 'YES' -> not null False
        self.assertEqual(schema['unit']['default'], None)

        # Required columns present
        for col in ['name', 'price', 'url', 'created_at', 'updated_at']:
            self.assertIn(col, schema)

    def test_check_table_exists_mysql(self):
        """check_table_exists should return True when MySQL engine yields rows."""
        validator = Mitra10TableValidator()
        validator.db_engine = 'django.db.backends.mysql'
        with patch.object(validator, '_run_query', return_value=[('mitra10_products',)]):
            self.assertTrue(validator.check_table_exists())

    def test_validate_schema_mysql_true(self):
        """validate_schema returns True when table exists and required columns are present (MySQL)."""
        validator = Mitra10TableValidator()
        validator.db_engine = 'django.db.backends.mysql'

        fake_schema = {k: {'type': 't', 'not_null': True, 'default': None, 'primary_key': (k == 'id')}
                       for k in ['id', 'name', 'price', 'url', 'unit', 'created_at', 'updated_at']}

        with patch.object(validator, 'check_table_exists', return_value=True), \
             patch.object(validator, 'get_table_schema', return_value=fake_schema):
            self.assertTrue(validator.validate_schema())

    def test_get_query_sqlite_exists_and_schema(self):
        """Ensure SQLite-specific queries are generated correctly."""
        validator = Mitra10TableValidator()
        validator.db_engine = 'django.db.backends.sqlite3'
        exists_query = validator._get_query("exists")
        schema_query = validator._get_query("schema")
        self.assertEqual(exists_query, "SELECT name FROM sqlite_master WHERE type='table' AND name='mitra10_products'")
        self.assertEqual(schema_query, "PRAGMA table_info(mitra10_products)")

    def test_get_table_schema_sqlite_mapping(self):
        """Map SQLite PRAGMA output to expected schema format."""
        validator = Mitra10TableValidator()
        validator.db_engine = 'django.db.backends.sqlite3'

        # Simulated SQLite PRAGMA table_info rows: cid, name, type, notnull, dflt_value, pk
        sqlite_table_info_rows = [
            (0, 'id', 'INTEGER', 1, None, 1),
            (1, 'name', 'TEXT', 1, None, 0),
            (2, 'price', 'REAL', 1, None, 0),
            (3, 'url', 'TEXT', 1, None, 0),
            (4, 'unit', 'TEXT', 0, None, 0),
            (5, 'created_at', 'TEXT', 1, None, 0),
            (6, 'updated_at', 'TEXT', 1, None, 0),
        ]

        with patch.object(validator, '_run_query', return_value=sqlite_table_info_rows):
            schema = validator.get_table_schema()

        self.assertIsInstance(schema, dict)
        self.assertIn('id', schema)
        self.assertTrue(schema['id']['primary_key'])
        self.assertTrue(schema['id']['not_null'])
        self.assertEqual(schema['unit']['not_null'], False)
        self.assertEqual(schema['name']['type'], 'TEXT')