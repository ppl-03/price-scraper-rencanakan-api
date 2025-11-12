from django.test import TestCase
from django.db import connection
from db_pricing.utils import check_mitra10_table_exists
from db_pricing.models import Mitra10Product
import unittest


class TestMitra10HandshakeTest(TestCase):
    
    @unittest.skipIf(
        'sqlite' in connection.settings_dict.get('ENGINE', ''),
        "Test requires MySQL database (uses MySQL-specific table checking)"
    )
    def test_check_mitra10_table_exists_returns_true_when_table_exists(self):
        Mitra10Product.objects.create(
            name='Test Product',
            price=10000,
            url='https://example.com/product'
        )
        
        result = check_mitra10_table_exists()
        
        self.assertTrue(result['exists'])
        self.assertIsNone(result['error'])
        self.assertIsInstance(result['columns'], list)
        self.assertGreater(len(result['columns']), 0)
    
    @unittest.skipIf(
        'sqlite' in connection.settings_dict.get('ENGINE', ''),
        "Test requires MySQL database (uses MySQL-specific table checking)"
    )
    def test_check_mitra10_table_returns_correct_column_structure(self):
        Mitra10Product.objects.create(
            name='Test Product',
            price=10000,
            url='https://example.com/product'
        )
        
        result = check_mitra10_table_exists()
        
        column_names = [col['name'] for col in result['columns']]
        
        self.assertIn('id', column_names)
        self.assertIn('name', column_names)
        self.assertIn('price', column_names)
        self.assertIn('url', column_names)
        self.assertIn('unit', column_names)
        self.assertIn('created_at', column_names)
        self.assertIn('updated_at', column_names)
    
    @unittest.skipIf(
        'sqlite' in connection.settings_dict.get('ENGINE', ''),
        "Test requires MySQL database"
    )
    def test_uses_mysql_for_mitra10_table(self):
        engine = connection.settings_dict.get('ENGINE', '')
        self.assertIn('mysql', engine)
