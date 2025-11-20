# db_pricing/tests/test_apply_anomaly.py
"""
Tests for applying approved price anomalies to the database
"""

from django.test import TestCase, Client
from django.urls import reverse
from db_pricing.models import (
    PriceAnomaly,
    GemilangProduct,
    Mitra10Product,
    TokopediaProduct,
    DepoBangunanProduct,
    JuraganMaterialProduct
)
from db_pricing.anomaly_service import PriceAnomalyService
import json


class TestApplyPriceAnomaly(TestCase):
    """Test applying approved price anomalies"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        PriceAnomaly.objects.all().delete()
        GemilangProduct.objects.all().delete()
        
        # Create a product
        self.product = GemilangProduct.objects.create(
            name="Test Product",
            price=10000,
            url="https://example.com/product",
            unit="PCS"
        )
        
        # Create an approved anomaly
        self.anomaly = PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name="Test Product",
            product_url="https://example.com/product",
            unit="PCS",
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='approved'
        )
    
    def test_apply_approved_anomaly(self):
        """Test applying an approved anomaly updates the product price"""
        # Apply the anomaly
        result = PriceAnomalyService.apply_approved_price(self.anomaly.id)
        
        # Check result
        self.assertTrue(result['success'])
        self.assertEqual(result['updated'], 1)
        
        # Check product was updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 12000)
        
        # Check anomaly status changed to applied
        self.anomaly.refresh_from_db()
        self.assertEqual(self.anomaly.status, 'applied')
    
    def test_apply_pending_anomaly_fails(self):
        """Test that pending anomalies cannot be applied"""
        # Create pending anomaly
        pending = PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name="Test Product 2",
            product_url="https://example.com/product2",
            unit="PCS",
            old_price=5000,
            new_price=6000,
            change_percent=20.0,
            status='pending'
        )
        
        # Try to apply
        result = PriceAnomalyService.apply_approved_price(pending.id)
        
        # Should fail
        self.assertFalse(result['success'])
        self.assertIn('must be approved', result['message'])
    
    def test_apply_nonexistent_anomaly(self):
        """Test applying non-existent anomaly"""
        result = PriceAnomalyService.apply_approved_price(99999)
        
        self.assertFalse(result['success'])
        self.assertIn('not found', result['message'])
    
    def test_apply_anomaly_no_matching_product(self):
        """Test applying anomaly when product doesn't exist"""
        # Create anomaly for non-existent product
        anomaly = PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name="Non Existent Product",
            product_url="https://example.com/nonexistent",
            unit="PCS",
            old_price=5000,
            new_price=6000,
            change_percent=20.0,
            status='approved'
        )
        
        # Try to apply
        result = PriceAnomalyService.apply_approved_price(anomaly.id)
        
        # Should fail
        self.assertFalse(result['success'])
        self.assertIn('No matching product', result['message'])


