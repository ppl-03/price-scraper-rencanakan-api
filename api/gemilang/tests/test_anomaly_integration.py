# api/gemilang/tests/test_anomaly_integration.py
"""
Integration tests for Gemilang price anomaly detection and notification
"""

from django.test import TestCase
from db_pricing.models import PriceAnomaly, GemilangProduct
from api.gemilang.database_service import GemilangDatabaseService


class TestGemilangAnomalyIntegration(TestCase):
    """Test Gemilang anomaly detection and notification integration"""
    
    def setUp(self):
        """Set up test data"""
        PriceAnomaly.objects.all().delete()
        GemilangProduct.objects.all().delete()
        self.service = GemilangDatabaseService()
    
    def test_gemilang_anomaly_saved_to_database(self):
        """Test that Gemilang anomalies are saved to database"""
        # Create initial product
        initial_data = [
            {
                "name": "Gemilang Product",
                "price": 50000,
                "url": "https://gemilang.com/test",
                "unit": "BOX"
            }
        ]
        self.service.save(initial_data)
        
        # Update with 30% price decrease (anomaly)
        updated_data = [
            {
                "name": "Gemilang Product",
                "price": 35000,
                "url": "https://gemilang.com/test",
                "unit": "BOX"
            }
        ]
        result = self.service.save_with_price_update(updated_data)
        
        # Check anomaly was saved
        self.assertTrue(result['success'])
        self.assertEqual(len(result['anomalies']), 1)
        
        saved_anomalies = PriceAnomaly.objects.filter(vendor='gemilang')
        self.assertEqual(saved_anomalies.count(), 1)
        
        anomaly = saved_anomalies.first()
        self.assertEqual(anomaly.product_name, "Gemilang Product")
        self.assertEqual(anomaly.old_price, 50000)
        self.assertEqual(anomaly.new_price, 35000)
        self.assertEqual(float(anomaly.change_percent), -30.0)
