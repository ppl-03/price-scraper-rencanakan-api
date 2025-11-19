# api/tokopedia/tests/test_anomaly_integration.py
"""
Integration tests for Tokopedia price anomaly detection and notification
"""

from django.test import TestCase
from db_pricing.models import PriceAnomaly, TokopediaProduct
from api.tokopedia.database_service import TokopediaDatabaseService


class TestTokopediaAnomalyIntegration(TestCase):
    """Test Tokopedia anomaly detection and notification integration"""
    
    def setUp(self):
        """Set up test data"""
        PriceAnomaly.objects.all().delete()
        TokopediaProduct.objects.all().delete()
        self.service = TokopediaDatabaseService()
    
    def test_tokopedia_anomaly_with_location_saved(self):
        """Test that Tokopedia anomalies include location"""
        # Create initial product
        initial_data = [
            {
                "name": "Tokopedia Product",
                "price": 25000,
                "url": "https://tokopedia.com/test",
                "unit": "PCS",
                "location": "Jakarta"
            }
        ]
        self.service.save(initial_data)
        
        # Update with 20% price increase
        updated_data = [
            {
                "name": "Tokopedia Product",
                "price": 30000,
                "url": "https://tokopedia.com/test",
                "unit": "PCS",
                "location": "Jakarta"
            }
        ]
        result = self.service.save_with_price_update(updated_data)
        
        # Check anomaly was saved with location
        self.assertTrue(result['success'])
        self.assertEqual(len(result['anomalies']), 1)
        
        saved_anomaly = PriceAnomaly.objects.filter(vendor='tokopedia').first()
        self.assertIsNotNone(saved_anomaly)
        self.assertEqual(saved_anomaly.location, 'Jakarta')
        self.assertEqual(saved_anomaly.old_price, 25000)
        self.assertEqual(saved_anomaly.new_price, 30000)
