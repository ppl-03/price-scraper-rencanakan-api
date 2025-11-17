from django.test import TestCase
from db_pricing.models import DepoBangunanProduct
from api.depobangunan.database_service import DepoBangunanDatabaseService


class TestDepoBangunanDatabaseService(TestCase):
    """Simple tests for DepoBangunan database service
    
    Django's TestCase automatically:
    - Uses a separate test database (NOT production)
    - Rolls back changes after each test
    - Isolates tests from each other
    """
    
    def setUp(self):
        """Clear all products before each test"""
        DepoBangunanProduct.objects.all().delete()
    
    def test_save_valid_data(self):
        """Test saving valid product data"""
        data = [
            {"name": "Semen Gresik", "price": 50000, "url": "https://example.com/1", "unit": "sak"},
            {"name": "Cat Tembok", "price": 75000, "url": "https://example.com/2", "unit": "kaleng"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertTrue(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 2)
        
        product = DepoBangunanProduct.objects.get(name="Semen Gresik")
        self.assertEqual(product.price, 50000)
        self.assertEqual(product.url, "https://example.com/1")
        self.assertEqual(product.unit, "sak")
    
    def test_save_empty_data(self):
        """Test saving empty data returns False"""
        data = []
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)
    
    def test_save_missing_name_field(self):
        """Test saving data with missing name field"""
        data = [
            {"price": 10000, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)
    
    def test_save_missing_price_field(self):
        """Test saving data with missing price field"""
        data = [
            {"name": "Item 1", "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)
    
    def test_save_missing_url_field(self):
        """Test saving data with missing url field"""
        data = [
            {"name": "Item 1", "price": 10000, "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)
    
    def test_save_missing_unit_field(self):
        """Test saving data with missing unit field"""
        data = [
            {"name": "Item 1", "price": 10000, "url": "https://example.com/1"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)
    
    def test_save_negative_price(self):
        """Test saving product with negative price"""
        data = [
            {"name": "Item 1", "price": -100, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertFalse(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)
    
    def test_save_zero_price(self):
        """Test saving product with zero price is allowed"""
        data = [
            {"name": "Free Item", "price": 0, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertTrue(result)
        self.assertEqual(DepoBangunanProduct.objects.count(), 1)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.price, 0)
    
    def test_save_with_location(self):
        """Test saving product with location field"""
        data = [
            {
                "name": "Item 1",
                "price": 10000,
                "url": "https://example.com/1",
                "unit": "pcs",
                "location": "Jakarta, Bandung"
            }
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertTrue(result)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.location, "Jakarta, Bandung")
    
    def test_save_with_category(self):
        """Test saving product with category field"""
        data = [
            {
                "name": "Item 1",
                "price": 10000,
                "url": "https://example.com/1",
                "unit": "pcs",
                "category": "Building Materials"
            }
        ]
        service = DepoBangunanDatabaseService()
        result = service.save(data)
        
        self.assertTrue(result)
        product = DepoBangunanProduct.objects.first()
        self.assertEqual(product.category, "Building Materials")
    
    def test_save_with_price_update_new_products(self):
        """Test save_with_price_update inserts new products"""
        data = [
            {"name": "New Item", "price": 50000, "url": "https://example.com/new", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["new_count"], 1)
        self.assertEqual(result["updated_count"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
        self.assertEqual(DepoBangunanProduct.objects.count(), 1)
    
    def test_save_with_price_update_existing_no_change(self):
        """Test save_with_price_update does not update if price unchanged"""
        # Insert initial product
        DepoBangunanProduct.objects.create(
            name="Existing Item",
            price=50000,
            url="https://example.com/existing",
            unit="pcs"
        )
        
        # Try to save same product with same price
        data = [
            {"name": "Existing Item", "price": 50000, "url": "https://example.com/existing", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["new_count"], 0)
        self.assertEqual(result["updated_count"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
        self.assertEqual(DepoBangunanProduct.objects.count(), 1)
    
    def test_save_with_price_update_price_changed(self):
        """Test save_with_price_update updates price when changed"""
        # Insert initial product
        DepoBangunanProduct.objects.create(
            name="Existing Item",
            price=50000,
            url="https://example.com/existing",
            unit="pcs"
        )
        
        # Save with different price
        data = [
            {"name": "Existing Item", "price": 55000, "url": "https://example.com/existing", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["new_count"], 0)
        self.assertEqual(result["updated_count"], 1)
        
        product = DepoBangunanProduct.objects.get(name="Existing Item")
        self.assertEqual(product.price, 55000)
    
    def test_save_with_price_update_no_anomaly_small_change(self):
        """Test save_with_price_update does not detect anomaly for small change (<15%)"""
        # Insert initial product
        DepoBangunanProduct.objects.create(
            name="Existing Item",
            price=100000,
            url="https://example.com/existing",
            unit="pcs"
        )
        
        # Save with 10% price increase (no anomaly)
        data = [
            {"name": "Existing Item", "price": 110000, "url": "https://example.com/existing", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_save_with_price_update_invalid_data(self):
        """Test save_with_price_update handles invalid data"""
        data = [
            {"name": "Item", "price": -100, "url": "https://example.com/1", "unit": "pcs"}
        ]
        service = DepoBangunanDatabaseService()
        result = service.save_with_price_update(data)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["updated_count"], 0)
        self.assertEqual(result["new_count"], 0)
        self.assertEqual(DepoBangunanProduct.objects.count(), 0)
