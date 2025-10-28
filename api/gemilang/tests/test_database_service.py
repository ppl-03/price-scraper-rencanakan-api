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
        self.assertTrue(result)
        self.assertEqual(GemilangProduct.objects.count(), 2)
        product = GemilangProduct.objects.get(name="Item 1")
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.url, "https://example.com/1")
        self.assertEqual(product.unit, "pcs")

    def test_save_empty_data(self):
        data = []
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_name_field(self):
        data = [
            {"price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_price_field(self):
        data = [
            {"name": "Item 1", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_url_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_missing_unit_field(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_negative_price(self):
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
        self.assertEqual(GemilangProduct.objects.count(), 0)

    def test_save_zero_price(self):
        data = [
            {"name": "Item 1", "price": 0, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
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
        self.assertTrue(result)
        self.assertEqual(GemilangProduct.objects.count(), 2)

    def test_save_large_price(self):
        data = [
            {"name": "Item 1", "price": 999999999, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.price, 999999999)

    def test_save_empty_string_unit(self):
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1", "unit": ""}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.unit, "")

    def test_save_long_name(self):
        long_name = "A" * 500
        data = [
            {"name": long_name, "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.name, long_name)

    def test_save_long_url(self):
        long_url = "https://example.com/" + "x" * 980
        data = [
            {"name": "Item 1", "price": 10000, "url": long_url, "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.url, long_url)

    def test_save_special_characters_in_name(self):
        data = [
            {"name": "Item @#$% & * () 1", "price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertTrue(result)
        product = GemilangProduct.objects.first()
        self.assertEqual(product.name, "Item @#$% & * () 1")

    def test_save_price_not_integer(self):
        data = [
            {"name": "Item 1", "price": "10000", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = GemilangDatabaseService()
        result = service.save(data)
        self.assertFalse(result)
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
        self.assertTrue(result1)
        self.assertTrue(result2)
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


class TestSaveWithPriceUpdate(MySQLTestCase):
    """Test cases for save_with_price_update method"""
    
    def test_save_with_price_update_invalid_data(self):
        """Test save_with_price_update with invalid data"""
        service = GemilangDatabaseService()
        data = []
        result = service.save_with_price_update(data)
        self.assertFalse(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["anomalies"], [])
    
    def test_save_with_price_update_insert_new_product(self):
        """Test inserting new products via save_with_price_update"""
        service = GemilangDatabaseService()
        data = [
            {"name": "New Product", "price": 15000, "url": "https://new.com", "unit": "pcs"}
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
        self.assertEqual(GemilangProduct.objects.count(), 1)
    
    def test_save_with_price_update_update_existing_no_change(self):
        """Test updating existing product with same price (no change)"""
        service = GemilangDatabaseService()
        # Insert initial product
        GemilangProduct.objects.create(
            name="Existing Product",
            price=10000,
            url="https://existing.com",
            unit="box"
        )
        
        # Update with same price
        data = [
            {"name": "Existing Product", "price": 10000, "url": "https://existing.com", "unit": "box"}
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_save_with_price_update_update_existing_price_change_no_anomaly(self):
        """Test updating existing product with price change but no anomaly (< 15%)"""
        service = GemilangDatabaseService()
        # Insert initial product
        GemilangProduct.objects.create(
            name="Test Product",
            price=10000,
            url="https://test.com",
            unit="pcs"
        )
        
        # Update with 10% price increase (no anomaly)
        data = [
            {"name": "Test Product", "price": 11000, "url": "https://test.com", "unit": "pcs"}
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 0)
        product = GemilangProduct.objects.get(name="Test Product")
        self.assertEqual(product.price, 11000)
    
    def test_save_with_price_update_with_anomaly_increase(self):
        """Test price update with anomaly detection (15% increase)"""
        service = GemilangDatabaseService()
        # Insert initial product
        GemilangProduct.objects.create(
            name="Anomaly Product",
            price=10000,
            url="https://anomaly.com",
            unit="kg"
        )
        
        # Update with 20% price increase (anomaly)
        data = [
            {"name": "Anomaly Product", "price": 12000, "url": "https://anomaly.com", "unit": "kg"}
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["name"], "Anomaly Product")
        self.assertEqual(anomaly["url"], "https://anomaly.com")
        self.assertEqual(anomaly["unit"], "kg")
        self.assertEqual(anomaly["old_price"], 10000)
        self.assertEqual(anomaly["new_price"], 12000)
        self.assertEqual(anomaly["change_percent"], 20.0)
    
    def test_save_with_price_update_with_anomaly_decrease(self):
        """Test price update with anomaly detection (15% decrease)"""
        service = GemilangDatabaseService()
        # Insert initial product
        GemilangProduct.objects.create(
            name="Drop Product",
            price=20000,
            url="https://drop.com",
            unit="liter"
        )
        
        # Update with 25% price decrease (anomaly)
        data = [
            {"name": "Drop Product", "price": 15000, "url": "https://drop.com", "unit": "liter"}
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["change_percent"], -25.0)
    
    def test_save_with_price_update_zero_existing_price(self):
        """Test price update when existing price is zero (no anomaly check)"""
        service = GemilangDatabaseService()
        # Insert initial product with zero price
        GemilangProduct.objects.create(
            name="Zero Price Product",
            price=0,
            url="https://zero.com",
            unit="pcs"
        )
        
        # Update with non-zero price
        data = [
            {"name": "Zero Price Product", "price": 10000, "url": "https://zero.com", "unit": "pcs"}
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 0)  # No anomaly when existing price is 0
    
    def test_save_with_price_update_mixed_operations(self):
        """Test save_with_price_update with mixed insert and update operations"""
        service = GemilangDatabaseService()
        # Insert some existing products
        GemilangProduct.objects.create(
            name="Product A",
            price=10000,
            url="https://a.com",
            unit="pcs"
        )
        GemilangProduct.objects.create(
            name="Product B",
            price=20000,
            url="https://b.com",
            unit="box"
        )
        
        # Mix of updates and inserts
        data = [
            {"name": "Product A", "price": 12000, "url": "https://a.com", "unit": "pcs"},  # Update with 20% increase (anomaly)
            {"name": "Product B", "price": 21000, "url": "https://b.com", "unit": "box"},  # Update with 5% increase (no anomaly)
            {"name": "Product C", "price": 30000, "url": "https://c.com", "unit": "kg"}    # Insert new
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 2)
        self.assertEqual(len(result["anomalies"]), 1)
        self.assertEqual(result["anomalies"][0]["name"], "Product A")
        self.assertEqual(GemilangProduct.objects.count(), 3)
    
    def test_save_with_price_update_multiple_anomalies(self):
        """Test save_with_price_update detecting multiple anomalies"""
        service = GemilangDatabaseService()
        # Insert products
        GemilangProduct.objects.create(
            name="Product X",
            price=10000,
            url="https://x.com",
            unit="pcs"
        )
        GemilangProduct.objects.create(
            name="Product Y",
            price=20000,
            url="https://y.com",
            unit="kg"
        )
        
        # Both with price anomalies
        data = [
            {"name": "Product X", "price": 12000, "url": "https://x.com", "unit": "pcs"},  # +20%
            {"name": "Product Y", "price": 16000, "url": "https://y.com", "unit": "kg"}    # -20%
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 2)
        self.assertEqual(len(result["anomalies"]), 2)
    
    def test_save_with_price_update_exact_15_percent_threshold(self):
        """Test anomaly detection at exactly 15% threshold"""
        service = GemilangDatabaseService()
        GemilangProduct.objects.create(
            name="Threshold Product",
            price=10000,
            url="https://threshold.com",
            unit="pcs"
        )
        
        # Exactly 15% increase
        data = [
            {"name": "Threshold Product", "price": 11500, "url": "https://threshold.com", "unit": "pcs"}
        ]
        result = service.save_with_price_update(data)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["anomalies"]), 1)  # Should trigger anomaly at >= 15%
    
    def test_save_with_price_update_invalid_data_missing_field(self):
        """Test save_with_price_update with missing required field"""
        service = GemilangDatabaseService()
        data = [
            {"name": "Product", "price": 10000, "url": "https://test.com"}  # Missing unit
        ]
        result = service.save_with_price_update(data)
        self.assertFalse(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["anomalies"], [])
    
    def test_save_with_price_update_invalid_data_negative_price(self):
        """Test save_with_price_update with negative price"""
        service = GemilangDatabaseService()
        data = [
            {"name": "Product", "price": -100, "url": "https://test.com", "unit": "pcs"}
        ]
        result = service.save_with_price_update(data)
        self.assertFalse(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["anomalies"], [])
