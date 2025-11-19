# db_pricing/tests/test_pending_approval_workflow.py
"""
Tests for the pending approval workflow where prices are NOT automatically updated
when anomalies are detected. Prices only update after admin approval.
"""

from django.test import TestCase
from db_pricing.models import (
    PriceAnomaly,
    GemilangProduct,
    Mitra10Product,
    TokopediaProduct,
    DepoBangunanProduct,
    JuraganMaterialProduct
)
from api.gemilang.database_service import GemilangDatabaseService
from api.mitra10.database_service import Mitra10DatabaseService
from api.tokopedia.database_service import TokopediaDatabaseService
from api.depobangunan.database_service import DepoBangunanDatabaseService
from api.juragan_material.database_service import JuraganMaterialDatabaseService
from db_pricing.anomaly_service import PriceAnomalyService


class TestGemilangPendingApproval(TestCase):
    """Test that Gemilang scraper does NOT auto-update prices for anomalies"""
    
    def setUp(self):
        PriceAnomaly.objects.all().delete()
        GemilangProduct.objects.all().delete()
        self.service = GemilangDatabaseService()
        
        # Create initial product
        initial_data = [{
            "name": "Test Product",
            "price": 10000,
            "url": "https://example.com/test",
            "unit": "PCS"
        }]
        self.service.save_with_price_update(initial_data)
    
    def test_large_price_increase_does_not_auto_update(self):
        """Test that price anomalies are NOT automatically applied"""
        # Attempt to update with 20% increase (anomaly threshold is 15%)
        updated_data = [{
            "name": "Test Product",
            "price": 12000,  # 20% increase
            "url": "https://example.com/test",
            "unit": "PCS"
        }]
        
        result = self.service.save_with_price_update(updated_data)
        
        # Anomaly should be detected
        self.assertEqual(len(result['anomalies']), 1)
        
        # Product price should NOT be updated (still 10000)
        product = GemilangProduct.objects.get(name="Test Product")
        self.assertEqual(product.price, 10000)  # Old price
        
        # Anomaly should be saved as pending
        anomaly = PriceAnomaly.objects.get(vendor='gemilang')
        self.assertEqual(anomaly.status, 'pending')
        self.assertEqual(anomaly.old_price, 10000)
        self.assertEqual(anomaly.new_price, 12000)
    
    def test_small_price_change_auto_updates(self):
        """Test that small price changes (< 15%) are automatically applied"""
        # Update with 10% increase (below anomaly threshold)
        updated_data = [{
            "name": "Test Product",
            "price": 11000,  # 10% increase
            "url": "https://example.com/test",
            "unit": "PCS"
        }]
        
        result = self.service.save_with_price_update(updated_data)
        
        # No anomaly should be detected
        self.assertEqual(len(result['anomalies']), 0)
        
        # Product price SHOULD be updated automatically
        product = GemilangProduct.objects.get(name="Test Product")
        self.assertEqual(product.price, 11000)  # New price
    
    def test_approved_anomaly_applies_price(self):
        """Test that approving and applying an anomaly updates the price"""
        # Create anomaly (price should NOT update)
        updated_data = [{
            "name": "Test Product",
            "price": 12000,  # 20% increase
            "url": "https://example.com/test",
            "unit": "PCS"
        }]
        self.service.save_with_price_update(updated_data)
        
        # Verify price is still old
        product = GemilangProduct.objects.get(name="Test Product")
        self.assertEqual(product.price, 10000)
        
        # Get the anomaly and approve it
        anomaly = PriceAnomaly.objects.get(vendor='gemilang')
        PriceAnomalyService.mark_as_reviewed(anomaly.id, 'approved', 'Verified')
        
        # Apply the approved price
        result = PriceAnomalyService.apply_approved_price(anomaly.id)
        self.assertTrue(result['success'])
        
        # Now price should be updated
        product.refresh_from_db()
        self.assertEqual(product.price, 12000)
        
        # Anomaly status should be 'applied'
        anomaly.refresh_from_db()
        self.assertEqual(anomaly.status, 'applied')


