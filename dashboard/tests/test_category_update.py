"""
Unit tests for category update backend functionality.

This test suite uses mocks and stubs to test the category update service,
validators, and API endpoints without database dependencies.
"""

import json
from django.test import TestCase, RequestFactory
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from dashboard.services import CategoryUpdateService
from dashboard.category_validators import (
    CategoryLengthValidator,
    CategoryFormatValidator,
    CategoryBlacklistValidator,
    CompositeValidator,
    CategoryUpdateRequestValidator,
)
from dashboard import views_db


class CategoryValidatorTests(TestCase):
    """Test cases for individual category validators."""
    
    def test_length_validator_valid(self):
        """Test that valid length passes validation."""
        validator = CategoryLengthValidator(min_length=0, max_length=100)
        result = validator.validate("Valid Category")
        self.assertTrue(result["valid"])
    
    def test_length_validator_too_long(self):
        """Test that too-long category fails validation."""
        validator = CategoryLengthValidator(min_length=0, max_length=10)
        result = validator.validate("This is too long")
        self.assertFalse(result["valid"])
        self.assertIn("exceed", result["error"])
    
    def test_length_validator_too_short(self):
        """Test that too-short category fails validation."""
        validator = CategoryLengthValidator(min_length=5, max_length=100)
        result = validator.validate("abc")
        self.assertFalse(result["valid"])
        self.assertIn("at least", result["error"])
    
    def test_length_validator_none(self):
        """Test that None category fails validation."""
        validator = CategoryLengthValidator()
        result = validator.validate(None)
        self.assertFalse(result["valid"])
    
    def test_format_validator_valid(self):
        """Test that valid format passes validation."""
        validator = CategoryFormatValidator()
        result = validator.validate("Alat Listrik & Elektronik")
        self.assertTrue(result["valid"])
    
    def test_format_validator_empty(self):
        """Test that empty category is allowed."""
        validator = CategoryFormatValidator()
        result = validator.validate("")
        self.assertTrue(result["valid"])
    
    def test_format_validator_none(self):
        """Test that None category fails validation."""
        validator = CategoryFormatValidator()
        result = validator.validate(None)
        self.assertFalse(result["valid"])
    
    def test_format_validator_with_special_chars_disabled(self):
        """Test format validator with special chars disabled."""
        validator = CategoryFormatValidator(allow_special_chars=False)
        result = validator.validate("Valid Category")
        self.assertTrue(result["valid"])
    
    def test_format_validator_invalid_chars_when_disabled(self):
        """Test format validator rejects invalid chars when disabled."""
        validator = CategoryFormatValidator(allow_special_chars=False)
        result = validator.validate("Invalid@#$%Category")
        self.assertFalse(result["valid"])
        self.assertIn("invalid characters", result["error"])
    
    def test_blacklist_validator_blocked(self):
        """Test that blacklisted category fails validation."""
        validator = CategoryBlacklistValidator(blacklist=["spam", "test"])
        result = validator.validate("spam")
        self.assertFalse(result["valid"])
    
    def test_blacklist_validator_case_insensitive(self):
        """Test that blacklist is case-insensitive."""
        validator = CategoryBlacklistValidator(blacklist=["spam", "test"])
        result = validator.validate("SPAM")
        self.assertFalse(result["valid"])
    
    def test_blacklist_validator_allowed(self):
        """Test that non-blacklisted category passes validation."""
        validator = CategoryBlacklistValidator(blacklist=["spam", "test"])
        result = validator.validate("Valid Category")
        self.assertTrue(result["valid"])
    
    def test_blacklist_validator_none(self):
        """Test that None category fails validation in blacklist validator."""
        validator = CategoryBlacklistValidator(blacklist=["spam"])
        result = validator.validate(None)
        self.assertFalse(result["valid"])
    
    def test_composite_validator(self):
        """Test that composite validator runs all validators."""
        composite = CompositeValidator([
            CategoryLengthValidator(min_length=0, max_length=100),
            CategoryFormatValidator(),
        ])
        
        # Valid case
        result = composite.validate("Valid Category")
        self.assertTrue(result["valid"])
        
        # Invalid case (too long)
        result = composite.validate("x" * 101)
        self.assertFalse(result["valid"])
    
    def test_composite_validator_add_validator(self):
        """Test adding validator to composite dynamically."""
        composite = CompositeValidator([
            CategoryLengthValidator(min_length=0, max_length=100),
        ])
        
        # Add blacklist validator
        composite.add_validator(CategoryBlacklistValidator(blacklist=["spam"]))
        
        # Test that blacklist is enforced
        result = composite.validate("spam")
        self.assertFalse(result["valid"])


