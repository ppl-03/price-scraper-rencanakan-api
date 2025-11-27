# api/mitra10/tests/test_anomaly_integration.py
"""
Integration tests for Mitra10 price anomaly detection and notification
"""

from db_pricing.models import PriceAnomaly, Mitra10Product
from api.mitra10.database_service import Mitra10DatabaseService
from .test_base import MySQLTestCase


class TestMitra10AnomalyIntegration(MySQLTestCase):
    """Test Mitra10 anomaly detection and notification integration"""
    
    def setUp(self):
        """Set up test data"""
        PriceAnomaly.objects.all().delete()
        Mitra10Product.objects.all().delete()
        self.service = Mitra10DatabaseService()
    
    def test_mitra10_anomaly_saved_to_database(self):
        """Test that Mitra10 anomalies are saved to database"""
        # Create initial product (no category - that's added later by AutoCategorizationService)
        initial_data = [
            {
                "name": "Mitra10 Test Product",
                "price": 10000,
                "url": "https://www.mitra10.com/test",
                "unit": "PCS"
            }
        ]
        self.service.save(initial_data)
        
        # Update with 20% price increase (anomaly)
        updated_data = [
            {
                "name": "Mitra10 Test Product",
                "price": 12000,
                "url": "https://www.mitra10.com/test",
                "unit": "PCS"
            }
        ]
        result = self.service.save_with_price_update(updated_data)
        
        # Check response contains anomaly
        self.assertTrue(result['success'])
        self.assertEqual(len(result['anomalies']), 1)
        
        # Check anomaly was saved to database
        saved_anomalies = PriceAnomaly.objects.filter(vendor='mitra10')
        self.assertEqual(saved_anomalies.count(), 1)
        
        anomaly = saved_anomalies.first()
        self.assertEqual(anomaly.product_name, "Mitra10 Test Product")
        self.assertEqual(anomaly.old_price, 10000)
        self.assertEqual(anomaly.new_price, 12000)
        self.assertEqual(float(anomaly.change_percent), 20.0)
        self.assertEqual(anomaly.status, 'pending')
    
    def test_mitra10_no_anomaly_below_threshold(self):
        """Test that small price changes don't create anomalies"""
        initial_data = [
            {
                "name": "Mitra10 Product",
                "price": 10000,
                "url": "https://www.mitra10.com/test",
                "unit": "PCS"
            }
        ]
        self.service.save(initial_data)
        
        # Update with 10% increase (below 15% threshold)
        updated_data = [
            {
                "name": "Mitra10 Product",
                "price": 11000,
                "url": "https://www.mitra10.com/test",
                "unit": "PCS"
            }
        ]
        result = self.service.save_with_price_update(updated_data)
        
        # No anomaly should be created
        self.assertEqual(len(result['anomalies']), 0)
        self.assertEqual(PriceAnomaly.objects.count(), 0)