class TestMitra10PendingApproval(TestCase):
    """Test that Mitra10 scraper does NOT auto-update prices for anomalies"""
    
    def setUp(self):
        PriceAnomaly.objects.all().delete()
        Mitra10Product.objects.all().delete()
        self.service = Mitra10DatabaseService()
        
        # Create initial product
        self.service.save([{
            "name": "Mitra10 Product",
            "price": 15000,
            "url": "https://mitra10.com/product",
            "unit": "PCS"
        }])
    
    def test_price_anomaly_does_not_auto_update(self):
        """Test that detected anomalies do NOT automatically update prices"""
        updated_data = [{
            "name": "Mitra10 Product",
            "price": 18000,  # 20% increase
            "url": "https://mitra10.com/product",
            "unit": "PCS"
        }]
        
        result = self.service.save_with_price_update(updated_data)
        
        # Anomaly detected
        self.assertEqual(len(result['anomalies']), 1)
        
        # Price should NOT be updated
        product = Mitra10Product.objects.get(name="Mitra10 Product")
        self.assertEqual(product.price, 15000)  # Still old price
        
        # Anomaly saved as pending
        self.assertEqual(PriceAnomaly.objects.filter(vendor='mitra10').count(), 1)


class TestTokopediaPendingApproval(TestCase):
    """Test that Tokopedia scraper does NOT auto-update prices for anomalies"""
    
    def setUp(self):
        PriceAnomaly.objects.all().delete()
        TokopediaProduct.objects.all().delete()
        self.service = TokopediaDatabaseService()
        
        # Create initial product
        self.service.save([{
            "name": "Tokopedia Product",
            "price": 20000,
            "url": "https://tokopedia.com/product",
            "unit": "PCS",
            "location": "Jakarta"
        }])
    
    def test_price_anomaly_does_not_auto_update(self):
        """Test that detected anomalies do NOT automatically update prices"""
        updated_data = [{
            "name": "Tokopedia Product",
            "price": 25000,  # 25% increase
            "url": "https://tokopedia.com/product",
            "unit": "PCS",
            "location": "Jakarta"
        }]
        
        result = self.service.save_with_price_update(updated_data)
        
        # Anomaly detected
        self.assertEqual(len(result['anomalies']), 1)
        
        # Price should NOT be updated
        product = TokopediaProduct.objects.get(name="Tokopedia Product")
        self.assertEqual(product.price, 20000)  # Still old price


class TestDepoBangunanPendingApproval(TestCase):
    """Test that Depo Bangunan scraper does NOT auto-update prices for anomalies"""
    
    def setUp(self):
        PriceAnomaly.objects.all().delete()
        DepoBangunanProduct.objects.all().delete()
        self.service = DepoBangunanDatabaseService()
        
        # Create initial product
        self.service.save([{
            "name": "Depo Product",
            "price": 30000,
            "url": "https://depo.com/product",
            "unit": "PCS"
        }])
    
    def test_price_anomaly_does_not_auto_update(self):
        """Test that detected anomalies do NOT automatically update prices"""
        updated_data = [{
            "name": "Depo Product",
            "price": 36000,  # 20% increase
            "url": "https://depo.com/product",
            "unit": "PCS"
        }]
        
        result = self.service.save_with_price_update(updated_data)
        
        # Anomaly detected
        self.assertEqual(len(result['anomalies']), 1)
        
        # Price should NOT be updated
        product = DepoBangunanProduct.objects.get(name="Depo Product")
        self.assertEqual(product.price, 30000)  # Still old price


