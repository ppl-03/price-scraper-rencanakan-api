from django.test import TestCase
from api.mitra10.table_validator import Mitra10TableValidator

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
