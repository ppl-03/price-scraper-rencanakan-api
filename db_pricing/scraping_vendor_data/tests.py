from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.db import connection
import json

from .models import ScrapingVendorData
from .services import (
    DjangoScrapingVendorDataRepository, 
    ScrapingVendorDataService, 
    RequiredFieldsValidator, 
    FieldLengthValidator,
    ScrapingVendorDataContext
)
from .validators import validate_vendor_data, ScrapingVendorDataValidationError


class ScrapingVendorDataModelTest(TestCase):
    """Test cases for ScrapingVendorData model."""
    
    def test_create_scraping_vendor_data(self):
        """Test creating a new scraping vendor data record."""
        vendor_data = ScrapingVendorData.objects.create(
            product_name="Test Product",
            price="10000",
            unit="kg",
            vendor="Test Vendor",
            location="Test Location"
        )
        
        self.assertEqual(vendor_data.product_name, "Test Product")
        self.assertEqual(vendor_data.price, "10000")
        self.assertEqual(vendor_data.unit, "kg")
        self.assertEqual(vendor_data.vendor, "Test Vendor")
        self.assertEqual(vendor_data.location, "Test Location")
        self.assertIsNotNone(vendor_data.created_at)
        self.assertIsNotNone(vendor_data.updated_at)
    
    def test_string_representation(self):
        """Test the string representation of the model."""
        vendor_data = ScrapingVendorData(
            product_name="Test Product",
            vendor="Test Vendor",
            location="Test Location"
        )
        
        expected = "Test Product - Test Vendor (Test Location)"
        self.assertEqual(str(vendor_data), expected)
    
    def test_table_name(self):
        """Test that the table name is correctly set."""
        self.assertEqual(ScrapingVendorData._meta.db_table, 'scraping_vendor_data')


class ScrapingVendorDataRepositoryTest(TestCase):
    """Test cases for DjangoScrapingVendorDataRepository."""
    
    def setUp(self):
        self.repository = DjangoScrapingVendorDataRepository()
        self.test_data = {
            'product_name': 'Test Product',
            'price': '15000',
            'unit': 'liter',
            'vendor': 'Test Vendor',
            'location': 'Test Location'
        }
    
    def test_create_vendor_data(self):
        """Test creating vendor data through repository."""
        vendor_data = self.repository.create(**self.test_data)
        
        self.assertIsInstance(vendor_data, ScrapingVendorData)
        self.assertEqual(vendor_data.product_name, self.test_data['product_name'])
        self.assertEqual(vendor_data.price, self.test_data['price'])
    
    def test_get_by_id(self):
        """Test getting vendor data by ID."""
        vendor_data = self.repository.create(**self.test_data)
        retrieved = self.repository.get_by_id(vendor_data.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, vendor_data.id)
        
        # Test non-existent ID
        non_existent = self.repository.get_by_id(99999)
        self.assertIsNone(non_existent)
    
    def test_get_all(self):
        """Test getting all vendor data."""
        # Create multiple records
        self.repository.create(**self.test_data)
        self.repository.create(
            product_name='Product 2',
            price='20000',
            unit='piece',
            vendor='Vendor 2',
            location='Location 2'
        )
        
        all_data = self.repository.get_all()
        self.assertEqual(len(all_data), 2)
    
    def test_filter_by_vendor(self):
        """Test filtering by vendor."""
        self.repository.create(**self.test_data)
        self.repository.create(
            product_name='Product 2',
            price='20000',
            unit='piece',
            vendor='Different Vendor',
            location='Location 2'
        )
        
        filtered = self.repository.filter_by_vendor('Test Vendor')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].vendor, 'Test Vendor')
    
    def test_filter_by_location(self):
        """Test filtering by location."""
        self.repository.create(**self.test_data)
        self.repository.create(
            product_name='Product 2',
            price='20000',
            unit='piece',
            vendor='Vendor 2',
            location='Different Location'
        )
        
        filtered = self.repository.filter_by_location('Test Location')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].location, 'Test Location')
    
    def test_update_vendor_data(self):
        """Test updating vendor data."""
        vendor_data = self.repository.create(**self.test_data)
        
        updated = self.repository.update(
            vendor_data.id,
            product_name='Updated Product',
            price='25000'
        )
        
        self.assertIsNotNone(updated)
        self.assertEqual(updated.product_name, 'Updated Product')
        self.assertEqual(updated.price, '25000')
        self.assertEqual(updated.vendor, 'Test Vendor')  # Unchanged
        
        # Test updating non-existent record
        non_existent_update = self.repository.update(99999, product_name='Test')
        self.assertIsNone(non_existent_update)
    
    def test_delete_vendor_data(self):
        """Test deleting vendor data."""
        vendor_data = self.repository.create(**self.test_data)
        
        success = self.repository.delete(vendor_data.id)
        self.assertTrue(success)
        
        # Verify deletion
        deleted = self.repository.get_by_id(vendor_data.id)
        self.assertIsNone(deleted)
        
        # Test deleting non-existent record
        non_existent_delete = self.repository.delete(99999)
        self.assertFalse(non_existent_delete)
    
    def test_table_exists(self):
        """Test checking if table exists."""
        # This should be True since Django creates the table for tests
        self.assertTrue(self.repository.table_exists())


