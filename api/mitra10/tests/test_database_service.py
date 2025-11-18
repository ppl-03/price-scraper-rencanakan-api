from django.test import TestCase
from db_pricing.models import Mitra10Product
from api.mitra10.database_service import Mitra10DatabaseService

class TestMitra10DatabaseService(TestCase):
    def setUp(self):
        Mitra10Product.objects.all().delete()
    
    def test_save_valid_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"},
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box", "location": "Bandung"}
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
            {"price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_missing_price_field(self):
        data = [
            {"name": "Item 1", "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_missing_url_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_missing_unit_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_negative_price(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(Mitra10Product.objects.count(), 0)

    def test_save_zero_price(self):
        data = [
            {"name": "Item 1", "price": 0, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(Mitra10Product.objects.count(), 1)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.price, 0)

    def test_save_duplicate_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"},
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(Mitra10Product.objects.count(), 2)

    def test_save_large_price(self):
        data = [
            {"name": "Item 1", "price": 999999999, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.price, 999999999)

    def test_save_string_price(self):
        data = [
            {"name": "Item 1", "price": "10000", "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertFalse(result)

    def test_save_long_product_name(self):
        long_name = "A" * 500
        data = [
            {"name": long_name, "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.name, long_name)

    def test_save_empty_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.unit, "")

    def test_save_multiple_items(self):
        data = [
            {"name": f"Item {i}", "price": 1000 * i, "url": f"https://example.com/{i}", "unit": "pcs", "location": "City"}
            for i in range(1, 11)
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(Mitra10Product.objects.count(), 10)

    def test_save_with_special_characters_in_name(self):
        data = [
            {"name": "Item & Special <> Characters", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.name, "Item & Special <> Characters")

    def test_save_with_special_characters_in_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "m²", "location": "Jakarta"}
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
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service._validate_data(data)
        self.assertTrue(result)

    def test_validate_data_invalid(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service._validate_data(data)
        self.assertFalse(result)

    def test_detect_anomaly_with_zero_old_price(self):
        """Test that no anomaly is detected when old price is 0"""
        service = Mitra10DatabaseService()
        item = {"name": "Test Item", "url": "https://test.com", "unit": "pcs", "location": "Jakarta"}
        result = service._detect_anomaly(item, 0, 10000)
        self.assertIsNone(result)

    def test_detect_anomaly_with_increase_above_15_percent(self):
        """Test that anomaly is detected when price increases by 15% or more"""
        service = Mitra10DatabaseService()
        item = {"name": "Test Item", "url": "https://test.com", "unit": "pcs", "location": "Jakarta"}
        result = service._detect_anomaly(item, 10000, 12000)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Test Item")
        self.assertEqual(result["old_price"], 10000)
        self.assertEqual(result["new_price"], 12000)
        self.assertEqual(result["change_percent"], 20.0)

    def test_detect_anomaly_with_decrease_above_15_percent(self):
        """Test that anomaly is detected when price decreases by 15% or more"""
        service = Mitra10DatabaseService()
        item = {"name": "Test Item", "url": "https://test.com", "unit": "pcs", "location": "Jakarta"}
        result = service._detect_anomaly(item, 10000, 8000)
        self.assertIsNotNone(result)
        self.assertEqual(result["change_percent"], -20.0)

    def test_detect_anomaly_below_15_percent(self):
        """Test that no anomaly is detected when price change is below 15%"""
        service = Mitra10DatabaseService()
        item = {"name": "Test Item", "url": "https://test.com", "unit": "pcs", "location": "Jakarta"}
        result = service._detect_anomaly(item, 10000, 11000)
        self.assertIsNone(result)

    def test_save_with_price_update_insert_new_product(self):
        """Test save_with_price_update inserts a new product"""
        data = [
            {"name": "New Item", "price": 10000, "url": "https://example.com/new", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
        self.assertEqual(Mitra10Product.objects.count(), 1)

    def test_save_with_price_update_update_existing_product_no_anomaly(self):
        """Test save_with_price_update updates existing product without anomaly"""
        # Create existing product
        Mitra10Product.objects.create(
            name="Existing Item", 
            price=10000, 
            url="https://example.com/existing", 
            unit="pcs",
            location="Jakarta"
        )
        
        # Update with small price change (< 15%)
        data = [
            {"name": "Existing Item", "price": 11000, "url": "https://example.com/existing", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 0)
        
        product = Mitra10Product.objects.get(name="Existing Item")
        self.assertEqual(product.price, 11000)

    def test_save_with_price_update_update_existing_product_with_anomaly(self):
        """Test save_with_price_update detects anomaly on large price change"""
        # Create existing product
        Mitra10Product.objects.create(
            name="Existing Item", 
            price=10000, 
            url="https://example.com/existing", 
            unit="pcs",
            location="Jakarta"
        )
        
        # Update with large price change (>= 15%)
        data = [
            {"name": "Existing Item", "price": 12000, "url": "https://example.com/existing", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["name"], "Existing Item")
        self.assertEqual(anomaly["old_price"], 10000)
        self.assertEqual(anomaly["new_price"], 12000)
        self.assertEqual(anomaly["change_percent"], 20.0)

    def test_save_with_price_update_no_price_change(self):
        """Test save_with_price_update doesn't update when price is same"""
        # Create existing product
        Mitra10Product.objects.create(
            name="Existing Item", 
            price=10000, 
            url="https://example.com/existing", 
            unit="pcs"
        )
        
        # Update with same price
        data = [
            {"name": "Existing Item", "price": 10000, "url": "https://example.com/existing", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 0)  # No update because price is same
        self.assertEqual(len(result["anomalies"]), 0)

    def test_save_with_price_update_invalid_data(self):
        """Test save_with_price_update returns error for invalid data"""
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = Mitra10DatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["anomalies"]), 0)

    def test_save_with_price_update_mixed_insert_and_update(self):
        """Test save_with_price_update handles both inserts and updates"""
        # Create one existing product
        Mitra10Product.objects.create(
            name="Existing Item", 
            price=10000, 
            url="https://example.com/existing", 
            unit="pcs"
        )
        
        # Mix of new and existing products
        data = [
            {"name": "Existing Item", "price": 12000, "url": "https://example.com/existing", "unit": "pcs", "location": "Jakarta"},
            {"name": "New Item", "price": 5000, "url": "https://example.com/new", "unit": "box", "location": "Bali"}
        ]
        service = Mitra10DatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(len(result["anomalies"]), 1)  # One anomaly from price change
        self.assertEqual(Mitra10Product.objects.count(), 2)

    def test_save_with_price_update_with_location(self):
        """Test save_with_price_update handles location field"""
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Bandung"}
        ]
        service = Mitra10DatabaseService()
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        product = Mitra10Product.objects.first()
        self.assertEqual(product.location, "Bandung")
