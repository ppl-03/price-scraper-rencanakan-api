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
        success, error_msg = service.save(data)
        self.assertTrue(success)
        self.assertEqual(error_msg, "")
        self.assertEqual(GemilangProduct.objects.count(), 2)
        product = GemilangProduct.objects.get(name="Item 1")
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.url, "https://example.com/1")
        self.assertEqual(product.unit, "pcs")

    def test_save_empty_data(self):
        data = []
        service = GemilangDatabaseService()
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("cannot be empty", error_msg)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_name_field(self):
        data = [
            {"price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("missing required fields", error_msg)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_price_field(self):
        data = [
            {"name": "Item 1", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("missing required fields", error_msg)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_url_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("missing required fields", error_msg)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_unit_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1"}
        ]
        service = GemilangDatabaseService()
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("missing required fields", error_msg)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_negative_price(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("must be non-negative", error_msg)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_zero_price(self):
        data = [
            {"name": "Item 1", "price": 0, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        self.assertEqual(GemilangProduct.objects.count(), 1)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.price, 0)

    def test_save_duplicate_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"},
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        self.assertEqual(GemilangProduct.objects.count(), 2)

    def test_save_large_price(self):
        data = [
            {"name": "Item 1", "price": 999999999, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.price, 999999999)

    def test_save_empty_string_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": ""}
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.unit, "")

    def test_save_long_name(self):
        long_name = "A" * 500
        data = [
            {"name": long_name, "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.name, long_name)

    def test_save_long_url(self):
        long_url = "https://example.com/" + "x" * 980
        data = [
            {"name": "Item 1", "price": 10000, "url": long_url, "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.url[:1000], long_url[:1000])

    def test_save_special_characters_in_name(self):
        data = [
            {"name": "Item Test 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.name, "Item Test 1")

    def test_save_price_not_integer(self):
        data = [
            {"name": "Item 1", "price": "10000", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("must be a number", error_msg)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_multiple_batches(self):
        data1 = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        data2 = [
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box"}
        ]
        service = GemilangDatabaseService()
        success1, _ = service.save(data1)
        success2, _ = service.save(data2)
        self.assertTrue(success1)
        self.assertTrue(success2)
        self.assertEqual(GemilangProduct.objects.count(), 2)

    def test_verify_timestamps_created(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        _, _ = service.save(data)
        product = GemilangProduct.objects.first()
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)

    def test_save_with_location(self):
        data = [
            {
                "name": "Item 1", 
                "price": 10000, 
                "url": "https://example.com/1", 
                "unit": "pcs",
                "location": "GEMILANG - BANJARMASIN SUTOYO"
            }
        ]
        service = GemilangDatabaseService()
        success, error_msg = service.save(data)
        self.assertTrue(success)
        self.assertEqual(error_msg, "")
        product = GemilangProduct.objects.first()
        self.assertEqual(product.location, "GEMILANG - BANJARMASIN SUTOYO")

    def test_save_with_multiple_locations(self):
        location_string = "GEMILANG - BANJARMASIN SUTOYO, GEMILANG - BANJARMASIN KM, GEMILANG - BANJARBARU, GEMILANG - PALANGKARAYA, GEMILANG - PALANGKARAYA KM.8"
        data = [
            {
                "name": "Item 1", 
                "price": 10000, 
                "url": "https://example.com/1", 
                "unit": "pcs",
                "location": location_string
            }
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.location, location_string)

    def test_save_without_location(self):
        data = [
            {
                "name": "Item 1", 
                "price": 10000, 
                "url": "https://example.com/1", 
                "unit": "pcs"
            }
        ]
        service = GemilangDatabaseService()
        success, _ = service.save(data)
        self.assertTrue(success)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.location, "")


from unittest.mock import patch, MagicMock

class TestDatabaseServiceCoverage(MySQLTestCase):
    
    def test_executemany_called_with_correct_params(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "Product 1", "price": 10000, "url": "https://test1.com", "unit": "PCS"},
            {"name": "Product 2", "price": 20000, "url": "https://test2.com", "unit": "BOX"}
        ]
        
        success, _ = service.save(data)
        self.assertTrue(success)
        self.assertEqual(GemilangProduct.objects.count(), 2)


class TestDatabaseServiceSecurity(MySQLTestCase):
    
    def test_save_rejects_ssrf_localhost(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://localhost/admin", "unit": "pcs"}
        ]
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("invalid URL", error_msg)
    
    def test_save_rejects_ssrf_127(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://127.0.0.1/secret", "unit": "pcs"}
        ]
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("invalid URL", error_msg)
    
    def test_save_rejects_price_exceeds_limit(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "Item 1", "price": 2000000000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("exceeds reasonable limit", error_msg)
    
    def test_save_rejects_short_name(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "A", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("length must be between", error_msg)
    
    def test_save_rejects_very_long_name(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "A" * 501, "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("length must be between", error_msg)
    
    def test_save_rejects_invalid_url_format(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "Item 1", "price": 10000, "url": "not-a-url", "unit": "pcs"}
        ]
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("must use HTTPS protocol", error_msg)
    
    def test_save_rejects_long_unit(self):
        service = GemilangDatabaseService()
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "x" * 51}
        ]
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("unit too long", error_msg)
    
    def test_save_rejects_non_dict_item(self):
        service = GemilangDatabaseService()
        data = ["not a dict"]
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("must be a dictionary", error_msg)
    
    def test_save_rejects_non_list_data(self):
        service = GemilangDatabaseService()
        data = {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        success, error_msg = service.save(data)
        self.assertFalse(success)
        self.assertIn("must be a list", error_msg)