class ScrapingVendorDataValidatorTest(TestCase):
    """Test cases for validators."""
    
    def test_required_fields_validator(self):
        """Test required fields validation."""
        validator = RequiredFieldsValidator()
        
        # Valid context
        valid_ctx = ScrapingVendorDataContext(
            product_name='Test Product',
            price='10000',
            unit='kg',
            vendor='Test Vendor',
            location='Test Location'
        )
        
        # Should not raise exception
        validator.validate(valid_ctx)
        
        # Invalid contexts
        invalid_contexts = [
            ScrapingVendorDataContext(product_name='', price='10000', unit='kg', vendor='Vendor', location='Location'),
            ScrapingVendorDataContext(product_name='Product', price='', unit='kg', vendor='Vendor', location='Location'),
            ScrapingVendorDataContext(product_name='Product', price='10000', unit='', vendor='Vendor', location='Location'),
            ScrapingVendorDataContext(product_name='Product', price='10000', unit='kg', vendor='', location='Location'),
            ScrapingVendorDataContext(product_name='Product', price='10000', unit='kg', vendor='Vendor', location=''),
        ]
        
        for ctx in invalid_contexts:
            with self.assertRaises(ValidationError):
                validator.validate(ctx)
    
    def test_field_length_validator(self):
        """Test field length validation."""
        validator = FieldLengthValidator()
        
        # Valid context
        valid_ctx = ScrapingVendorDataContext(
            product_name='Test Product',
            price='10000',
            unit='kg',
            vendor='Test Vendor',
            location='Test Location'
        )
        
        # Should not raise exception
        validator.validate(valid_ctx)
        
        # Invalid context with too long fields
        long_string = 'x' * 256  # Exceeds 255 character limit
        invalid_ctx = ScrapingVendorDataContext(
            product_name=long_string,
            price='10000',
            unit='kg',
            vendor='Test Vendor',
            location='Test Location'
        )
        
        with self.assertRaises(ValidationError):
            validator.validate(invalid_ctx)
    
    def test_standalone_validators(self):
        """Test standalone validator functions."""
        # Valid data
        validate_vendor_data(
            product_name='Test Product',
            price='10000',
            unit='kg',
            vendor='Test Vendor',
            location='Test Location'
        )
        
        # Invalid data - missing required field
        with self.assertRaises(ScrapingVendorDataValidationError):
            validate_vendor_data(
                product_name='',
                price='10000',
                unit='kg',
                vendor='Test Vendor',
                location='Test Location'
            )
        
        # Invalid data - field too long
        long_string = 'x' * 256
        with self.assertRaises(ScrapingVendorDataValidationError):
            validate_vendor_data(
                product_name=long_string,
                price='10000',
                unit='kg',
                vendor='Test Vendor',
                location='Test Location'
            )


class ScrapingVendorDataServiceTest(TestCase):
    """Test cases for ScrapingVendorDataService."""
    
    def setUp(self):
        repository = DjangoScrapingVendorDataRepository()
        validators = [RequiredFieldsValidator(), FieldLengthValidator()]
        self.service = ScrapingVendorDataService(repository, validators)
        
        self.test_data = {
            'product_name': 'Test Product',
            'price': '15000',
            'unit': 'liter',
            'vendor': 'Test Vendor',
            'location': 'Test Location'
        }
    
    def test_create_vendor_data_with_validation(self):
        """Test creating vendor data with validation through service."""
        vendor_data = self.service.create_vendor_data(**self.test_data)
        
        self.assertIsInstance(vendor_data, ScrapingVendorData)
        self.assertEqual(vendor_data.product_name, self.test_data['product_name'])
    
    def test_create_vendor_data_validation_failure(self):
        """Test validation failure when creating vendor data."""
        invalid_data = self.test_data.copy()
        invalid_data['product_name'] = ''  # Empty required field
        
        with self.assertRaises(ValidationError):
            self.service.create_vendor_data(**invalid_data)
    
    def test_get_vendor_data_operations(self):
        """Test various get operations through service."""
        vendor_data = self.service.create_vendor_data(**self.test_data)
        
        # Test get by ID
        retrieved = self.service.get_vendor_data_by_id(vendor_data.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, vendor_data.id)
        
        # Test get all
        all_data = self.service.get_all_vendor_data()
        self.assertGreaterEqual(len(all_data), 1)
        
        # Test get by vendor
        vendor_data_list = self.service.get_vendor_data_by_vendor('Test Vendor')
        self.assertEqual(len(vendor_data_list), 1)
        
        # Test get by location
        location_data_list = self.service.get_vendor_data_by_location('Test Location')
        self.assertEqual(len(location_data_list), 1)
    
    def test_update_vendor_data_with_validation(self):
        """Test updating vendor data with validation through service."""
        vendor_data = self.service.create_vendor_data(**self.test_data)
        
        # Valid update
        updated = self.service.update_vendor_data(
            vendor_data.id,
            product_name='Updated Product'
        )
        
        self.assertIsNotNone(updated)
        self.assertEqual(updated.product_name, 'Updated Product')
        
        # Invalid update
        with self.assertRaises(ValidationError):
            self.service.update_vendor_data(
                vendor_data.id,
                product_name=''  # Empty required field
            )
    
    def test_delete_vendor_data(self):
        """Test deleting vendor data through service."""
        vendor_data = self.service.create_vendor_data(**self.test_data)
        
        success = self.service.delete_vendor_data(vendor_data.id)
        self.assertTrue(success)
        
        # Verify deletion
        deleted = self.service.get_vendor_data_by_id(vendor_data.id)
        self.assertIsNone(deleted)


