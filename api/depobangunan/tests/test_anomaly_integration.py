# api/depobangunan/tests/test_anomaly_integration.py
"""
Integration tests for DepoBangunan price anomaly detection and notification
"""

from django.test import TestCase
from db_pricing.models import PriceAnomaly, DepoBangunanProduct
from api.depobangunan.database_service import DepoBangunanDatabaseService


class TestDepoBangunanAnomalyIntegration(TestCase):
    """Test DepoBangunan anomaly detection and notification integration"""
    
    def setUp(self):
        """Set up test data"""
        PriceAnomaly.objects.all().delete()
        DepoBangunanProduct.objects.all().delete()
        self.service = DepoBangunanDatabaseService()

    def test_depobangunan_anomaly_saved_to_database(self):
        """Test that DepoBangunan anomalies are saved to database"""
        # Create initial product
        initial_data = [
            {
                "name": "Depo Product",
                "price": 100000,
                "url": "https://depobangunan.com/test",
                "unit": "UNIT"
            }
        ]
        self.service.save(initial_data)

        # Update with 15% price increase (at threshold)
        updated_data = [
            {
                "name": "Depo Product",
                "price": 115000,
                "url": "https://depobangunan.com/test",
                "unit": "UNIT"
            }
        ]
        result = self.service.save_with_price_update(updated_data)

        # Check anomaly was saved
        self.assertTrue(result['success'])
        self.assertEqual(len(result['anomalies']), 1)

        saved_anomaly = PriceAnomaly.objects.filter(vendor='depobangunan').first()
        self.assertIsNotNone(saved_anomaly)
        self.assertEqual(float(saved_anomaly.change_percent), 15.0)