class TestJuraganMaterialPendingApproval(TestCase):
    """Test that Juragan Material scraper does NOT auto-update prices for anomalies"""
    
    def setUp(self):
        PriceAnomaly.objects.all().delete()
        JuraganMaterialProduct.objects.all().delete()
        self.service = JuraganMaterialDatabaseService()
        
        # Create initial product
        self.service.save([{
            "name": "Juragan Product",
            "price": 25000,
            "url": "https://juragan.com/product",
            "unit": "PCS",
            "location": "Jakarta"
        }])
    
    def test_price_anomaly_does_not_auto_update(self):
        """Test that detected anomalies do NOT automatically update prices"""
        updated_data = [{
            "name": "Juragan Product",
            "price": 30000,  # 20% increase
            "url": "https://juragan.com/product",
            "unit": "PCS",
            "location": "Jakarta"
        }]
        
        result = self.service.save_with_price_update(updated_data)
        
        # Anomaly detected
        self.assertEqual(len(result['anomalies']), 1)
        
        # Price should NOT be updated
        product = JuraganMaterialProduct.objects.get(name="Juragan Product")
        self.assertEqual(product.price, 25000)  # Still old price


class TestCompleteApprovalWorkflow(TestCase):
    """Test the complete workflow: detect → pending → approve → apply"""
    
    def setUp(self):
        PriceAnomaly.objects.all().delete()
        GemilangProduct.objects.all().delete()
        self.service = GemilangDatabaseService()
        
        # Create initial product
        self.service.save_with_price_update([{
            "name": "Workflow Test",
            "price": 10000,
            "url": "https://example.com/workflow",
            "unit": "PCS"
        }])
    
    def test_full_approval_workflow(self):
        """Test complete workflow from detection to final price update"""
        
        # Step 1: Scraper detects price change (anomaly)
        self.service.save_with_price_update([{
            "name": "Workflow Test",
            "price": 13000,  # 30% increase
            "url": "https://example.com/workflow",
            "unit": "PCS"
        }])
        
        # Verify: Anomaly saved, price NOT updated
        product = GemilangProduct.objects.get(name="Workflow Test")
        self.assertEqual(product.price, 10000)
        
        anomaly = PriceAnomaly.objects.get(vendor='gemilang')
        self.assertEqual(anomaly.status, 'pending')
        self.assertEqual(anomaly.new_price, 13000)
        
        # Step 2: Admin reviews and approves
        PriceAnomalyService.mark_as_reviewed(anomaly.id, 'approved', 'Price verified')
        
        # Verify: Status changed, but price still NOT updated
        product.refresh_from_db()
        self.assertEqual(product.price, 10000)
        anomaly.refresh_from_db()
        self.assertEqual(anomaly.status, 'approved')
        
        # Step 3: Admin applies the price
        result = PriceAnomalyService.apply_approved_price(anomaly.id)
        self.assertTrue(result['success'])
        
        # Verify: Price NOW updated, status is 'applied'
        product.refresh_from_db()
        self.assertEqual(product.price, 13000)
        anomaly.refresh_from_db()
        self.assertEqual(anomaly.status, 'applied')
    
    def test_rejected_anomaly_keeps_old_price(self):
        """Test that rejecting an anomaly keeps the old price"""
        
        # Step 1: Scraper detects price change
        self.service.save_with_price_update([{
            "name": "Workflow Test",
            "price": 15000,  # 50% increase
            "url": "https://example.com/workflow",
            "unit": "PCS"
        }])
        
        # Verify: Price NOT updated
        product = GemilangProduct.objects.get(name="Workflow Test")
        self.assertEqual(product.price, 10000)
        
        # Step 2: Admin rejects
        anomaly = PriceAnomaly.objects.get(vendor='gemilang')
        result = PriceAnomalyService.reject_anomaly(anomaly.id, 'Invalid data')
        self.assertTrue(result['success'])
        
        # Verify: Price STILL old price, status is 'rejected'
        product.refresh_from_db()
        self.assertEqual(product.price, 10000)  # No change
        anomaly.refresh_from_db()
        self.assertEqual(anomaly.status, 'rejected')
