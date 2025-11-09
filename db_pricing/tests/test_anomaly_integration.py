# db_pricing/tests/test_anomaly_integration.py
"""
Integration tests for price anomaly detection and notification across all vendors
"""

from django.test import TestCase
from db_pricing.models import (
    PriceAnomaly, 
    Mitra10Product, 
    GemilangProduct, 
    TokopediaProduct,
    DepoBangunanProduct,
    JuraganMaterialProduct
)
from api.mitra10.database_service import Mitra10DatabaseService
from api.gemilang.database_service import GemilangDatabaseService
from api.tokopedia.database_service import TokopediaDatabaseService
from api.depobangunan.database_service import DepoBangunanDatabaseService
from api.juragan_material.database_service import JuraganMaterialDatabaseService


class TestMitra10AnomalyIntegration(TestCase):
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
                "url": "https://mitra10.com/test",
                "unit": "PCS"
            }
        ]
        self.service.save(initial_data)
        
        # Update with 20% price increase (anomaly)
        updated_data = [
            {
                "name": "Mitra10 Test Product",
                "price": 12000,
                "url": "https://mitra10.com/test",
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
                "url": "https://mitra10.com/test",
                "unit": "PCS"
            }
        ]
        self.service.save(initial_data)
        
        # Update with 10% increase (below 15% threshold)
        updated_data = [
            {
                "name": "Mitra10 Product",
                "price": 11000,
                "url": "https://mitra10.com/test",
                "unit": "PCS"
            }
        ]
        result = self.service.save_with_price_update(updated_data)
        
        # No anomaly should be created
        self.assertEqual(len(result['anomalies']), 0)
        self.assertEqual(PriceAnomaly.objects.count(), 0)


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