class ScrapingVendorDataViewTest(TestCase):
    """Test cases for ScrapingVendorData API views."""
    
    def setUp(self):
        self.client = Client()
        self.test_data = {
            'product_name': 'Test Product',
            'price': '15000',
            'unit': 'liter',
            'vendor': 'Test Vendor',
            'location': 'Test Location'
        }
        
        # Create test data
        self.vendor_data = ScrapingVendorData.objects.create(**self.test_data)
    
    def test_get_all_vendor_data(self):
        """Test GET request to retrieve all vendor data."""
        response = self.client.get('/scraping-vendor-data/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('data', data)
        self.assertGreaterEqual(len(data['data']), 1)
    
    def test_get_vendor_data_by_id(self):
        """Test GET request to retrieve specific vendor data."""
        response = self.client.get(f'/scraping-vendor-data/{self.vendor_data.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['id'], self.vendor_data.id)
        self.assertEqual(data['product_name'], self.test_data['product_name'])
    
    def test_get_vendor_data_not_found(self):
        """Test GET request for non-existent vendor data."""
        response = self.client.get('/scraping-vendor-data/99999/')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_post_create_vendor_data(self):
        """Test POST request to create new vendor data."""
        new_data = {
            'product_name': 'New Product',
            'price': '20000',
            'unit': 'piece',
            'vendor': 'New Vendor',
            'location': 'New Location'
        }
        
        response = self.client.post(
            '/scraping-vendor-data/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data['product_name'], new_data['product_name'])
        self.assertIn('id', data)
    
    def test_post_create_vendor_data_validation_error(self):
        """Test POST request with invalid data."""
        invalid_data = {
            'product_name': '',  # Empty required field
            'price': '20000',
            'unit': 'piece',
            'vendor': 'New Vendor',
            'location': 'New Location'
        }
        
        response = self.client.post(
            '/scraping-vendor-data/',
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_put_update_vendor_data(self):
        """Test PUT request to update vendor data."""
        update_data = {
            'product_name': 'Updated Product Name'
        }
        
        response = self.client.put(
            f'/scraping-vendor-data/{self.vendor_data.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['product_name'], update_data['product_name'])
    
    def test_put_update_vendor_data_not_found(self):
        """Test PUT request for non-existent vendor data."""
        update_data = {'product_name': 'Updated Product'}
        
        response = self.client.put(
            '/scraping-vendor-data/99999/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_delete_vendor_data(self):
        """Test DELETE request to remove vendor data."""
        response = self.client.delete(f'/scraping-vendor-data/{self.vendor_data.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('message', data)
        
        # Verify deletion
        self.assertFalse(ScrapingVendorData.objects.filter(id=self.vendor_data.id).exists())
    
    def test_delete_vendor_data_not_found(self):
        """Test DELETE request for non-existent vendor data."""
        response = self.client.delete('/scraping-vendor-data/99999/')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_get_vendor_data_filter_by_vendor(self):
        """Test GET request with vendor filter."""
        response = self.client.get('/scraping-vendor-data/?vendor=Test Vendor')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('data', data)
        
        # All returned items should have the specified vendor
        for item in data['data']:
            self.assertEqual(item['vendor'], 'Test Vendor')
    
    def test_get_vendor_data_filter_by_location(self):
        """Test GET request with location filter."""
        response = self.client.get('/scraping-vendor-data/?location=Test Location')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('data', data)
        
        # All returned items should have the specified location
        for item in data['data']:
            self.assertEqual(item['location'], 'Test Location')