class CategoryUpdateRequestValidatorTests(TestCase):
    """Test cases for category update request validation."""
    
    def setUp(self):
        self.validator = CategoryUpdateRequestValidator()
    
    def test_validator_with_custom_category_validator(self):
        """Test initializing with custom category validator."""
        custom_validator = CategoryLengthValidator(min_length=5, max_length=50)
        validator = CategoryUpdateRequestValidator(category_validator=custom_validator)
        
        # Test that custom validator is used (min_length=5)
        result = validator.validate_update_request(
            source="Gemilang Store",
            product_url="https://example.com/product",
            new_category="ABC"  # Too short
        )
        self.assertFalse(result["valid"])
    
    def test_valid_request(self):
        """Test that valid request passes validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="https://example.com/product",
            new_category="Alat Listrik"
        )
        self.assertTrue(result["valid"])
    
    def test_missing_source(self):
        """Test that missing source fails validation."""
        result = self.validator.validate_update_request(
            source="",
            product_url="https://example.com/product",
            new_category="Alat Listrik"
        )
        self.assertFalse(result["valid"])
    
    def test_whitespace_only_source(self):
        """Test that whitespace-only source fails validation."""
        result = self.validator.validate_update_request(
            source="   ",  # Whitespace only
            product_url="https://example.com/product",
            new_category="Alat Listrik"
        )
        self.assertFalse(result["valid"])
        self.assertIn("cannot be empty", result["error"])
    
    def test_none_source(self):
        """Test that None source fails validation."""
        result = self.validator.validate_update_request(
            source=None,
            product_url="https://example.com/product",
            new_category="Alat Listrik"
        )
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing source", result["error"])
    
    def test_non_string_source(self):
        """Test that non-string source fails validation."""
        result = self.validator.validate_update_request(
            source=123,
            product_url="https://example.com/product",
            new_category="Alat Listrik"
        )
        self.assertFalse(result["valid"])
    
    def test_missing_url(self):
        """Test that missing URL fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="",
            new_category="Alat Listrik"
        )
        self.assertFalse(result["valid"])
    
    def test_whitespace_only_url(self):
        """Test that whitespace-only URL fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="   ",  # Whitespace only
            new_category="Alat Listrik"
        )
        self.assertFalse(result["valid"])
        self.assertIn("cannot be empty", result["error"])
    
    def test_none_url(self):
        """Test that None URL fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url=None,
            new_category="Alat Listrik"
        )
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing product_url", result["error"])
    
    def test_non_string_url(self):
        """Test that non-string URL fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url=456,
            new_category="Alat Listrik"
        )
        self.assertFalse(result["valid"])
    
    def test_any_url_format_accepted(self):
        """Test that any non-empty URL format is accepted (for compatibility with legacy data)."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="not-a-url",
            new_category="Alat Listrik"
        )
        self.assertTrue(result["valid"])
    
    def test_none_category(self):
        """Test that None category fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="https://example.com/product",
            new_category=None
        )
        self.assertFalse(result["valid"])
    
    def test_non_string_category(self):
        """Test that non-string category fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="https://example.com/product",
            new_category=789
        )
        self.assertFalse(result["valid"])
        self.assertIn("must be a string", result["error"])
    
    def test_bulk_request_valid(self):
        """Test that valid bulk request passes validation."""
        updates = [
            {
                "source": "Gemilang Store",
                "product_url": "https://example.com/product1",
                "new_category": "Category A"
            },
            {
                "source": "Mitra10",
                "product_url": "https://example.com/product2",
                "new_category": "Category B"
            }
        ]
        result = self.validator.validate_bulk_request(updates)
        self.assertTrue(result["valid"])
    
    def test_bulk_request_not_list(self):
        """Test that non-list bulk request fails validation."""
        result = self.validator.validate_bulk_request("not a list")
        self.assertFalse(result["valid"])
        self.assertIn("must be a list", result["error"])
    
    def test_bulk_request_empty(self):
        """Test that empty bulk request fails validation."""
        result = self.validator.validate_bulk_request([])
        self.assertFalse(result["valid"])
        self.assertIn("cannot be empty", result["error"])
    
    def test_bulk_request_too_large(self):
        """Test that oversized bulk request fails validation."""
        updates = [
            {
                "source": "Gemilang Store",
                "product_url": f"https://example.com/product{i}",
                "new_category": "Category"
            }
            for i in range(101)
        ]
        result = self.validator.validate_bulk_request(updates)
        self.assertFalse(result["valid"])
        self.assertIn("limited to 100", result["error"])
    
    def test_bulk_request_with_non_dict_item(self):
        """Test bulk request with non-dict item fails validation."""
        updates = [
            {
                "source": "Gemilang Store",
                "product_url": "https://example.com/product1",
                "new_category": "Category A"
            },
            "not a dict",  # Invalid item
        ]
        result = self.validator.validate_bulk_request(updates)
        self.assertFalse(result["valid"])
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["index"], 1)
    
    def test_bulk_request_with_invalid_items(self):
        """Test bulk request with invalid items."""
        updates = [
            {
                "source": "",  # Invalid empty source
                "product_url": "https://example.com/product1",
                "new_category": "Category A"
            },
            {
                "source": "Gemilang Store",
                "product_url": "not-a-url",  # Accepted for compatibility with legacy data
                "new_category": "Category B"
            }
        ]
        result = self.validator.validate_bulk_request(updates)
        self.assertFalse(result["valid"])
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 1)  # Only empty source causes error now


