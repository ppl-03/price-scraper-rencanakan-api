# db_pricing/tests/test_anomaly_service.py
"""
Tests for the PriceAnomalyService
"""

from django.test import TestCase
from django.utils import timezone
from django.db import DatabaseError
from db_pricing.models import PriceAnomaly
from db_pricing.anomaly_service import PriceAnomalyService


class TestPriceAnomalyService(TestCase):
    """Test cases for PriceAnomalyService"""
    
    def setUp(self):
        """Set up test data"""
        PriceAnomaly.objects.all().delete()
    
    def test_save_anomalies_mitra10_success(self):
        """Test saving Mitra10 anomalies successfully"""
        anomalies = [
            {
                "name": "Test Product 1",
                "url": "https://mitra10.com/product1",
                "unit": "PCS",
                "old_price": 10000,
                "new_price": 12000,
                "change_percent": 20.0
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('mitra10', anomalies)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 1)
        self.assertEqual(len(result['errors']), 0)
        
        # Verify database record
        saved_anomaly = PriceAnomaly.objects.get(product_name="Test Product 1")
        self.assertEqual(saved_anomaly.vendor, 'mitra10')
        self.assertEqual(saved_anomaly.old_price, 10000)
        self.assertEqual(saved_anomaly.new_price, 12000)
        self.assertEqual(float(saved_anomaly.change_percent), 20.0)
        self.assertEqual(saved_anomaly.status, 'pending')
        self.assertEqual(saved_anomaly.location, '')  # No location for Mitra10
    
    def test_save_anomalies_gemilang_success(self):
        """Test saving Gemilang anomalies successfully"""
        anomalies = [
            {
                "name": "Gemilang Product",
                "url": "https://gemilang.com/product",
                "unit": "BOX",
                "old_price": 50000,
                "new_price": 60000,
                "change_percent": 20.0
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('gemilang', anomalies)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 1)
        
        saved_anomaly = PriceAnomaly.objects.get(vendor='gemilang')
        self.assertEqual(saved_anomaly.product_name, "Gemilang Product")
        self.assertEqual(saved_anomaly.location, '')  # No location for Gemilang
    
    def test_save_anomalies_tokopedia_with_location(self):
        """Test saving Tokopedia anomalies with location"""
        anomalies = [
            {
                "name": "Tokopedia Product",
                "url": "https://tokopedia.com/product",
                "unit": "PCS",
                "location": "Jakarta",
                "old_price": 25000,
                "new_price": 30000,
                "change_percent": 20.0
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('tokopedia', anomalies)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 1)
        
        saved_anomaly = PriceAnomaly.objects.get(vendor='tokopedia')
        self.assertEqual(saved_anomaly.location, 'Jakarta')  # Has location
    
    def test_save_anomalies_juragan_material_with_location(self):
        """Test saving JuraganMaterial anomalies with location"""
        anomalies = [
            {
                "name": "JM Product",
                "url": "https://jm.com/product",
                "unit": "M",
                "location": "Bandung",
                "old_price": 15000,
                "new_price": 18000,
                "change_percent": 20.0
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('juragan_material', anomalies)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 1)
        
        saved_anomaly = PriceAnomaly.objects.get(vendor='juragan_material')
        self.assertEqual(saved_anomaly.location, 'Bandung')
    
    def test_save_anomalies_depobangunan_success(self):
        """Test saving DepoBangunan anomalies successfully"""
        anomalies = [
            {
                "name": "Depo Product",
                "url": "https://depobangunan.com/product",
                "unit": "UNIT",
                "old_price": 100000,
                "new_price": 120000,
                "change_percent": 20.0
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('depobangunan', anomalies)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 1)
        
        saved_anomaly = PriceAnomaly.objects.get(vendor='depobangunan')
        self.assertEqual(saved_anomaly.product_name, "Depo Product")
    
    def test_save_multiple_anomalies(self):
        """Test saving multiple anomalies at once"""
        anomalies = [
            {
                "name": "Product 1",
                "url": "https://test.com/1",
                "unit": "PCS",
                "old_price": 10000,
                "new_price": 12000,
                "change_percent": 20.0
            },
            {
                "name": "Product 2",
                "url": "https://test.com/2",
                "unit": "BOX",
                "old_price": 20000,
                "new_price": 18000,
                "change_percent": -10.0
            },
            {
                "name": "Product 3",
                "url": "https://test.com/3",
                "unit": "M",
                "old_price": 30000,
                "new_price": 36000,
                "change_percent": 20.0
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('mitra10', anomalies)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 3)
        self.assertEqual(PriceAnomaly.objects.count(), 3)
    
    def test_save_anomalies_empty_list(self):
        """Test saving empty anomalies list"""
        result = PriceAnomalyService.save_anomalies('mitra10', [])
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 0)
        self.assertEqual(len(result['errors']), 0)
    
    def test_save_anomalies_invalid_vendor(self):
        """Test saving anomalies with invalid vendor"""
        anomalies = [
            {
                "name": "Test Product",
                "url": "https://test.com/product",
                "unit": "PCS",
                "old_price": 10000,
                "new_price": 12000,
                "change_percent": 20.0
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('invalid_vendor', anomalies)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['saved_count'], 0)
        self.assertGreater(len(result['errors']), 0)
        self.assertIn('Invalid vendor', result['errors'][0])
    
    def test_save_anomalies_missing_required_fields(self):
        """Test saving anomalies with missing required fields"""
        anomalies = [
            {
                "unit": "PCS",
                "old_price": 10000,
                "new_price": 12000,
                "change_percent": 20.0
                # Missing name and url
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('mitra10', anomalies)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 0)
        self.assertGreater(len(result['errors']), 0)
    
    def test_save_anomalies_partial_success(self):
        """Test saving anomalies with some valid and some invalid"""
        anomalies = [
            {
                "name": "Valid Product",
                "url": "https://test.com/valid",
                "unit": "PCS",
                "old_price": 10000,
                "new_price": 12000,
                "change_percent": 20.0
            },
            {
                # Missing required fields
                "unit": "BOX",
                "old_price": 20000,
                "new_price": 18000,
            },
            {
                "name": "Another Valid",
                "url": "https://test.com/valid2",
                "unit": "M",
                "old_price": 30000,
                "new_price": 36000,
                "change_percent": 20.0
            }
        ]
        
        result = PriceAnomalyService.save_anomalies('mitra10', anomalies)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 2)  # Only valid ones saved
        self.assertEqual(len(result['errors']), 1)  # One error for invalid
    
    def test_get_pending_anomalies_all(self):
        """Test getting all pending anomalies"""
        # Create test anomalies
        PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Product 1',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='pending'
        )
        PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name='Product 2',
            product_url='https://test.com/2',
            unit='BOX',
            old_price=20000,
            new_price=24000,
            change_percent=20.0,
            status='pending'
        )
        PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Product 3',
            product_url='https://test.com/3',
            unit='M',
            old_price=30000,
            new_price=36000,
            change_percent=20.0,
            status='reviewed'  # Not pending
        )
        
        pending = PriceAnomalyService.get_pending_anomalies()
        
        self.assertEqual(len(pending), 2)
        self.assertTrue(all(a.status == 'pending' for a in pending))
    
    def test_get_pending_anomalies_by_vendor(self):
        """Test getting pending anomalies filtered by vendor"""
        PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Mitra Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='pending'
        )
        PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name='Gemilang Product',
            product_url='https://test.com/2',
            unit='BOX',
            old_price=20000,
            new_price=24000,
            change_percent=20.0,
            status='pending'
        )
        
        mitra_pending = PriceAnomalyService.get_pending_anomalies('mitra10')
        
        self.assertEqual(len(mitra_pending), 1)
        self.assertEqual(mitra_pending[0].vendor, 'mitra10')
    
    def test_mark_as_reviewed_success(self):
        """Test marking anomaly as reviewed"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='pending'
        )
        
        result = PriceAnomalyService.mark_as_reviewed(
            anomaly.id, 
            status='approved', 
            notes='Price increase verified'
        )
        
        self.assertTrue(result)
        
        anomaly.refresh_from_db()
        self.assertEqual(anomaly.status, 'approved')
        self.assertEqual(anomaly.notes, 'Price increase verified')
        self.assertIsNotNone(anomaly.reviewed_at)
    
    def test_mark_as_reviewed_not_found(self):
        """Test marking non-existent anomaly as reviewed"""
        result = PriceAnomalyService.mark_as_reviewed(99999, status='reviewed')
        
        self.assertFalse(result)
    
    def test_anomaly_is_price_increase(self):
        """Test the is_price_increase property"""
        increase_anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Increase Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        decrease_anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Decrease Product',
            product_url='https://test.com/2',
            unit='PCS',
            old_price=10000,
            new_price=8000,
            change_percent=-20.0
        )
        
        self.assertTrue(increase_anomaly.is_price_increase)
        self.assertFalse(decrease_anomaly.is_price_increase)
    
    def test_anomaly_price_difference(self):
        """Test the price_difference property"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        self.assertEqual(anomaly.price_difference, 2000)
    
    def test_anomaly_str_representation(self):
        """Test the string representation of PriceAnomaly"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        expected = "mitra10 - Test Product (20.0% change)"
        self.assertEqual(str(anomaly), expected)
    
    def test_save_anomalies_database_error_in_loop(self):
        """Test handling database error while saving individual anomalies"""
        from unittest.mock import patch, MagicMock
        
        anomalies = [
            {
                "name": "Good Product",
                "url": "https://test.com/1",
                "unit": "PCS",
                "old_price": 10000,
                "new_price": 12000,
                "change_percent": 20.0
            },
            {
                "name": "Bad Product",
                "url": "https://test.com/2",
                "unit": "PCS",
                "old_price": 10000,
                "new_price": 12000,
                "change_percent": 20.0
            }
        ]
        
        # Mock PriceAnomaly.objects.create to raise exception on second call
        create_count = [0]
        original_create = PriceAnomaly.objects.create
        
        def mock_create(*args, **kwargs):
            create_count[0] += 1
            if create_count[0] == 2:
                raise DatabaseError("Database error")
            return original_create(*args, **kwargs)
        
        with patch.object(PriceAnomaly.objects, 'create', side_effect=mock_create):
            result = PriceAnomalyService.save_anomalies('mitra10', anomalies)
        
        # Should still succeed but with errors
        self.assertTrue(result['success'])
        self.assertEqual(result['saved_count'], 1)  # Only first one saved
        self.assertEqual(len(result['errors']), 1)  # One error logged
        self.assertIn("Error saving anomaly Bad Product", result['errors'][0])
    
    def test_save_anomalies_transaction_error(self):
        """Test handling transaction-level error"""
        from unittest.mock import patch
        
        anomalies = [
            {
                "name": "Test Product",
                "url": "https://test.com/1",
                "unit": "PCS",
                "old_price": 10000,
                "new_price": 12000,
                "change_percent": 20.0
            }
        ]
        
        # Mock transaction.atomic to raise exception
        with patch('db_pricing.anomaly_service.transaction.atomic') as mock_atomic:
            mock_atomic.side_effect = Exception("Transaction error")
            result = PriceAnomalyService.save_anomalies('mitra10', anomalies)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['saved_count'], 0)
        self.assertEqual(len(result['errors']), 1)
        self.assertIn("Transaction error", result['errors'][0])
    
    def test_mark_as_reviewed_not_found(self):
        """Test marking non-existent anomaly as reviewed"""
        result = PriceAnomalyService.mark_as_reviewed(99999, 'approved', 'Test notes')
        self.assertFalse(result)
    
    def test_mark_as_reviewed_database_error(self):
        """Test handling database error when marking as reviewed"""
        from unittest.mock import patch
        
        # Create an anomaly
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        # Mock save to raise exception
        with patch.object(PriceAnomaly, 'save', side_effect=Exception("Database error")):
            result = PriceAnomalyService.mark_as_reviewed(anomaly.id, 'approved', 'Test')
        
        self.assertFalse(result)
    
    def test_apply_anomaly_unknown_vendor(self):
        """Test applying anomaly with unknown vendor"""
        anomaly = PriceAnomaly.objects.create(
            vendor='unknown_vendor',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='approved'  # Must be approved to apply
        )
        
        result = PriceAnomalyService.apply_approved_price(anomaly.id)
        
        self.assertFalse(result['success'])
        self.assertIn('Unknown vendor', result['message'])
        self.assertEqual(result['updated'], 0)
    
    def test_apply_anomaly_not_found(self):
        """Test applying non-existent anomaly"""
        result = PriceAnomalyService.apply_approved_price(99999)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Anomaly not found')
        self.assertEqual(result['updated'], 0)
    
    def test_apply_anomaly_exception(self):
        """Test apply anomaly with exception during execution"""
        from unittest.mock import patch, MagicMock
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='approved'  # Must be approved to apply
        )
        
        with patch('db_pricing.anomaly_service.PriceAnomaly.objects.get') as mock_get:
            mock_anomaly = MagicMock()
            mock_anomaly.status = 'approved'
            mock_anomaly.vendor = 'mitra10'
            mock_anomaly.new_price = 12000
            mock_anomaly.product_url = 'https://test.com/1'
            mock_get.return_value = mock_anomaly
            
            with patch('db_pricing.anomaly_service.connection.cursor') as mock_cursor:
                mock_cursor.side_effect = Exception("Database connection error")
                
                result = PriceAnomalyService.apply_approved_price(anomaly.id)
        
        self.assertFalse(result['success'])
        self.assertIn('Error applying price', result['message'])
        self.assertEqual(result['updated'], 0)
    
    def test_reject_anomaly_already_rejected(self):
        """Test rejecting an already rejected anomaly"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='rejected'
        )
        
        result = PriceAnomalyService.reject_anomaly(anomaly.id, 'Already rejected')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Anomaly already rejected')
    
    def test_reject_anomaly_not_found(self):
        """Test rejecting non-existent anomaly"""
        result = PriceAnomalyService.reject_anomaly(99999, 'Test notes')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Anomaly not found')
    
    def test_reject_anomaly_exception(self):
        """Test reject anomaly with exception"""
        from unittest.mock import patch
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        with patch.object(PriceAnomaly, 'save', side_effect=Exception("Save error")):
            result = PriceAnomalyService.reject_anomaly(anomaly.id, 'Test notes')
        
        self.assertFalse(result['success'])
        self.assertIn('Error rejecting anomaly', result['message'])
    
    def test_batch_apply_anomalies_mixed_results(self):
        """Test batch apply with some successes and failures"""
        from unittest.mock import patch
        
        anomaly1 = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Product 1',
            product_url='https://test.com/1',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='approved'
        )
        
        anomaly2 = PriceAnomaly.objects.create(
            vendor='unknown_vendor',
            product_name='Product 2',
            product_url='https://test.com/2',
            unit='PCS',
            old_price=15000,
            new_price=18000,
            change_percent=20.0,
            status='approved'
        )
        
        result = PriceAnomalyService.batch_apply_approved([anomaly1.id, anomaly2.id])
        
        # Should have at least one failure (unknown vendor)
        self.assertGreater(result['failed_count'], 0)
        self.assertEqual(result['applied_count'] + result['failed_count'], 2)
