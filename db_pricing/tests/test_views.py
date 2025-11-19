# db_pricing/tests/test_views.py
"""
Tests for price anomaly API views
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import json

from db_pricing.models import PriceAnomaly


class TestPriceAnomalyViews(TestCase):
    """Test suite for price anomaly API endpoints"""
    
    def setUp(self):
        """Set up test client and sample data"""
        self.client = Client()
        
        # Create sample anomalies
        self.anomaly1 = PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name='Test Product 1',
            product_url='https://example.com/product1',
            unit='pcs',
            location='Jakarta',
            old_price=100000,
            new_price=125000,
            change_percent=Decimal('25.00'),
            status='pending',
        )
        
        self.anomaly2 = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product 2',
            product_url='https://example.com/product2',
            unit='kg',
            location='',
            old_price=50000,
            new_price=40000,
            change_percent=Decimal('-20.00'),
            status='reviewed',
            notes='Price drop verified'
        )
        
        self.anomaly3 = PriceAnomaly.objects.create(
            vendor='tokopedia',
            product_name='Test Product 3',
            product_url='https://example.com/product3',
            unit='m',
            location='Bandung',
            old_price=75000,
            new_price=90000,
            change_percent=Decimal('20.00'),
            status='approved',
        )
    
    def test_list_anomalies_default(self):
        """Test listing all anomalies with default parameters"""
        response = self.client.get('/api/pricing/anomalies/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 3)
        self.assertEqual(data['pagination']['total_count'], 3)
        self.assertEqual(data['pagination']['page'], 1)
    
    def test_list_anomalies_filter_by_status(self):
        """Test filtering anomalies by status"""
        response = self.client.get('/api/pricing/anomalies/?status=pending')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['status'], 'pending')
        self.assertEqual(data['data'][0]['product_name'], 'Test Product 1')
    
    def test_list_anomalies_filter_by_vendor(self):
        """Test filtering anomalies by vendor"""
        response = self.client.get('/api/pricing/anomalies/?vendor=mitra10')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['vendor'], 'mitra10')
        self.assertEqual(data['data'][0]['product_name'], 'Test Product 2')
    
    def test_list_anomalies_search(self):
        """Test searching anomalies by product name"""
        response = self.client.get('/api/pricing/anomalies/?search=Product 1')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['product_name'], 'Test Product 1')
    
    def test_list_anomalies_pagination(self):
        """Test pagination"""
        # Create more anomalies
        for i in range(25):
            PriceAnomaly.objects.create(
                vendor='gemilang',
                product_name=f'Product {i}',
                product_url=f'https://example.com/product{i}',
                unit='pcs',
                old_price=10000,
                new_price=12000,
                change_percent=Decimal('20.00'),
                status='pending',
            )
        
        # Test first page
        response = self.client.get('/api/pricing/anomalies/?page=1&page_size=10')
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['data']), 10)
        self.assertTrue(data['pagination']['has_next'])
        self.assertFalse(data['pagination']['has_previous'])
        
        # Test second page
        response = self.client.get('/api/pricing/anomalies/?page=2&page_size=10')
        data = response.json()
        
        self.assertEqual(len(data['data']), 10)
        self.assertTrue(data['pagination']['has_next'])
        self.assertTrue(data['pagination']['has_previous'])
    
    def test_list_anomalies_invalid_page(self):
        """Test handling of invalid page number"""
        response = self.client.get('/api/pricing/anomalies/?page=invalid')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid parameter', data['error'])
    
    def test_get_anomaly_success(self):
        """Test getting a single anomaly by ID"""
        response = self.client.get(f'/api/pricing/anomalies/{self.anomaly1.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['id'], self.anomaly1.id)
        self.assertEqual(data['data']['product_name'], 'Test Product 1')
        self.assertEqual(data['data']['vendor'], 'gemilang')
        self.assertEqual(data['data']['old_price'], 100000)
        self.assertEqual(data['data']['new_price'], 125000)
        self.assertEqual(data['data']['change_percent'], 25.00)
        self.assertTrue(data['data']['is_price_increase'])
        self.assertEqual(data['data']['price_difference'], 25000)
    
    def test_get_anomaly_not_found(self):
        """Test getting a non-existent anomaly"""
        response = self.client.get('/api/pricing/anomalies/99999/')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Anomaly not found')
    
    def test_review_anomaly_approve(self):
        """Test approving an anomaly"""
        payload = {
            'status': 'approved',
            'notes': 'Price increase verified'
        }
        
        response = self.client.post(
            f'/api/pricing/anomalies/{self.anomaly1.id}/review/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['status'], 'approved')
        self.assertEqual(data['data']['notes'], 'Price increase verified')
        self.assertIsNotNone(data['data']['reviewed_at'])
        
        # Verify in database
        self.anomaly1.refresh_from_db()
        self.assertEqual(self.anomaly1.status, 'approved')
        self.assertEqual(self.anomaly1.notes, 'Price increase verified')
        self.assertIsNotNone(self.anomaly1.reviewed_at)
    
    def test_review_anomaly_reject(self):
        """Test rejecting an anomaly"""
        payload = {
            'status': 'rejected',
            'notes': 'Invalid data'
        }
        
        response = self.client.post(
            f'/api/pricing/anomalies/{self.anomaly1.id}/review/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['status'], 'rejected')
        
        # Verify in database
        self.anomaly1.refresh_from_db()
        self.assertEqual(self.anomaly1.status, 'rejected')
    
    def test_review_anomaly_invalid_status(self):
        """Test reviewing with invalid status"""
        payload = {
            'status': 'invalid_status',
            'notes': 'Test'
        }
        
        response = self.client.post(
            f'/api/pricing/anomalies/{self.anomaly1.id}/review/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Invalid status', data['error'])
    
    def test_review_anomaly_not_found(self):
        """Test reviewing a non-existent anomaly"""
        payload = {
            'status': 'approved',
            'notes': 'Test'
        }
        
        response = self.client.post(
            '/api/pricing/anomalies/99999/review/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Anomaly not found')
    
    def test_review_anomaly_invalid_json(self):
        """Test reviewing with invalid JSON"""
        response = self.client.post(
            f'/api/pricing/anomalies/{self.anomaly1.id}/review/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid JSON')
    
    def test_get_statistics(self):
        """Test getting anomaly statistics"""
        response = self.client.get('/api/pricing/anomalies/statistics/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['total_count'], 3)
        self.assertEqual(data['data']['pending_count'], 1)
        
        # Check status counts
        self.assertEqual(data['data']['by_status']['pending'], 1)
        self.assertEqual(data['data']['by_status']['reviewed'], 1)
        self.assertEqual(data['data']['by_status']['approved'], 1)
        
        # Check vendor counts
        self.assertEqual(data['data']['by_vendor']['gemilang'], 1)
        self.assertEqual(data['data']['by_vendor']['mitra10'], 1)
        self.assertEqual(data['data']['by_vendor']['tokopedia'], 1)
    
    def test_list_anomalies_response_structure(self):
        """Test that response includes all required fields"""
        response = self.client.get('/api/pricing/anomalies/')
        data = response.json()
        
        anomaly = data['data'][0]
        
        # Check all required fields are present
        required_fields = [
            'id', 'vendor', 'product_name', 'product_url', 'unit', 'location',
            'old_price', 'new_price', 'change_percent', 'price_difference',
            'is_price_increase', 'status', 'detected_at', 'reviewed_at', 'notes'
        ]
        
        for field in required_fields:
            self.assertIn(field, anomaly)
    
    def test_list_anomalies_ordering(self):
        """Test that anomalies are ordered by newest first"""
        # Create anomaly with specific time
        old_anomaly = PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name='Old Product',
            product_url='https://example.com/old',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=Decimal('20.00'),
            status='pending',
        )
        old_anomaly.detected_at = timezone.now() - timezone.timedelta(days=5)
        old_anomaly.save()
        
        response = self.client.get('/api/pricing/anomalies/')
        data = response.json()
        
        # First item should be newest
        self.assertNotEqual(data['data'][0]['product_name'], 'Old Product')
        # Last item should be oldest
        self.assertEqual(data['data'][-1]['product_name'], 'Old Product')
    
    def test_multiple_filters(self):
        """Test combining multiple filters"""
        # Create more test data
        PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name='Another Gemilang Product',
            product_url='https://example.com/product4',
            unit='pcs',
            old_price=20000,
            new_price=25000,
            change_percent=Decimal('25.00'),
            status='pending',
        )
        
        response = self.client.get('/api/pricing/anomalies/?vendor=gemilang&status=pending')
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['data']), 2)
        
        # Verify all results match both filters
        for anomaly in data['data']:
            self.assertEqual(anomaly['vendor'], 'gemilang')
            self.assertEqual(anomaly['status'], 'pending')
    
    def test_page_size_limit(self):
        """Test that page_size is capped at maximum"""
        # Try to request 200 items
        response = self.client.get('/api/pricing/anomalies/?page_size=200')
        data = response.json()
        
        # Should return max 100 even though 200 was requested
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(data['pagination']['page_size'], 100)


class TestDatabaseStatusView(TestCase):
    """Test suite for database status endpoint"""
    
    def test_database_status(self):
        """Test database status endpoint"""
        response = self.client.get('/api/pricing/status/')
        
        # Should return 200 or 503
        self.assertIn(response.status_code, [200, 503])
        
        data = response.json()
        
        # Check structure
        self.assertIn('connection', data)
        self.assertIn('gemilang_table', data)
        self.assertIn('overall_status', data)


class TestErrorHandling(TestCase):
    """Test suite for error handling in API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.client = Client()
    
    def test_list_anomalies_invalid_page_number(self):
        """Test handling invalid page number (ValueError)"""
        response = self.client.get('/api/pricing/anomalies/?page=invalid')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid parameter', data['error'])
    
    def test_list_anomalies_invalid_page_size(self):
        """Test handling invalid page_size (ValueError)"""
        response = self.client.get('/api/pricing/anomalies/?page_size=notanumber')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid parameter', data['error'])
    
    def test_list_anomalies_database_error(self):
        """Test handling database error in list endpoint"""
        from unittest.mock import patch
        
        with patch('db_pricing.views.PriceAnomaly.objects.all') as mock_all:
            mock_all.side_effect = Exception("Database connection error")
            response = self.client.get('/api/pricing/anomalies/')
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')
    
    def test_get_anomaly_not_found(self):
        """Test getting non-existent anomaly (DoesNotExist)"""
        response = self.client.get('/api/pricing/anomalies/99999/')
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Anomaly not found')
    
    def test_get_anomaly_database_error(self):
        """Test handling database error in get endpoint"""
        from unittest.mock import patch
        
        # Create an anomaly first
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        with patch('db_pricing.views.PriceAnomaly.objects.get') as mock_get:
            mock_get.side_effect = Exception("Database error")
            response = self.client.get(f'/api/pricing/anomalies/{anomaly.id}/')
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')
    
    def test_review_anomaly_invalid_json(self):
        """Test review endpoint with invalid JSON"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        response = self.client.post(
            f'/api/pricing/anomalies/{anomaly.id}/review/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid JSON')
    
    def test_review_anomaly_database_error(self):
        """Test handling database error in review endpoint"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        payload = {
            'status': 'approved',
            'notes': 'Approved'
        }
        
        with patch('db_pricing.views.PriceAnomalyService.mark_as_reviewed') as mock_mark:
            mock_mark.side_effect = Exception("Database error")
            response = self.client.post(
                f'/api/pricing/anomalies/{anomaly.id}/review/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')
    
    def test_get_statistics_database_error(self):
        """Test handling database error in statistics endpoint"""
        from unittest.mock import patch
        
        with patch('db_pricing.views.PriceAnomaly.objects.count') as mock_count:
            mock_count.side_effect = Exception("Database error")
            response = self.client.get('/api/pricing/anomalies/statistics/')
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')
    
    def test_apply_price_anomaly_success(self):
        """Test successfully applying a price anomaly"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='approved'
        )
        
        with patch('db_pricing.views.PriceAnomalyService.apply_approved_price') as mock_apply:
            mock_apply.return_value = {
                'success': True,
                'message': 'Price applied successfully',
                'updated': 1
            }
            
            response = self.client.post(f'/api/pricing/anomalies/{anomaly.id}/apply/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['anomaly_id'], anomaly.id)
        self.assertEqual(data['data']['updated'], 1)
    
    def test_apply_price_anomaly_not_found(self):
        """Test applying non-existent anomaly"""
        from unittest.mock import patch
        
        with patch('db_pricing.views.PriceAnomalyService.apply_approved_price') as mock_apply:
            mock_apply.return_value = {
                'success': False,
                'message': 'Anomaly not found'
            }
            
            response = self.client.post('/api/pricing/anomalies/99999/apply/')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_apply_price_anomaly_failure(self):
        """Test applying anomaly with service failure"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        with patch('db_pricing.views.PriceAnomalyService.apply_approved_price') as mock_apply:
            mock_apply.return_value = {
                'success': False,
                'message': 'Failed to update product'
            }
            
            response = self.client.post(f'/api/pricing/anomalies/{anomaly.id}/apply/')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_apply_price_anomaly_exception(self):
        """Test apply anomaly with exception"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        with patch('db_pricing.views.PriceAnomalyService.apply_approved_price') as mock_apply:
            mock_apply.side_effect = Exception("Database error")
            
            response = self.client.post(f'/api/pricing/anomalies/{anomaly.id}/apply/')
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')
    
    def test_reject_price_anomaly_success(self):
        """Test successfully rejecting a price anomaly"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        payload = {'notes': 'Rejected due to data error'}
        
        with patch('db_pricing.views.PriceAnomalyService.mark_as_reviewed') as mock_mark:
            mock_mark.return_value = {
                'success': True,
                'message': 'Anomaly rejected successfully'
            }
            
            response = self.client.post(
                f'/api/pricing/anomalies/{anomaly.id}/reject/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['anomaly_id'], anomaly.id)
    
    def test_reject_price_anomaly_not_found(self):
        """Test rejecting non-existent anomaly"""
        from unittest.mock import patch
        
        payload = {'notes': 'Test rejection'}
        
        with patch('db_pricing.views.PriceAnomalyService.mark_as_reviewed') as mock_mark:
            mock_mark.return_value = {
                'success': False,
                'message': 'Anomaly not found'
            }
            
            response = self.client.post(
                '/api/pricing/anomalies/99999/reject/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_reject_price_anomaly_invalid_json(self):
        """Test rejecting with invalid JSON"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        response = self.client.post(
            f'/api/pricing/anomalies/{anomaly.id}/reject/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid JSON')
    
    def test_reject_price_anomaly_exception(self):
        """Test reject anomaly with exception"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        payload = {'notes': 'Test'}
        
        with patch('db_pricing.views.PriceAnomalyService.reject_anomaly') as mock_reject:
            mock_reject.side_effect = Exception("Database error")
            
            response = self.client.post(
                f'/api/pricing/anomalies/{anomaly.id}/reject/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')
    
    def test_batch_apply_anomalies_success(self):
        """Test successfully applying multiple anomalies"""
        from unittest.mock import patch
        
        anomaly1 = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product 1',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='approved'
        )
        
        anomaly2 = PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name='Test Product 2',
            product_url='https://test.com/2',
            unit='box',
            old_price=20000,
            new_price=24000,
            change_percent=20.0,
            status='approved'
        )
        
        payload = {'anomaly_ids': [anomaly1.id, anomaly2.id]}
        
        with patch('db_pricing.views.PriceAnomalyService.batch_apply_approved') as mock_batch:
            mock_batch.return_value = {
                'applied_count': 2,
                'failed_count': 0,
                'results': []
            }
            
            response = self.client.post(
                '/api/pricing/anomalies/batch-apply/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['applied_count'], 2)
        self.assertEqual(data['data']['failed_count'], 0)
    
    def test_batch_apply_anomalies_empty_array(self):
        """Test batch apply with empty array"""
        payload = {'anomaly_ids': []}
        
        response = self.client.post(
            '/api/pricing/anomalies/batch-apply/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('required', data['error'])
    
    def test_batch_apply_anomalies_not_array(self):
        """Test batch apply with non-array input"""
        payload = {'anomaly_ids': 'not an array'}
        
        response = self.client.post(
            '/api/pricing/anomalies/batch-apply/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('must be an array', data['error'])
    
    def test_batch_apply_anomalies_invalid_json(self):
        """Test batch apply with invalid JSON"""
        response = self.client.post(
            '/api/pricing/anomalies/batch-apply/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid JSON')
    
    def test_batch_apply_anomalies_exception(self):
        """Test batch apply with exception"""
        from unittest.mock import patch
        
        payload = {'anomaly_ids': [1, 2, 3]}
        
        with patch('db_pricing.views.PriceAnomalyService.batch_apply_approved') as mock_batch:
            mock_batch.side_effect = Exception("Database error")
            
            response = self.client.post(
                '/api/pricing/anomalies/batch-apply/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')
    
    def test_approve_and_apply_anomaly_success(self):
        """Test successfully approving and applying anomaly"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='pending'
        )
        
        payload = {'notes': 'Approved and applied'}
        
        with patch('db_pricing.views.PriceAnomalyService.mark_as_reviewed') as mock_mark, \
             patch('db_pricing.views.PriceAnomalyService.apply_approved_price') as mock_apply:
            
            mock_mark.return_value = True
            mock_apply.return_value = {
                'success': True,
                'message': 'Price applied',
                'updated': 1
            }
            
            response = self.client.post(
                f'/api/pricing/anomalies/{anomaly.id}/approve-and-apply/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Anomaly approved and price applied', data['message'])
    
    def test_approve_and_apply_anomaly_not_found(self):
        """Test approve and apply with non-existent anomaly"""
        from unittest.mock import patch
        
        payload = {'notes': 'Test'}
        
        with patch('db_pricing.views.PriceAnomalyService.mark_as_reviewed') as mock_mark:
            mock_mark.return_value = False
            
            response = self.client.post(
                '/api/pricing/anomalies/99999/approve-and-apply/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Anomaly not found')
    
    def test_approve_and_apply_anomaly_apply_failure(self):
        """Test approve succeeds but apply fails"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='pending'
        )
        
        payload = {'notes': 'Test'}
        
        with patch('db_pricing.views.PriceAnomalyService.mark_as_reviewed') as mock_mark, \
             patch('db_pricing.views.PriceAnomalyService.apply_approved_price') as mock_apply:
            
            mock_mark.return_value = True
            mock_apply.return_value = {
                'success': False,
                'message': 'Failed to update product'
            }
            
            response = self.client.post(
                f'/api/pricing/anomalies/{anomaly.id}/approve-and-apply/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Approved but failed to apply', data['error'])
    
    def test_approve_and_apply_anomaly_invalid_json(self):
        """Test approve and apply with invalid JSON"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        response = self.client.post(
            f'/api/pricing/anomalies/{anomaly.id}/approve-and-apply/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid JSON')
    
    def test_approve_and_apply_anomaly_exception(self):
        """Test approve and apply with exception"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        payload = {'notes': 'Test'}
        
        with patch('db_pricing.views.PriceAnomalyService.mark_as_reviewed') as mock_mark:
            mock_mark.side_effect = Exception("Database error")
            
            response = self.client.post(
                f'/api/pricing/anomalies/{anomaly.id}/approve-and-apply/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')
    
    def test_list_anomalies_empty_page(self):
        """Test listing anomalies with page number beyond available pages"""
        response = self.client.get('/api/pricing/anomalies/?page=999')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        # Should return empty list or last page
        self.assertIsInstance(data['data'], list)
    
    def test_review_anomaly_mark_as_reviewed_fails(self):
        """Test review anomaly when mark_as_reviewed returns False"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        payload = {'status': 'approved', 'notes': 'Test'}
        
        with patch('db_pricing.views.PriceAnomalyService.mark_as_reviewed') as mock_mark:
            mock_mark.return_value = False
            
            response = self.client.post(
                f'/api/pricing/anomalies/{anomaly.id}/review/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Anomaly not found')
    
    def test_reject_anomaly_exception_handler(self):
        """Test reject anomaly exception handling"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='pcs',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        payload = {'notes': 'Test rejection'}
        
        with patch('db_pricing.views.PriceAnomalyService.reject_anomaly') as mock_reject:
            mock_reject.side_effect = Exception("Unexpected error")
            
            response = self.client.post(
                f'/api/pricing/anomalies/{anomaly.id}/reject/',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Internal server error')

