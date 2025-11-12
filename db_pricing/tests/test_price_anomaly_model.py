# db_pricing/tests/test_price_anomaly_model.py
"""
Tests for the PriceAnomaly model
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from db_pricing.models import PriceAnomaly


class TestPriceAnomalyModel(TestCase):
    """Test cases for PriceAnomaly model"""
    
    def test_create_price_anomaly_all_fields(self):
        """Test creating a price anomaly with all fields"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/product',
            unit='PCS',
            location='Jakarta',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            status='pending',
            notes='Test anomaly'
        )
        
        self.assertEqual(anomaly.vendor, 'mitra10')
        self.assertEqual(anomaly.product_name, 'Test Product')
        self.assertEqual(anomaly.old_price, 10000)
        self.assertEqual(anomaly.new_price, 12000)
        self.assertEqual(float(anomaly.change_percent), 20.0)
        self.assertEqual(anomaly.status, 'pending')
        self.assertIsNotNone(anomaly.detected_at)
    
    def test_create_price_anomaly_without_optional_fields(self):
        """Test creating anomaly without optional fields"""
        anomaly = PriceAnomaly.objects.create(
            vendor='gemilang',
            product_name='Gemilang Product',
            product_url='https://gemilang.com/product',
            unit='BOX',
            old_price=50000,
            new_price=60000,
            change_percent=20.0
        )
        
        self.assertEqual(anomaly.location, '')
        self.assertEqual(anomaly.notes, '')
        self.assertEqual(anomaly.status, 'pending')
        self.assertIsNone(anomaly.reviewed_at)
    
    def test_vendor_choices(self):
        """Test that all vendor choices are valid"""
        valid_vendors = ['gemilang', 'mitra10', 'tokopedia', 'depobangunan', 'juragan_material']
        
        for vendor in valid_vendors:
            anomaly = PriceAnomaly.objects.create(
                vendor=vendor,
                product_name=f'{vendor} Product',
                product_url=f'https://{vendor}.com/product',
                unit='PCS',
                old_price=10000,
                new_price=12000,
                change_percent=20.0
            )
            self.assertEqual(anomaly.vendor, vendor)
    
    def test_status_choices(self):
        """Test that all status choices are valid"""
        statuses = ['pending', 'reviewed', 'approved', 'rejected']
        
        for status in statuses:
            anomaly = PriceAnomaly.objects.create(
                vendor='mitra10',
                product_name=f'Product {status}',
                product_url=f'https://test.com/{status}',
                unit='PCS',
                old_price=10000,
                new_price=12000,
                change_percent=20.0,
                status=status
            )
            self.assertEqual(anomaly.status, status)
    
    def test_is_price_increase_property(self):
        """Test is_price_increase property"""
        increase = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Increase Product',
            product_url='https://test.com/increase',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        decrease = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Decrease Product',
            product_url='https://test.com/decrease',
            unit='PCS',
            old_price=10000,
            new_price=8000,
            change_percent=-20.0
        )
        
        self.assertTrue(increase.is_price_increase)
        self.assertFalse(decrease.is_price_increase)
    
    def test_price_difference_property(self):
        """Test price_difference property"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/product',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        self.assertEqual(anomaly.price_difference, 2000)
        
        # Test with price decrease
        decrease = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Decrease Product',
            product_url='https://test.com/decrease',
            unit='PCS',
            old_price=10000,
            new_price=7000,
            change_percent=-30.0
        )
        
        self.assertEqual(decrease.price_difference, 3000)
    
    def test_negative_price_validation(self):
        """Test that negative prices are rejected"""
        with self.assertRaises(ValidationError):
            anomaly = PriceAnomaly(
                vendor='mitra10',
                product_name='Invalid Product',
                product_url='https://test.com/invalid',
                unit='PCS',
                old_price=-1000,
                new_price=12000,
                change_percent=20.0
            )
            anomaly.full_clean()
    
    def test_str_representation(self):
        """Test string representation of anomaly"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/product',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        expected = "mitra10 - Test Product (20.0% change)"
        self.assertEqual(str(anomaly), expected)
    
    def test_db_table_name(self):
        """Test that the correct database table name is used"""
        self.assertEqual(PriceAnomaly._meta.db_table, 'price_anomalies')
    
    def test_ordering(self):
        """Test default ordering by detected_at descending"""
        # Create multiple anomalies
        for i in range(3):
            PriceAnomaly.objects.create(
                vendor='mitra10',
                product_name=f'Product {i}',
                product_url=f'https://test.com/{i}',
                unit='PCS',
                old_price=10000,
                new_price=12000,
                change_percent=20.0
            )
        
        anomalies = list(PriceAnomaly.objects.all())
        
        # Check ordering (newest first)
        for i in range(len(anomalies) - 1):
            self.assertGreaterEqual(
                anomalies[i].detected_at,
                anomalies[i + 1].detected_at
            )
    
    def test_indexes_created(self):
        """Test that indexes are created on expected fields"""
        indexes = PriceAnomaly._meta.indexes
        index_fields = [idx.fields for idx in indexes]
        
        # Check that we have indexes on important fields
        self.assertTrue(any('vendor' in fields for fields in index_fields))
        self.assertTrue(any('status' in fields for fields in index_fields))
        self.assertTrue(any('detected_at' in fields for fields in index_fields))
        self.assertTrue(any('product_name' in fields for fields in index_fields))
    
    def test_update_reviewed_at(self):
        """Test updating reviewed_at timestamp"""
        from django.utils import timezone
        
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/product',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        self.assertIsNone(anomaly.reviewed_at)
        
        # Update status and reviewed_at
        anomaly.status = 'approved'
        anomaly.reviewed_at = timezone.now()
        anomaly.save()
        
        anomaly.refresh_from_db()
        self.assertEqual(anomaly.status, 'approved')
        self.assertIsNotNone(anomaly.reviewed_at)
    
    def test_large_price_values(self):
        """Test handling of large price values"""
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Expensive Product',
            product_url='https://test.com/expensive',
            unit='PCS',
            old_price=10000000,
            new_price=12000000,
            change_percent=20.0
        )
        
        self.assertEqual(anomaly.old_price, 10000000)
        self.assertEqual(anomaly.new_price, 12000000)
        self.assertEqual(anomaly.price_difference, 2000000)
    
    def test_long_product_name(self):
        """Test handling of long product names"""
        long_name = 'A' * 500
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name=long_name,
            product_url='https://test.com/long',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        self.assertEqual(len(anomaly.product_name), 500)
    
    def test_long_url(self):
        """Test handling of long URLs"""
        # 'https://test.com/' is 17 chars, so add 983 more to make exactly 1000
        long_url = 'https://test.com/' + 'a' * 983
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url=long_url,
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0
        )
        
        self.assertEqual(len(anomaly.product_url), 1000)
    
    def test_long_notes(self):
        """Test handling of long notes"""
        long_notes = 'Note ' * 1000
        anomaly = PriceAnomaly.objects.create(
            vendor='mitra10',
            product_name='Test Product',
            product_url='https://test.com/notes',
            unit='PCS',
            old_price=10000,
            new_price=12000,
            change_percent=20.0,
            notes=long_notes
        )
        
        self.assertEqual(anomaly.notes, long_notes)