class TestApplyAnomalyAPI(TestCase):
    """Test the apply anomaly API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        PriceAnomaly.objects.all().delete()
        Mitra10Product.objects.all().delete()
        
        # Create a product
        self.product = Mitra10Product.objects.create(
            name="Mitra10 Product",
            price=20000,
            url="https://mitra10.com/product",
            unit="PCS"
        )
        
        # Create an approved anomaly
        self.anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name="Mitra10 Product",
            product_url="https://mitra10.com/product",
            unit="PCS",
            old_price=20000,
            new_price=25000,
            change_percent=25.0,
            status='approved'
        )
    
    def test_apply_anomaly_endpoint(self):
        """Test POST /anomalies/<id>/apply/"""
        url = reverse('db_pricing:apply_anomaly', kwargs={'anomaly_id': self.anomaly.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['updated'], 1)
        
        # Check product was updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 25000)
    
    def test_apply_anomaly_not_found(self):
        """Test applying non-existent anomaly"""
        url = reverse('db_pricing:apply_anomaly', kwargs={'anomaly_id': 99999})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])


class TestRejectAnomalyAPI(TestCase):
    """Test rejecting anomalies"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        PriceAnomaly.objects.all().delete()
        
        # Create a pending anomaly
        self.anomaly = PriceAnomaly.objects.create(
            vendor='tokopedia',
            product_name="Tokopedia Product",
            product_url="https://tokopedia.com/product",
            unit="PCS",
            old_price=15000,
            new_price=18000,
            change_percent=20.0,
            status='pending'
        )
    
    def test_reject_anomaly(self):
        """Test rejecting an anomaly"""
        result = PriceAnomalyService.reject_anomaly(
            self.anomaly.id,
            notes="Price data incorrect"
        )
        
        self.assertTrue(result['success'])
        
        # Check anomaly was rejected
        self.anomaly.refresh_from_db()
        self.assertEqual(self.anomaly.status, 'rejected')
        self.assertEqual(self.anomaly.notes, "Price data incorrect")
    
    def test_reject_anomaly_endpoint(self):
        """Test POST /anomalies/<id>/reject/"""
        url = reverse('db_pricing:reject_anomaly', kwargs={'anomaly_id': self.anomaly.id})
        response = self.client.post(
            url,
            data=json.dumps({'notes': 'Invalid data'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        
        # Check anomaly was rejected
        self.anomaly.refresh_from_db()
        self.assertEqual(self.anomaly.status, 'rejected')


class TestBatchApplyAnomalies(TestCase):
    """Test batch applying multiple anomalies"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        PriceAnomaly.objects.all().delete()
        DepoBangunanProduct.objects.all().delete()
        
        # Create products
        self.product1 = DepoBangunanProduct.objects.create(
            name="Product 1",
            price=10000,
            url="https://depo.com/product1",
            unit="PCS"
        )
        
        self.product2 = DepoBangunanProduct.objects.create(
            name="Product 2",
            price=20000,
            url="https://depo.com/product2",
            unit="PCS"
        )
        
        # Create approved anomalies
        self.anomaly1 = PriceAnomaly.objects.create(
            vendor='depobangunan',
            product_name="Product 1",
            product_url="https://depo.com/product1",
            unit="PCS",
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='approved'
        )
        
        self.anomaly2 = PriceAnomaly.objects.create(
            vendor='depobangunan',
            product_name="Product 2",
            product_url="https://depo.com/product2",
            unit="PCS",
            old_price=20000,
            new_price=24000,
            change_percent=20.0,
            status='approved'
        )
    
    def test_batch_apply_multiple_anomalies(self):
        """Test applying multiple anomalies at once"""
        result = PriceAnomalyService.batch_apply_approved([
            self.anomaly1.id,
            self.anomaly2.id
        ])
        
        self.assertTrue(result['success'])
        self.assertEqual(result['applied_count'], 2)
        self.assertEqual(result['failed_count'], 0)
        
        # Check products were updated
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.price, 12000)
        self.assertEqual(self.product2.price, 24000)
    
    def test_batch_apply_endpoint(self):
        """Test POST /anomalies/batch-apply/"""
        url = reverse('db_pricing:batch_apply_anomalies')
        response = self.client.post(
            url,
            data=json.dumps({
                'anomaly_ids': [self.anomaly1.id, self.anomaly2.id]
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['applied_count'], 2)
        self.assertEqual(data['data']['failed_count'], 0)


class TestApproveAndApply(TestCase):
    """Test approve and apply in one step"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        PriceAnomaly.objects.all().delete()
        JuraganMaterialProduct.objects.all().delete()
        
        # Create product
        self.product = JuraganMaterialProduct.objects.create(
            name="Juragan Product",
            price=30000,
            url="https://juragan.com/product",
            unit="PCS",
            location="Jakarta"
        )
        
        # Create pending anomaly
        self.anomaly = PriceAnomaly.objects.create(
            vendor='juragan_material',
            product_name="Juragan Product",
            product_url="https://juragan.com/product",
            unit="PCS",
            location="Jakarta",
            old_price=30000,
            new_price=36000,
            change_percent=20.0,
            status='pending'
        )
    
    def test_approve_and_apply_endpoint(self):
        """Test POST /anomalies/<id>/approve-and-apply/"""
        url = reverse('db_pricing:approve_and_apply_anomaly', kwargs={'anomaly_id': self.anomaly.id})
        response = self.client.post(
            url,
            data=json.dumps({'notes': 'Verified with vendor'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('approved and price applied', data['message'])
        
        # Check anomaly was approved and applied
        self.anomaly.refresh_from_db()
        self.assertEqual(self.anomaly.status, 'applied')
        self.assertEqual(self.anomaly.notes, 'Verified with vendor')
        
        # Check product was updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 36000)
