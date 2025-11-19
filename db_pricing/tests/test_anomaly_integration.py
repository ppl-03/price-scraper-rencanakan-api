# db_pricing/tests/test_anomaly_integration.py
"""
Integration tests for price anomaly detection across multiple vendors.
Individual vendor tests have been moved to their respective vendor test folders:
- api/mitra10/tests/test_anomaly_integration.py
- api/gemilang/tests/test_anomaly_integration.py
- api/tokopedia/tests/test_anomaly_integration.py
- api/depobangunan/tests/test_anomaly_integration.py
- api/juragan_material/tests/test_anomaly_integration.py

This file now only contains cross-vendor integration tests.
"""

from django.test import TestCase
from db_pricing.models import (
    PriceAnomaly, 
    Mitra10Product, 
    GemilangProduct
)
from api.mitra10.database_service import Mitra10DatabaseService
from api.gemilang.database_service import GemilangDatabaseService


class TestMultipleVendorAnomalies(TestCase):
    """Test anomaly notifications across multiple vendors"""
    
    def setUp(self):
        """Set up test data"""
        PriceAnomaly.objects.all().delete()
        Mitra10Product.objects.all().delete()
        GemilangProduct.objects.all().delete()
    
    def test_anomalies_from_multiple_vendors(self):
        """Test that anomalies from different vendors are tracked separately"""
        # Create Mitra10 anomaly
        mitra10_service = Mitra10DatabaseService()
        mitra10_service.save([{
            "name": "Mitra10 Product",
            "price": 10000,
            "url": "https://mitra10.com/test",
            "unit": "PCS"
        }])
        mitra10_service.save_with_price_update([{
            "name": "Mitra10 Product",
            "price": 12000,
            "url": "https://mitra10.com/test",
            "unit": "PCS"
        }])
        
        # Create Gemilang anomaly
        gemilang_service = GemilangDatabaseService()
        gemilang_service.save([{
            "name": "Gemilang Product",
            "price": 20000,
            "url": "https://gemilang.com/test",
            "unit": "BOX"
        }])
        gemilang_service.save_with_price_update([{
            "name": "Gemilang Product",
            "price": 24000,
            "url": "https://gemilang.com/test",
            "unit": "BOX"
        }])
        
        # Check both anomalies were saved
        total_anomalies = PriceAnomaly.objects.all()
        self.assertEqual(total_anomalies.count(), 2)
        
        mitra10_anomalies = PriceAnomaly.objects.filter(vendor='mitra10')
        gemilang_anomalies = PriceAnomaly.objects.filter(vendor='gemilang')
        
        self.assertEqual(mitra10_anomalies.count(), 1)
        self.assertEqual(gemilang_anomalies.count(), 1)
    
    def test_anomaly_ordering(self):
        """Test that anomalies are ordered by detected_at descending"""
        # Create multiple anomalies
        mitra10_service = Mitra10DatabaseService()
        
        for i in range(3):
            mitra10_service.save([{
                "name": f"Product {i}",
                "price": 10000,
                "url": f"https://test.com/{i}",
                "unit": "PCS"
            }])
            mitra10_service.save_with_price_update([{
                "name": f"Product {i}",
                "price": 12000,
                "url": f"https://test.com/{i}",
                "unit": "PCS"
            }])
        
        anomalies = list(PriceAnomaly.objects.all())
        
        # Check they're ordered by detected_at descending (newest first)
        for i in range(len(anomalies) - 1):
            self.assertGreaterEqual(
                anomalies[i].detected_at, 
                anomalies[i + 1].detected_at
            )
