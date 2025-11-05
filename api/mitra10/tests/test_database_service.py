from django.test import TestCase
from db_pricing.models import Mitra10Product
from api.mitra10.database_service import Mitra10DatabaseService

class TestMitra10DatabaseService(TestCase):
    def setUp(self):
        Mitra10Product.objects.all().delete()
    
    def test_save_valid_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"},
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(Mitra10Product.objects.count(), 2)
        product = Mitra10Product.objects.get(name="Item 1")
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.url, "https://example.com/1")
        self.assertEqual(product.unit, "pcs")

    def test_save_empty_data(self):
        data = []
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_missing_name_field(self):
        data = [
            {"price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_missing_price_field(self):
        data = [
            {"name": "Item 1", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_missing_url_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_missing_unit_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_negative_price(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_zero_price(self):
        data = [
            {"name": "Item 1", "price": 0, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(Mitra10Product.objects.count(), 1)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.price, 0)

    def test_save_duplicate_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"},
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(Mitra10Product.objects.count(), 2)

    def test_save_large_price(self):
        data = [
            {"name": "Item 1", "price": 999999999, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.price, 999999999)

    def test_save_string_price(self):
        data = [
            {"name": "Item 1", "price": "10000", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)

    def test_save_long_product_name(self):
        long_name = "A" * 500
        data = [
            {"name": long_name, "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.name, long_name)

    def test_save_empty_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": ""}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.unit, "")

    def test_save_multiple_items(self):
        data = [
            {"name": f"Item {i}", "price": 1000 * i, "url": f"https://example.com/{i}", "unit": "pcs"}
            for i in range(1, 11)
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(Mitra10Product.objects.count(), 10)

    def test_save_with_special_characters_in_name(self):
        data = [
            {"name": "Item & Special <> Characters", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.name, "Item & Special <> Characters")

    def test_save_with_special_characters_in_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "m²"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.unit, "m²")

    def test_save_with_none_data(self):
        data = None
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_validate_data_valid(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service._validate_data(data)
        self.assertTrue(result)

    def test_validate_data_invalid(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = Mitra10DatabaseService()
        result = service._validate_data(data)
        self.assertFalse(result)

    def test_detect_anomaly_with_zero_old_price(self):
        """Test that no anomaly is detected when old price is 0"""
        service = Mitra10DatabaseService()
        item = {"name": "Test Item", "url": "http://test.com", "unit": "pcs"}
        result = service._detect_anomaly(item, 0, 10000)
        self.assertIsNone(result)
