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
