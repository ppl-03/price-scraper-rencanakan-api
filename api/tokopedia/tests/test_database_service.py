from django.test import TestCase, TransactionTestCase
from django.db import connection
from db_pricing.models import TokopediaProduct
from api.tokopedia.database_service import TokopediaDatabaseService


class TestTokopediaDatabaseService(TransactionTestCase):
    """Test TokopediaDatabaseService with SQL injection protection"""
    
    def setUp(self):
        """Clear database before each test"""
        TokopediaProduct.objects.all().delete()
    
    # Test: _validate_data() function
    def test_validate_data_with_valid_input(self):
        """Test validation accepts valid data"""
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service._validate_data(data)
        self.assertTrue(result)
    
    def test_validate_data_with_empty_data(self):
        """Test validation rejects empty data"""
        service = TokopediaDatabaseService()
        result = service._validate_data([])
        self.assertFalse(result)
    
    def test_validate_data_missing_name_field(self):
        """Test validation rejects missing name field"""
        data = [
            {"price": 10000, "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service._validate_data(data)
        self.assertFalse(result)
    
    def test_validate_data_missing_price_field(self):
        """Test validation rejects missing price field"""
        data = [
            {"name": "Item 1", "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service._validate_data(data)
        self.assertFalse(result)
    
    def test_validate_data_missing_location_field(self):
        """Test validation rejects missing location field"""
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://tokopedia.com/1", 
             "unit": "pcs"}
        ]
        service = TokopediaDatabaseService()
        result = service._validate_data(data)
        self.assertFalse(result)
    
    def test_validate_data_negative_price(self):
        """Test validation rejects negative price"""
        data = [
            {"name": "Item 1", "price": -100, "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service._validate_data(data)
        self.assertFalse(result)
    
    def test_validate_data_wrong_price_type(self):
        """Test validation rejects non-integer price"""
        data = [
            {"name": "Item 1", "price": "10000", "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service._validate_data(data)
        self.assertFalse(result)
    
    # Test: save() function - SQL injection protection
    def test_save_valid_data(self):
        """Test save() with valid data"""
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"},
            {"name": "Item 2", "price": 20000, "url": "https://tokopedia.com/2", 
             "unit": "box", "location": "Bandung"}
        ]
        service = TokopediaDatabaseService()
        result = service.save(data)
        
        self.assertTrue(result)
        self.assertEqual(TokopediaProduct.objects.count(), 2)
        
        product = TokopediaProduct.objects.get(name="Item 1")
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.url, "https://tokopedia.com/1")
        self.assertEqual(product.unit, "pcs")
        self.assertEqual(product.location, "Jakarta")
    
    def test_save_with_sql_injection_attempt_in_name(self):
        """Test SQL injection protection in name field"""
        # Attempt SQL injection through name field
        data = [
            {"name": "Item'; DROP TABLE tokopedia_products;--", 
             "price": 10000, 
             "url": "https://tokopedia.com/1", 
             "unit": "pcs", 
             "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service.save(data)
        
        # Should save safely without executing injected SQL
        self.assertTrue(result)
        self.assertEqual(TokopediaProduct.objects.count(), 1)
        
        # Verify the malicious string was stored as data, not executed
        product = TokopediaProduct.objects.first()
        self.assertEqual(product.name, "Item'; DROP TABLE tokopedia_products;--")
        
        # Verify table still exists by querying it
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE %s", ['tokopedia_products'])
            self.assertIsNotNone(cursor.fetchone())
    
    def test_save_with_sql_injection_attempt_in_url(self):
        """Test SQL injection protection in URL field"""
        data = [
            {"name": "Item 1", 
             "price": 10000, 
             "url": "https://tokopedia.com/1' OR '1'='1", 
             "unit": "pcs", 
             "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service.save(data)
        
        self.assertTrue(result)
        product = TokopediaProduct.objects.first()
        self.assertEqual(product.url, "https://tokopedia.com/1' OR '1'='1")
    
    def test_save_with_sql_injection_attempt_in_location(self):
        """Test SQL injection protection in location field"""
        data = [
            {"name": "Item 1", 
             "price": 10000, 
             "url": "https://tokopedia.com/1", 
             "unit": "pcs", 
             "location": "Jakarta'; DELETE FROM tokopedia_products WHERE '1'='1"}
        ]
        service = TokopediaDatabaseService()
        result = service.save(data)
        
        self.assertTrue(result)
        self.assertEqual(TokopediaProduct.objects.count(), 1)
        product = TokopediaProduct.objects.first()
        self.assertEqual(product.location, "Jakarta'; DELETE FROM tokopedia_products WHERE '1'='1")
    
    # Test: _check_anomaly() function
    def test_check_anomaly_with_15_percent_increase(self):
        """Test anomaly detection for 15% price increase"""
        service = TokopediaDatabaseService()
        item = {"name": "Item", "url": "url", "unit": "pcs", "location": "Jakarta"}
        anomaly = service._check_anomaly(item, 10000, 11500)
        
        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly["old_price"], 10000)
        self.assertEqual(anomaly["new_price"], 11500)
        self.assertEqual(anomaly["change_percent"], 15.0)
    
    def test_check_anomaly_with_15_percent_decrease(self):
        """Test anomaly detection for 15% price decrease"""
        service = TokopediaDatabaseService()
        item = {"name": "Item", "url": "url", "unit": "pcs", "location": "Jakarta"}
        anomaly = service._check_anomaly(item, 10000, 8500)
        
        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly["change_percent"], -15.0)
    
    def test_check_anomaly_below_threshold(self):
        """Test no anomaly for price change below 15%"""
        service = TokopediaDatabaseService()
        item = {"name": "Item", "url": "url", "unit": "pcs", "location": "Jakarta"}
        anomaly = service._check_anomaly(item, 10000, 11000)
        
        self.assertIsNone(anomaly)
    
    def test_check_anomaly_with_zero_existing_price(self):
        """Test anomaly check with zero existing price"""
        service = TokopediaDatabaseService()
        item = {"name": "Item", "url": "url", "unit": "pcs", "location": "Jakarta"}
        anomaly = service._check_anomaly(item, 0, 10000)
        
        self.assertIsNone(anomaly)
    
    # Test: save_with_price_update() function
    def test_save_with_price_update_new_products(self):
        """Test saving new products"""
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_save_with_price_update_existing_product_no_change(self):
        """Test updating existing product with same price"""
        # Insert initial product
        TokopediaProduct.objects.create(
            name="Item 1", price=10000, url="https://tokopedia.com/1", 
            unit="pcs", location="Jakarta"
        )
        
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 0)
    
    def test_save_with_price_update_price_change_with_anomaly(self):
        """Test updating product with price change causing anomaly"""
        # Insert initial product
        TokopediaProduct.objects.create(
            name="Item 1", price=10000, url="https://tokopedia.com/1", 
            unit="pcs", location="Jakarta"
        )
        
        # Update with 20% price increase (anomaly)
        data = [
            {"name": "Item 1", "price": 12000, "url": "https://tokopedia.com/1", 
             "unit": "pcs", "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["old_price"], 10000)
        self.assertEqual(anomaly["new_price"], 12000)
        self.assertEqual(anomaly["change_percent"], 20.0)
    
    def test_save_with_price_update_sql_injection_in_select(self):
        """Test SQL injection protection in SELECT query during update"""
        # Insert initial product
        TokopediaProduct.objects.create(
            name="Item 1", price=10000, url="https://tokopedia.com/1", 
            unit="pcs", location="Jakarta"
        )
        
        # Attempt SQL injection in SELECT WHERE clause
        data = [
            {"name": "Item 1' OR '1'='1", 
             "price": 15000, 
             "url": "https://tokopedia.com/1", 
             "unit": "pcs", 
             "location": "Jakarta"}
        ]
        service = TokopediaDatabaseService()
        result = service.save_with_price_update(data)
        
        # Should treat injection attempt as new product name, not find existing
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)  # New product inserted
        self.assertEqual(result["updated"], 0)   # Existing not updated
        
        # Verify original product unchanged
        original = TokopediaProduct.objects.get(
            name="Item 1", url="https://tokopedia.com/1"
        )
        self.assertEqual(original.price, 10000)
