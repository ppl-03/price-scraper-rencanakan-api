from django.test import TestCase
from unittest.mock import Mock, patch
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
    
    def test_check_anomaly_with_zero_existing_price(self):
        """Line 110: existing_price == 0 returns None"""
        service = DepoBangunanDatabaseService()
        item = {
            "name": "Test Product",
            "url": "https://example.com/product",
            "unit": "PCS"
        }
        existing_price = 0
        new_price = 100000
        
        result = service._check_anomaly(item, existing_price, new_price)
        
        self.assertIsNone(result)

    def test_check_anomaly_with_large_price_change(self):
        """Line 113: price_diff >= 15% returns anomaly dict"""
        service = DepoBangunanDatabaseService()
        item = {
            "name": "Test Product",
            "url": "https://example.com/product",
            "unit": "PCS"
        }
        existing_price = 100000
        new_price = 120000  # 20% increase
        
        result = service._check_anomaly(item, existing_price, new_price)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Test Product")
        self.assertEqual(result["old_price"], 100000)
        self.assertEqual(result["new_price"], 120000)
        self.assertEqual(result["change_percent"], 20.0)

    def test_save_detected_anomalies_empty_list(self):
        """Lines 128-130: empty anomalies list returns early"""
        service = DepoBangunanDatabaseService()
        anomalies = []
        
        # Should return early without calling PriceAnomalyService
        result = service._save_detected_anomalies(anomalies)
        
        self.assertIsNone(result)

    @patch('api.depobangunan.database_service.logger')
    @patch('api.depobangunan.database_service.PriceAnomalyService.save_anomalies')
    def test_update_product_price_with_anomaly_detected(self, mock_save_anomalies, mock_logger):
        """Lines 65-71: anomaly detected, warning logged, price not updated"""
        service = DepoBangunanDatabaseService()
        
        cursor = Mock()
        item = {
            "name": "Test Product",
            "url": "https://example.com/product",
            "unit": "PCS",
            "price": 120000  # 20% increase from 100000
        }
        existing_id = 1
        existing_price = 100000
        now = Mock()
        anomalies = []
        
        result = service._update_product_price(
            cursor, item, existing_id, existing_price, now, anomalies
        )
        
        # Should not update (returns 0)
        self.assertEqual(result, 0)
        
        # Should append anomaly
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["name"], "Test Product")
        
        # Should log warning
        mock_logger.warning.assert_called_once()
        
        # Should NOT execute UPDATE query
        cursor.execute.assert_not_called()
    
    @patch('api.depobangunan.database_service.logger')
    @patch('api.depobangunan.database_service.PriceAnomalyService.save_anomalies')
    def test_save_detected_anomalies_with_errors(self, mock_save_anomalies, mock_logger):
        """Lines 128-130: logs error when anomaly save fails"""
        service = DepoBangunanDatabaseService()
        
        # Mock save_anomalies to return failure
        mock_save_anomalies.return_value = {
            'success': False,
            'errors': ['Database error']
        }
        
        anomalies = [
            {
                "name": "Test Product",
                "url": "https://example.com/product",
                "unit": "PCS",
                "old_price": 100000,
                "new_price": 120000,
                "change_percent": 20.0
            }
        ]
        
        service._save_detected_anomalies(anomalies)
        
        # Should call PriceAnomalyService
        mock_save_anomalies.assert_called_once_with('depobangunan', anomalies)
        
        # Should log error
        mock_logger.error.assert_called_once()
