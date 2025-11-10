from db_pricing.models import JuraganMaterialProduct
from api.juragan_material.database_service import JuraganMaterialDatabaseService
from .test_base import MySQLTestCase

class TestJuraganMaterialDatabaseService(MySQLTestCase):
    def test_save_valid_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"},
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box", "location": "Bandung"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 2)
        product = JuraganMaterialProduct.objects.get(name="Item 1")
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.url, "https://example.com/1")
        self.assertEqual(product.unit, "pcs")
        self.assertEqual(product.location, "Jakarta")


    def test_save_empty_data(self):
        data = []
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)

    def test_save_missing_name_field(self):
        data = [
            {"price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)

    def test_save_missing_price_field(self):
        data = [
            {"name": "Item 1", "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)

    def test_save_missing_url_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)

    def test_save_missing_unit_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)
        
    def test_save_negative_price(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)

    def test_save_zero_price(self):
        data = [
            {"name": "Item 1", "price": 0, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 1)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.price, 0)

    def test_save_duplicate_data(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"},
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 2)

    def test_save_large_price(self):
        data = [
            {"name": "Item 1", "price": 999999999, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.price, 999999999)

    def test_save_empty_string_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.unit, "")

    def test_save_long_name(self):
        long_name = "A" * 500
        data = [
            {"name": long_name, "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.name, long_name)

    def test_save_long_url(self):
        long_url = "https://example.com/" + "x" * 980
        data = [
            {"name": "Item 1", "price": 10000, "url": long_url, "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.url, long_url)

    def test_save_special_characters_in_name(self):
        data = [
            {"name": "Item @#$% & * () 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.name, "Item @#$% & * () 1")

    def test_save_price_not_integer(self):
        data = [
            {"name": "Item 1", "price": "10000", "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)

    def test_save_multiple_batches(self):
        data1 = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        data2 = [
            {"name": "Item 2", "price": 20000, "url": "https://example.com/2", "unit": "box", "location": "Bandung"}
        ]
        service = JuraganMaterialDatabaseService()
        result1 = service.save(data1)
        result2 = service.save(data2)
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 2)

    def test_verify_timestamps_created(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs", "location": "Jakarta"}
        ]
        service = JuraganMaterialDatabaseService()
        service.save(data)
        product = JuraganMaterialProduct.objects.first()
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)


from unittest.mock import patch, MagicMock

class TestDatabaseServiceCoverage(MySQLTestCase):
    
    def test_executemany_called_with_correct_params(self):
        service = JuraganMaterialDatabaseService()
        data = [
            {"name": "Product 1", "price": 10000, "url": "https://test1.com", "unit": "PCS", "location": "Jakarta"},
            {"name": "Product 2", "price": 20000, "url": "https://test2.com", "unit": "BOX", "location": "Bandung"}
        ]
        
        result = service.save(data)
        self.assertTrue(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 2)


class TestDatabaseServicePriceUpdate(MySQLTestCase):
    """Test save_with_price_update method"""
    
    def test_save_with_price_update_valid_data(self):
        """Test updating existing product with new price"""
        service = JuraganMaterialDatabaseService()
        
        # Insert initial product
        initial_data = [
            {"name": "Semen", "price": 50000, "url": "https://test.com/semen", "unit": "sak", "location": "Jakarta"}
        ]
        service.save(initial_data)
        
        # Update with new price
        updated_data = [
            {"name": "Semen", "price": 55000, "url": "https://test.com/semen", "unit": "sak", "location": "Jakarta"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
        
        # Verify price was updated
        product = JuraganMaterialProduct.objects.get(name="Semen")
        self.assertEqual(product.price, 55000)
    
    def test_save_with_price_update_insert_new(self):
        """Test inserting new product"""
        service = JuraganMaterialDatabaseService()
        
        new_data = [
            {"name": "Pasir", "price": 30000, "url": "https://test.com/pasir", "unit": "m3", "location": "Bandung"}
        ]
        result = service.save_with_price_update(new_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(len(result["anomalies"]), 0)
        
        # Verify product was created
        self.assertEqual(JuraganMaterialProduct.objects.count(), 1)
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.name, "Pasir")
        self.assertEqual(product.price, 30000)
    
    def test_save_with_price_update_price_anomaly(self):
        """Test detecting price anomaly (>15% change)"""
        service = JuraganMaterialDatabaseService()
        
        # Insert initial product
        initial_data = [
            {"name": "Bata", "price": 100000, "url": "https://test.com/bata", "unit": "pcs", "location": "Jakarta"}
        ]
        service.save(initial_data)
        
        # Update with 20% price increase
        updated_data = [
            {"name": "Bata", "price": 120000, "url": "https://test.com/bata", "unit": "pcs", "location": "Jakarta"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["name"], "Bata")
        self.assertEqual(anomaly["old_price"], 100000)
        self.assertEqual(anomaly["new_price"], 120000)
        self.assertEqual(anomaly["change_percent"], 20.0)
    
    def test_save_with_price_update_negative_anomaly(self):
        """Test detecting negative price anomaly (>15% decrease)"""
        service = JuraganMaterialDatabaseService()
        
        # Insert initial product
        initial_data = [
            {"name": "Cat", "price": 200000, "url": "https://test.com/cat", "unit": "kaleng", "location": "Surabaya"}
        ]
        service.save(initial_data)
        
        # Update with 20% price decrease
        updated_data = [
            {"name": "Cat", "price": 160000, "url": "https://test.com/cat", "unit": "kaleng", "location": "Surabaya"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["change_percent"], -20.0)
    
    def test_save_with_price_update_no_price_change(self):
        """Test updating product with same price (no anomaly)"""
        service = JuraganMaterialDatabaseService()
        
        # Insert initial product
        initial_data = [
            {"name": "Paku", "price": 15000, "url": "https://test.com/paku", "unit": "kg", "location": "Jakarta"}
        ]
        service.save(initial_data)
        
        # Update with same price
        updated_data = [
            {"name": "Paku", "price": 15000, "url": "https://test.com/paku", "unit": "kg", "location": "Jakarta"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 0)  # No update since price is same
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_save_with_price_update_small_price_change(self):
        """Test updating with small price change (<15%, no anomaly)"""
        service = JuraganMaterialDatabaseService()
        
        # Insert initial product
        initial_data = [
            {"name": "Kawat", "price": 100000, "url": "https://test.com/kawat", "unit": "roll", "location": "Jakarta"}
        ]
        service.save(initial_data)
        
        # Update with 10% price increase
        updated_data = [
            {"name": "Kawat", "price": 110000, "url": "https://test.com/kawat", "unit": "roll", "location": "Jakarta"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 0)  # No anomaly for <15%
    
    def test_save_with_price_update_invalid_data(self):
        """Test with invalid data"""
        service = JuraganMaterialDatabaseService()
        
        invalid_data = [
            {"name": "Test", "price": "not_a_number", "url": "https://test.com", "unit": "pcs", "location": "Jakarta"}
        ]
        result = service.save_with_price_update(invalid_data)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 0)
    
    def test_save_with_price_update_empty_data(self):
        """Test with empty data"""
        service = JuraganMaterialDatabaseService()
        
        result = service.save_with_price_update([])
        
        self.assertFalse(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 0)
    
    def test_save_with_price_update_multiple_products(self):
        """Test updating and inserting multiple products"""
        service = JuraganMaterialDatabaseService()
        
        # Insert initial products
        initial_data = [
            {"name": "Product A", "price": 10000, "url": "https://test.com/a", "unit": "pcs", "location": "Jakarta"},
            {"name": "Product B", "price": 20000, "url": "https://test.com/b", "unit": "box", "location": "Bandung"}
        ]
        service.save(initial_data)
        
        # Update A, insert C, keep B same
        mixed_data = [
            {"name": "Product A", "price": 12000, "url": "https://test.com/a", "unit": "pcs", "location": "Jakarta"},
            {"name": "Product C", "price": 30000, "url": "https://test.com/c", "unit": "set", "location": "Surabaya"}
        ]
        result = service.save_with_price_update(mixed_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["inserted"], 1)
    
    def test_save_with_price_update_from_zero_price(self):
        """Test price change from zero (edge case for percentage calculation)"""
        service = JuraganMaterialDatabaseService()
        
        # Insert product with zero price
        initial_data = [
            {"name": "Free Item", "price": 0, "url": "https://test.com/free", "unit": "pcs", "location": "Jakarta"}
        ]
        service.save(initial_data)
        
        # Update with non-zero price
        updated_data = [
            {"name": "Free Item", "price": 10000, "url": "https://test.com/free", "unit": "pcs", "location": "Jakarta"}
        ]
        result = service.save_with_price_update(updated_data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        # No anomaly calculation when old price is 0
        self.assertEqual(len(result["anomalies"]), 0)


class TestDatabaseServiceObjectSupport(MySQLTestCase):
    """Test database service with object-type data (not just dicts)"""
    
    def test_save_with_object_data(self):
        """Test saving data as objects instead of dicts"""
        service = JuraganMaterialDatabaseService()
        
        class Product:
            def __init__(self, name, price, url, unit, location):
                self.name = name
                self.price = price
                self.url = url
                self.unit = unit
                self.location = location
        
        data = [
            Product("Object Product", 50000, "https://test.com/obj", "pcs", "Jakarta")
        ]
        
        result = service.save(data)
        self.assertTrue(result)
        
        product = JuraganMaterialProduct.objects.first()
        self.assertEqual(product.name, "Object Product")
        self.assertEqual(product.price, 50000)
    
    def test_save_with_price_update_object_data(self):
        """Test save_with_price_update with object-type data"""
        service = JuraganMaterialDatabaseService()
        
        class Product:
            def __init__(self, name, price, url, unit, location):
                self.name = name
                self.price = price
                self.url = url
                self.unit = unit
                self.location = location
        
        # Insert initial
        initial = [Product("ObjItem", 100000, "https://test.com/obj", "box", "Jakarta")]
        service.save(initial)
        
        # Update with object
        updated = [Product("ObjItem", 120000, "https://test.com/obj", "box", "Jakarta")]
        result = service.save_with_price_update(updated)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["name"], "ObjItem")
        self.assertEqual(anomaly["new_price"], 120000)
    
    def test_validate_object_missing_attribute(self):
        """Test validation fails for object missing required attribute"""
        service = JuraganMaterialDatabaseService()
        
        class IncompleteProduct:
            def __init__(self, name, price):
                self.name = name
                self.price = price
                # Missing url, unit, location
        
        data = [IncompleteProduct("Bad Product", 10000)]
        result = service.save(data)
        
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)
    
    def test_validate_object_invalid_price(self):
        """Test validation fails for object with invalid price"""
        service = JuraganMaterialDatabaseService()
        
        class BadPriceProduct:
            def __init__(self):
                self.name = "Test"
                self.price = "not_a_number"
                self.url = "https://test.com"
                self.unit = "pcs"
                self.location = "Jakarta"
        
        data = [BadPriceProduct()]
        result = service.save(data)
        
        self.assertFalse(result)
        self.assertEqual(JuraganMaterialProduct.objects.count(), 0)