class CategoryUpdateServiceTests(TestCase):
    """Test cases for CategoryUpdateService using mocks."""
    
    def setUp(self):
        """Set up test mocks."""
        # Create mock product
        self.mock_product = Mock()
        self.mock_product.name = "Test Product 1"
        self.mock_product.price = 10000
        self.mock_product.url = "https://gemilang.com/product1"
        self.mock_product.unit = "pcs"
        self.mock_product.category = "Lainnya"
        self.mock_product.location = "Jakarta"
        self.mock_product.updated_at = datetime.now()
        self.mock_product.save = Mock()
    
    def test_update_category_success(self):
        """Test successful category update with mocked model."""
        with patch.object(CategoryUpdateService, 'VENDOR_MODEL_MAP') as mock_map:
            # Create a mock model class
            mock_model_class = Mock()
            mock_model_class.objects.get.return_value = self.mock_product
            mock_model_class.DoesNotExist = Exception
            
            # Setup the vendor map with the mock
            mock_map.__getitem__ = Mock(return_value=mock_model_class)
            mock_map.get = Mock(return_value=mock_model_class)
            
            service = CategoryUpdateService()
            result = service.update_category(
                source="Gemilang Store",
                product_url="https://gemilang.com/product1",
                new_category="Alat Listrik"
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["new_category"], "Alat Listrik")
            self.assertEqual(result["old_category"], "Lainnya")
            self.assertEqual(result["product_name"], "Test Product 1")
            
            # Verify save was called
            self.mock_product.save.assert_called_once()
    
    def test_update_category_validation_failure(self):
        """Test update with validation failure (empty source)."""
        service = CategoryUpdateService()
        result = service.update_category(
            source="",  # Invalid empty source
            product_url="https://gemilang.com/product1",
            new_category="Alat Listrik"
        )
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_update_category_invalid_source(self):
        """Test update with invalid source."""
        service = CategoryUpdateService()
        result = service.update_category(
            source="Invalid Vendor",
            product_url="https://gemilang.com/product1",
            new_category="Alat Listrik"
        )
        
        self.assertFalse(result["success"])
        self.assertIn("Invalid vendor", result["error"])
    
    def test_update_category_product_not_found(self):
        """Test update with non-existent product."""
        with patch.object(CategoryUpdateService, 'VENDOR_MODEL_MAP') as mock_map:
            # Create a mock model class that raises DoesNotExist
            mock_model_class = Mock()
            mock_model_class.DoesNotExist = Exception
            mock_model_class.objects.get.side_effect = mock_model_class.DoesNotExist
            
            # Setup the vendor map
            mock_map.get = Mock(return_value=mock_model_class)
            
            service = CategoryUpdateService()
            result = service.update_category(
                source="Gemilang Store",
                product_url="https://gemilang.com/nonexistent",
                new_category="Alat Listrik"
            )
            
            self.assertFalse(result["success"])
            self.assertIn("not found", result["error"])
    
    def test_bulk_update_success(self):
        """Test successful bulk update with mocked models."""
        with patch.object(CategoryUpdateService, 'VENDOR_MODEL_MAP') as mock_map:
            # Setup mocks
            mock_product1 = Mock()
            mock_product1.name = "Product 1"
            mock_product1.category = "Lainnya"
            mock_product1.updated_at = datetime.now()
            mock_product1.save = Mock()
            
            mock_product2 = Mock()
            mock_product2.name = "Product 2"
            mock_product2.category = "Lainnya"
            mock_product2.updated_at = datetime.now()
            mock_product2.save = Mock()
            
            # Create mock model classes
            mock_gemilang = Mock()
            mock_gemilang.objects.get.return_value = mock_product1
            mock_gemilang.DoesNotExist = Exception
            
            mock_mitra10 = Mock()
            mock_mitra10.objects.get.return_value = mock_product2
            mock_mitra10.DoesNotExist = Exception
            
            # Setup vendor map to return appropriate model based on source
            def get_model(source):
                if source == "Gemilang Store":
                    return mock_gemilang
                elif source == "Mitra10":
                    return mock_mitra10
                return None
            
            mock_map.get = Mock(side_effect=get_model)
            
            service = CategoryUpdateService()
            updates = [
                {
                    "source": "Gemilang Store",
                    "product_url": "https://gemilang.com/product1",
                    "new_category": "Category A"
                },
                {
                    "source": "Mitra10",
                    "product_url": "https://mitra10.com/product2",
                    "new_category": "Category B"
                }
            ]
            
            result = service.bulk_update_categories(updates)
            
            self.assertEqual(result["success_count"], 2)
            self.assertEqual(result["failure_count"], 0)
            
            # Verify save was called for both products
            mock_product1.save.assert_called_once()
            mock_product2.save.assert_called_once()
    
    def test_bulk_update_partial_failure(self):
        """Test bulk update with some failures."""
        with patch.object(CategoryUpdateService, 'VENDOR_MODEL_MAP') as mock_map:
            # Setup mock for successful update
            mock_product = Mock()
            mock_product.name = "Product 1"
            mock_product.category = "Lainnya"
            mock_product.updated_at = datetime.now()
            mock_product.save = Mock()
            
            mock_gemilang = Mock()
            mock_gemilang.objects.get.return_value = mock_product
            mock_gemilang.DoesNotExist = Exception
            
            # Setup vendor map to return model for valid vendor only
            def get_model(source):
                if source == "Gemilang Store":
                    return mock_gemilang
                return None
            
            mock_map.get = Mock(side_effect=get_model)
            
            service = CategoryUpdateService()
            updates = [
                {
                    "source": "Gemilang Store",
                    "product_url": "https://gemilang.com/product1",
                    "new_category": "Category A"
                },
                {
                    "source": "Invalid Vendor",
                    "product_url": "https://invalid.com/product",
                    "new_category": "Category B"
                }
            ]
            
            result = service.bulk_update_categories(updates)
            
            self.assertEqual(result["success_count"], 1)
            self.assertEqual(result["failure_count"], 1)
    
    def test_bulk_update_validation_failure(self):
        """Test bulk update with validation failure."""
        service = CategoryUpdateService()
        
        # Create updates with validation errors
        updates = [
            {
                "source": "",  # Invalid empty source
                "product_url": "https://gemilang.com/product1",
                "new_category": "Category A"
            },
            {
                "source": "Gemilang Store",
                "product_url": "not-a-url",  # Invalid URL format
                "new_category": "Category B"
            }
        ]
        
        result = service.bulk_update_categories(updates)
        
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failure_count"], 2)
        self.assertIn("validation_errors", result)
    
    def test_get_available_vendors(self):
        """Test getting available vendors."""
        service = CategoryUpdateService()
        vendors = service.get_available_vendors()
        
        self.assertIsInstance(vendors, list)
        self.assertIn("Gemilang Store", vendors)
        self.assertIn("Mitra10", vendors)


