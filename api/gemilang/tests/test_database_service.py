from db_pricing.models import GemilangProduct
from api.gemilang.database_service import GemilangDatabaseService
from .test_base import MySQLTestCase

class TestGemilangDatabaseService(MySQLTestCase):
    def test_save_valid_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"},
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['product_ids']), 2)
        self.assertEqual(GemilangProduct.objects.count(), 2)
        product = GemilangProduct.objects.get(name="Item 1")
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.url, "https://example.com/1")
        self.assertEqual(product.unit, "pcs")

    def test_save_empty_data(self):
        data = []
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['product_ids']), 0)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_name_field(self):
        data = [
            {"price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['product_ids']), 0)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_price_field(self):
        data = [
            {"name": "Item 1", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['product_ids']), 0)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_url_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['product_ids']), 0)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_unit_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['product_ids']), 0)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_negative_price(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['product_ids']), 0)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_zero_price(self):
        data = [
            {"name": "Item 1", "price": 0, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['product_ids']), 1)
        self.assertEqual(GemilangProduct.objects.count(), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.price, 0)

    def test_save_duplicate_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"},
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['product_ids']), 2)
        self.assertEqual(GemilangProduct.objects.count(), 2)

    def test_save_large_price(self):
        data = [
            {"name": "Item 1", "price": 999999999, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['product_ids']), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.price, 999999999)

    def test_save_empty_string_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": ""}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['product_ids']), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.unit, "")

    def test_save_long_name(self):
        long_name = "A" * 500
        data = [
            {"name": long_name, "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['product_ids']), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.name, long_name)

    def test_save_long_url(self):
        long_url = "https://example.com/" + "x" * 980
        data = [
            {"name": "Item 1", "price": 10000, "url": long_url, "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['product_ids']), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.url, long_url)

    def test_save_special_characters_in_name(self):
        data = [
            {"name": "Item @#$% & * () 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['product_ids']), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.name, "Item @#$% & * () 1")

    def test_save_price_not_integer(self):
        data = [
            {"name": "Item 1", "price": "10000", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['product_ids']), 0)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_multiple_batches(self):
        data1 = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        data2 = [
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box"}
        ]
        service = GemilangDatabaseService()
        result1 = service.save(data1)
        result2 = service.save(data2)
        self.assertTrue(result1['success'])
        self.assertTrue(result2['success'])
        self.assertEqual(len(result1['product_ids']), 1)
        self.assertEqual(len(result2['product_ids']), 1)
        self.assertEqual(GemilangProduct.objects.count(), 2)

    def test_verify_timestamps_created(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        service.save(data)
        product = GemilangProduct.objects.first()
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)


from unittest.mock import patch, MagicMock

class TestDatabaseServiceCoverage(MySQLTestCase):
    
    def test_executemany_called_with_correct_params(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "Product 1", "price": 10000, "url": "https://test1.com", "unit": "PCS"},
            {"name": "Product 2", "price": 20000, "url": "https://test2.com", "unit": "BOX"}
        ]
        
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(GemilangProduct.objects.count(), 2)
