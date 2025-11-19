# api/juragan_material/tests/test_anomaly_integration.py
"""
Integration tests for JuraganMaterial price anomaly detection and notification
"""

from django.test import TestCase
from db_pricing.models import PriceAnomaly, JuraganMaterialProduct
from api.juragan_material.database_service import JuraganMaterialDatabaseService


class TestJuraganMaterialAnomalyIntegration(TestCase):
    """Test JuraganMaterial anomaly detection and notification integration"""
    
    def setUp(self):
        """Set up test data"""
        PriceAnomaly.objects.all().delete()
        JuraganMaterialProduct.objects.all().delete()
        self.service = JuraganMaterialDatabaseService()
    
    def test_juragan_material_anomaly_with_location_saved(self):
        """Test that JuraganMaterial anomalies include location"""
        # Create initial product
        initial_data = [
            {
                "name": "JM Product",
                "price": 15000,
                "url": "https://jm.com/test",
                "unit": "M",
                "location": "Bandung"
            }
        ]
        self.service.save(initial_data)
        
        # Update with 25% price decrease
        updated_data = [
            {
                "name": "JM Product",
                "price": 11250,
                "url": "https://jm.com/test",
                "unit": "M",
                "location": "Bandung"
            }
        ]
        result = self.service.save_with_price_update(updated_data)
        
        # Check anomaly was saved with location
        self.assertTrue(result['success'])
        self.assertEqual(len(result['anomalies']), 1)
        
        saved_anomaly = PriceAnomaly.objects.filter(vendor='juragan_material').first()
        self.assertIsNotNone(saved_anomaly)
        self.assertEqual(saved_anomaly.location, 'Bandung')
        self.assertEqual(float(saved_anomaly.change_percent), -25.0)