class CategoryUpdateAPITests(TestCase):
    """Test cases for category update API endpoints using mocks."""
    
    def setUp(self):
        """Set up request factory and mocks."""
        self.factory = RequestFactory()
    
    @patch('dashboard.views_db.CategoryUpdateService')
    def test_update_category_endpoint_success(self, mock_service_class):
        """Test successful category update via API with mocked service."""
        # Setup mock service
        mock_service = Mock()
        mock_service.update_category.return_value = {
            "success": True,
            "message": "Category updated successfully",
            "product_name": "Test Product",
            "old_category": "Lainnya",
            "new_category": "Alat Listrik",
            "vendor": "Gemilang Store",
            "updated_at": "2025-11-23T10:30:00.000Z"
        }
        mock_service_class.return_value = mock_service
        
        # Create request
        request = self.factory.post(
            '/dashboard/api/category/update/',
            data=json.dumps({
                "source": "Gemilang Store",
                "product_url": "https://gemilang.com/api-test",
                "new_category": "Alat Listrik"
            }),
            content_type='application/json'
        )
        
        # Call view
        response = views_db.update_product_category(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["new_category"], "Alat Listrik")
        
        # Verify service was called correctly
        mock_service.update_category.assert_called_once_with(
            "Gemilang Store",
            "https://gemilang.com/api-test",
            "Alat Listrik"
        )
    
    def test_update_category_endpoint_invalid_json(self):
        """Test API with invalid JSON."""
        request = self.factory.post(
            '/dashboard/api/category/update/',
            data="invalid json",
            content_type='application/json'
        )
        
        response = views_db.update_product_category(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Invalid JSON", data["error"])
    
    @patch('dashboard.views_db.CategoryUpdateService')
    def test_update_category_endpoint_server_error(self, mock_service_class):
        """Test API with unexpected server error."""
        # Setup mock service to raise exception
        mock_service = Mock()
        mock_service.update_category.side_effect = Exception("Database connection failed")
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/category/update/',
            data=json.dumps({
                "source": "Gemilang Store",
                "product_url": "https://gemilang.com/product",
                "new_category": "Alat Listrik"
            }),
            content_type='application/json'
        )
        
        response = views_db.update_product_category(request)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])
    
    @patch('dashboard.views_db.CategoryUpdateService')
    def test_update_category_endpoint_validation_error(self, mock_service_class):
        """Test API with validation error from service."""
        # Setup mock service to return validation error
        mock_service = Mock()
        mock_service.update_category.return_value = {
            "success": False,
            "error": "Invalid or missing product_url"
        }
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/category/update/',
            data=json.dumps({
                "source": "Gemilang Store",
                "product_url": "",
                "new_category": "Alat Listrik"
            }),
            content_type='application/json'
        )
        
        response = views_db.update_product_category(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
    
    @patch('dashboard.views_db.CategoryUpdateService')
    def test_bulk_update_endpoint_success(self, mock_service_class):
        """Test successful bulk update via API with mocked service."""
        # Setup mock service
        mock_service = Mock()
        mock_service.bulk_update_categories.return_value = {
            "success_count": 1,
            "failure_count": 0,
            "updates": [
                {
                    "success": True,
                    "message": "Category updated successfully",
                    "product_name": "Test Product",
                    "old_category": "Lainnya",
                    "new_category": "Category A",
                    "vendor": "Gemilang Store"
                }
            ]
        }
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/category/bulk-update/',
            data=json.dumps({
                "updates": [
                    {
                        "source": "Gemilang Store",
                        "product_url": "https://gemilang.com/api-test",
                        "new_category": "Category A"
                    }
                ]
            }),
            content_type='application/json'
        )
        
        response = views_db.bulk_update_categories(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["success_count"], 1)
        self.assertEqual(data["failure_count"], 0)
    
    def test_bulk_update_endpoint_invalid_updates_type(self):
        """Test bulk update with invalid updates type."""
        request = self.factory.post(
            '/dashboard/api/category/bulk-update/',
            data=json.dumps({
                "updates": "not a list"
            }),
            content_type='application/json'
        )
        
        response = views_db.bulk_update_categories(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("must be a list", data["error"])
    
    def test_bulk_update_endpoint_invalid_json(self):
        """Test bulk update API with invalid JSON."""
        request = self.factory.post(
            '/dashboard/api/category/bulk-update/',
            data="invalid json",
            content_type='application/json'
        )
        
        response = views_db.bulk_update_categories(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Invalid JSON", data["error"])
    
    @patch('dashboard.views_db.CategoryUpdateService')
    def test_bulk_update_endpoint_server_error(self, mock_service_class):
        """Test bulk update API with unexpected server error."""
        # Setup mock service to raise exception
        mock_service = Mock()
        mock_service.bulk_update_categories.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/category/bulk-update/',
            data=json.dumps({
                "updates": [
                    {
                        "source": "Gemilang Store",
                        "product_url": "https://gemilang.com/product",
                        "new_category": "Category A"
                    }
                ]
            }),
            content_type='application/json'
        )
        
        response = views_db.bulk_update_categories(request)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])
    
    @patch('dashboard.views_db.CategoryUpdateService')
    def test_get_vendors_endpoint(self, mock_service_class):
        """Test getting available vendors via API with mocked service."""
        # Setup mock service
        mock_service = Mock()
        mock_service.get_available_vendors.return_value = [
            "Gemilang Store",
            "Depo Bangunan",
            "Juragan Material",
            "Mitra10",
            "Tokopedia"
        ]
        mock_service_class.return_value = mock_service
        
        request = self.factory.get('/dashboard/api/vendors/')
        
        response = views_db.get_available_vendors(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertIsInstance(data["vendors"], list)
        self.assertEqual(len(data["vendors"]), 5)
    
    @patch('dashboard.views_db.CategoryUpdateService')
    def test_get_vendors_endpoint_server_error(self, mock_service_class):
        """Test get vendors API with unexpected server error."""
        # Setup mock service to raise exception
        mock_service = Mock()
        mock_service.get_available_vendors.side_effect = Exception("Service unavailable")
        mock_service_class.return_value = mock_service
        
        request = self.factory.get('/dashboard/api/vendors/')
        
        response = views_db.get_available_vendors(request)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])
