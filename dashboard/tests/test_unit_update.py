"""
Unit tests for unit update backend functionality.

This test suite uses mocks and stubs to test the unit update service,
validators, and API endpoints without database dependencies.
"""

import json
from django.test import TestCase, RequestFactory
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from dashboard.services import UnitUpdateService
from dashboard.unit_validators import (
    UnitLengthValidator,
    UnitFormatValidator,
    UnitBlacklistValidator,
    CompositeValidator,
    UnitUpdateRequestValidator,
)
from dashboard import views_db


class UnitValidatorTests(TestCase):
    """Test cases for individual unit validators."""
    
    def test_length_validator_valid(self):
        """Test that valid length passes validation."""
        validator = UnitLengthValidator(min_length=0, max_length=50)
        result = validator.validate("kg")
        self.assertTrue(result["valid"])
    
    def test_length_validator_too_long(self):
        """Test that too-long unit fails validation."""
        validator = UnitLengthValidator(min_length=0, max_length=10)
        result = validator.validate("This is too long for a unit")
        self.assertFalse(result["valid"])
        self.assertIn("exceed", result["error"])
    
    def test_length_validator_too_short(self):
        """Test that too-short unit fails validation."""
        validator = UnitLengthValidator(min_length=2, max_length=50)
        result = validator.validate("a")
        self.assertFalse(result["valid"])
        self.assertIn("at least", result["error"])
    
    def test_length_validator_none(self):
        """Test that None unit fails validation."""
        validator = UnitLengthValidator()
        result = validator.validate(None)
        self.assertFalse(result["valid"])
    
    def test_format_validator_valid(self):
        """Test that valid format passes validation."""
        validator = UnitFormatValidator()
        result = validator.validate("m²")
        self.assertTrue(result["valid"])
    
    def test_format_validator_valid_with_special_chars(self):
        """Test that unit with superscript passes validation."""
        validator = UnitFormatValidator()
        result = validator.validate("m³")
        self.assertTrue(result["valid"])
    
    def test_format_validator_empty(self):
        """Test that empty unit is allowed."""
        validator = UnitFormatValidator()
        result = validator.validate("")
        self.assertTrue(result["valid"])
    
    def test_format_validator_none(self):
        """Test that None unit fails validation."""
        validator = UnitFormatValidator()
        result = validator.validate(None)
        self.assertFalse(result["valid"])
    
    def test_format_validator_with_special_chars_disabled(self):
        """Test format validator with special chars disabled."""
        validator = UnitFormatValidator(allow_special_chars=False)
        result = validator.validate("kg")
        self.assertTrue(result["valid"])
    
    def test_format_validator_invalid_chars_when_disabled(self):
        """Test format validator rejects invalid chars when disabled."""
        validator = UnitFormatValidator(allow_special_chars=False)
        result = validator.validate("Invalid@#$%Unit")
        self.assertFalse(result["valid"])
        self.assertIn("invalid characters", result["error"])
    
    def test_blacklist_validator_blocked(self):
        """Test that blacklisted unit fails validation."""
        validator = UnitBlacklistValidator(blacklist=["spam", "test"])
        result = validator.validate("spam")
        self.assertFalse(result["valid"])
    
    def test_blacklist_validator_case_insensitive(self):
        """Test that blacklist is case-insensitive."""
        validator = UnitBlacklistValidator(blacklist=["spam", "test"])
        result = validator.validate("SPAM")
        self.assertFalse(result["valid"])
    
    def test_blacklist_validator_allowed(self):
        """Test that non-blacklisted unit passes validation."""
        validator = UnitBlacklistValidator(blacklist=["spam", "test"])
        result = validator.validate("kg")
        self.assertTrue(result["valid"])
    
    def test_blacklist_validator_none(self):
        """Test that None unit fails validation in blacklist validator."""
        validator = UnitBlacklistValidator(blacklist=["spam"])
        result = validator.validate(None)
        self.assertFalse(result["valid"])
    
    def test_composite_validator(self):
        """Test that composite validator runs all validators."""
        composite = CompositeValidator([
            UnitLengthValidator(min_length=0, max_length=50),
            UnitFormatValidator(),
        ])
        
        # Valid case
        result = composite.validate("kg")
        self.assertTrue(result["valid"])
        
        # Invalid case (too long)
        result = composite.validate("x" * 51)
        self.assertFalse(result["valid"])
    
    def test_composite_validator_add_validator(self):
        """Test adding validator to composite dynamically."""
        composite = CompositeValidator([
            UnitLengthValidator(min_length=0, max_length=50),
        ])
        
        # Add blacklist validator
        composite.add_validator(UnitBlacklistValidator(blacklist=["spam"]))
        
        # Test that blacklist is enforced
        result = composite.validate("spam")
        self.assertFalse(result["valid"])


class UnitUpdateRequestValidatorTests(TestCase):
    """Test cases for unit update request validation."""
    
    def setUp(self):
        self.validator = UnitUpdateRequestValidator()
    
    def test_validator_with_custom_unit_validator(self):
        """Test initializing with custom unit validator."""
        custom_validator = UnitLengthValidator(min_length=2, max_length=10)
        validator = UnitUpdateRequestValidator(unit_validator=custom_validator)
        
        # Test that custom validator is used (min_length=2)
        result = validator.validate_update_request(
            source="Gemilang Store",
            product_url="https://example.com/product",
            new_unit="a"  # Too short
        )
        self.assertFalse(result["valid"])
    
    def test_valid_request(self):
        """Test that valid request passes validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="https://example.com/product",
            new_unit="kg"
        )
        self.assertTrue(result["valid"])
    
    def test_missing_source(self):
        """Test that missing source fails validation."""
        result = self.validator.validate_update_request(
            source="",
            product_url="https://example.com/product",
            new_unit="kg"
        )
        self.assertFalse(result["valid"])
    
    def test_whitespace_only_source(self):
        """Test that whitespace-only source fails validation."""
        result = self.validator.validate_update_request(
            source="   ",  # Whitespace only
            product_url="https://example.com/product",
            new_unit="kg"
        )
        self.assertFalse(result["valid"])
        self.assertIn("cannot be empty", result["error"])
    
    def test_none_source(self):
        """Test that None source fails validation."""
        result = self.validator.validate_update_request(
            source=None,
            product_url="https://example.com/product",
            new_unit="kg"
        )
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing source", result["error"])
    
    def test_non_string_source(self):
        """Test that non-string source fails validation."""
        result = self.validator.validate_update_request(
            source=123,
            product_url="https://example.com/product",
            new_unit="kg"
        )
        self.assertFalse(result["valid"])
    
    def test_missing_url(self):
        """Test that missing URL fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="",
            new_unit="kg"
        )
        self.assertFalse(result["valid"])
    
    def test_whitespace_only_url(self):
        """Test that whitespace-only URL fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="   ",  # Whitespace only
            new_unit="kg"
        )
        self.assertFalse(result["valid"])
        self.assertIn("cannot be empty", result["error"])
    
    def test_none_url(self):
        """Test that None URL fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url=None,
            new_unit="kg"
        )
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing product_url", result["error"])
    
    def test_non_string_url(self):
        """Test that non-string URL fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url=456,
            new_unit="kg"
        )
        self.assertFalse(result["valid"])
    
    def test_any_url_format_accepted(self):
        """Test that any non-empty URL format is accepted (for compatibility with legacy data)."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="not-a-url",
            new_unit="kg"
        )
        self.assertTrue(result["valid"])
    
    def test_none_unit(self):
        """Test that None unit fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="https://example.com/product",
            new_unit=None
        )
        self.assertFalse(result["valid"])
    
    def test_non_string_unit(self):
        """Test that non-string unit fails validation."""
        result = self.validator.validate_update_request(
            source="Gemilang Store",
            product_url="https://example.com/product",
            new_unit=789
        )
        self.assertFalse(result["valid"])
        self.assertIn("must be a string", result["error"])
    
    def test_bulk_request_valid(self):
        """Test that valid bulk request passes validation."""
        updates = [
            {
                "source": "Gemilang Store",
                "product_url": "https://example.com/product1",
                "new_unit": "kg"
            },
            {
                "source": "Mitra10",
                "product_url": "https://example.com/product2",
                "new_unit": "m²"
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
                "new_unit": "kg"
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
                "new_unit": "kg"
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
                "new_unit": "kg"
            },
            {
                "source": "Gemilang Store",
                "product_url": "not-a-url",  # Accepted for compatibility with legacy data
                "new_unit": "m²"
            }
        ]
        result = self.validator.validate_bulk_request(updates)
        self.assertFalse(result["valid"])
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 1)  # Only empty source causes error now


class UnitUpdateServiceTests(TestCase):
    """Test cases for UnitUpdateService using mocks."""
    
    def setUp(self):
        """Set up test mocks."""
        # Create mock product
        self.mock_product = Mock()
        self.mock_product.name = "Test Product 1"
        self.mock_product.price = 10000
        self.mock_product.url = "https://gemilang.com/product1"
        self.mock_product.unit = "pcs"
        self.mock_product.category = "Alat Listrik"
        self.mock_product.location = "Jakarta"
        self.mock_product.updated_at = datetime.now()
        self.mock_product.save = Mock()
    
    def test_update_unit_success(self):
        """Test successful unit update with mocked model."""
        with patch.object(UnitUpdateService, 'VENDOR_MODEL_MAP') as mock_map:
            # Create a mock model class
            mock_model_class = Mock()
            mock_model_class.objects.get.return_value = self.mock_product
            mock_model_class.DoesNotExist = Exception
            
            # Setup the vendor map with the mock
            mock_map.__getitem__ = Mock(return_value=mock_model_class)
            mock_map.get = Mock(return_value=mock_model_class)
            
            service = UnitUpdateService()
            result = service.update_unit(
                source="Gemilang Store",
                product_url="https://gemilang.com/product1",
                new_unit="kg"
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["new_unit"], "kg")
            self.assertEqual(result["old_unit"], "pcs")
            self.assertEqual(result["product_name"], "Test Product 1")
            
            # Verify save was called
            self.mock_product.save.assert_called_once()
    
    def test_update_unit_validation_failure(self):
        """Test update with validation failure (empty source)."""
        service = UnitUpdateService()
        result = service.update_unit(
            source="",  # Invalid empty source
            product_url="https://gemilang.com/product1",
            new_unit="kg"
        )
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_update_unit_invalid_source(self):
        """Test update with invalid source."""
        service = UnitUpdateService()
        result = service.update_unit(
            source="Invalid Vendor",
            product_url="https://gemilang.com/product1",
            new_unit="kg"
        )
        
        self.assertFalse(result["success"])
        self.assertIn("Invalid vendor", result["error"])
    
    def test_update_unit_product_not_found(self):
        """Test update with non-existent product."""
        with patch.object(UnitUpdateService, 'VENDOR_MODEL_MAP') as mock_map:
            # Create a mock model class that raises DoesNotExist
            mock_model_class = Mock()
            mock_model_class.DoesNotExist = Exception
            mock_model_class.objects.get.side_effect = mock_model_class.DoesNotExist
            
            # Setup the vendor map
            mock_map.get = Mock(return_value=mock_model_class)
            
            service = UnitUpdateService()
            result = service.update_unit(
                source="Gemilang Store",
                product_url="https://gemilang.com/nonexistent",
                new_unit="kg"
            )
            
            self.assertFalse(result["success"])
            self.assertIn("not found", result["error"])
    
    def test_bulk_update_success(self):
        """Test successful bulk update with mocked models."""
        with patch.object(UnitUpdateService, 'VENDOR_MODEL_MAP') as mock_map:
            # Setup mocks
            mock_product1 = Mock()
            mock_product1.name = "Product 1"
            mock_product1.unit = "pcs"
            mock_product1.updated_at = datetime.now()
            mock_product1.save = Mock()
            
            mock_product2 = Mock()
            mock_product2.name = "Product 2"
            mock_product2.unit = "box"
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
            
            service = UnitUpdateService()
            updates = [
                {
                    "source": "Gemilang Store",
                    "product_url": "https://gemilang.com/product1",
                    "new_unit": "kg"
                },
                {
                    "source": "Mitra10",
                    "product_url": "https://mitra10.com/product2",
                    "new_unit": "m²"
                }
            ]
            
            result = service.bulk_update_units(updates)
            
            self.assertEqual(result["success_count"], 2)
            self.assertEqual(result["failure_count"], 0)
            
            # Verify save was called for both products
            mock_product1.save.assert_called_once()
            mock_product2.save.assert_called_once()
    
    def test_bulk_update_partial_failure(self):
        """Test bulk update with some failures."""
        with patch.object(UnitUpdateService, 'VENDOR_MODEL_MAP') as mock_map:
            # Setup mock for successful update
            mock_product = Mock()
            mock_product.name = "Product 1"
            mock_product.unit = "pcs"
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
            
            service = UnitUpdateService()
            updates = [
                {
                    "source": "Gemilang Store",
                    "product_url": "https://gemilang.com/product1",
                    "new_unit": "kg"
                },
                {
                    "source": "Invalid Vendor",
                    "product_url": "https://invalid.com/product",
                    "new_unit": "m²"
                }
            ]
            
            result = service.bulk_update_units(updates)
            
            self.assertEqual(result["success_count"], 1)
            self.assertEqual(result["failure_count"], 1)
    
    def test_bulk_update_validation_failure(self):
        """Test bulk update with validation failure."""
        service = UnitUpdateService()
        
        # Create updates with validation errors
        updates = [
            {
                "source": "",  # Invalid empty source
                "product_url": "https://gemilang.com/product1",
                "new_unit": "kg"
            },
            {
                "source": "Gemilang Store",
                "product_url": "not-a-url",  # Invalid URL format
                "new_unit": "m²"
            }
        ]
        
        result = service.bulk_update_units(updates)
        
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failure_count"], 2)
        self.assertIn("validation_errors", result)
    
    def test_get_available_vendors(self):
        """Test getting available vendors."""
        service = UnitUpdateService()
        vendors = service.get_available_vendors()
        
        self.assertIsInstance(vendors, list)
        self.assertIn("Gemilang Store", vendors)
        self.assertIn("Mitra10", vendors)
    
    def test_bulk_update_uses_update_unit_method(self):
        """Test that bulk_update_units properly handles errors from update_unit method.
        
        This test verifies that bulk_update_units correctly delegates to update_unit
        and properly handles failure cases by counting them appropriately.
        """
        service = UnitUpdateService()
        
        # Mock update_unit to return an error for one item and success for another
        with patch.object(service, 'update_unit') as mock_update:
            def update_side_effect(source, product_url, new_unit):
                if product_url == "https://gemilang.com/product1":
                    return {
                        "success": False,
                        "error": "Product not found"
                    }
                else:
                    return {
                        "success": True,
                        "message": "Unit updated successfully",
                        "product_name": "Product 2",
                        "old_unit": "box",
                        "new_unit": new_unit,
                        "vendor": source,
                        "updated_at": datetime.now().isoformat()
                    }
            
            mock_update.side_effect = update_side_effect
            
            updates = [
                {
                    "source": "Gemilang Store",
                    "product_url": "https://gemilang.com/product1",
                    "new_unit": "kg"
                },
                {
                    "source": "Mitra10",
                    "product_url": "https://mitra10.com/product2",
                    "new_unit": "m²"
                }
            ]
            
            result = service.bulk_update_units(updates)
            
            # Verify that update_unit was called for both items
            self.assertEqual(mock_update.call_count, 2)
            mock_update.assert_any_call(
                "Gemilang Store",
                "https://gemilang.com/product1",
                "kg"
            )
            mock_update.assert_any_call(
                "Mitra10",
                "https://mitra10.com/product2",
                "m²"
            )
            
            # Verify the result counts: 1 success, 1 failure
            self.assertEqual(result["success_count"], 1)
            self.assertEqual(result["failure_count"], 1)
            
            # Verify the updates list contains both results
            self.assertEqual(len(result["updates"]), 2)
            self.assertFalse(result["updates"][0]["success"])
            self.assertIn("error", result["updates"][0])
            self.assertTrue(result["updates"][1]["success"])


class UnitUpdateAPITests(TestCase):
    """Test cases for unit update API endpoints using mocks."""
    
    def setUp(self):
        """Set up request factory and mocks."""
        self.factory = RequestFactory()
    
    @patch('dashboard.views_db.UnitUpdateService')
    def test_update_unit_endpoint_success(self, mock_service_class):
        """Test successful unit update via API with mocked service."""
        # Setup mock service
        mock_service = Mock()
        mock_service.update_unit.return_value = {
            "success": True,
            "message": "Unit updated successfully",
            "product_name": "Test Product",
            "old_unit": "pcs",
            "new_unit": "kg",
            "vendor": "Gemilang Store",
            "updated_at": "2025-11-23T10:30:00.000Z"
        }
        mock_service_class.return_value = mock_service
        
        # Create request
        request = self.factory.post(
            '/dashboard/api/unit/update/',
            data=json.dumps({
                "source": "Gemilang Store",
                "product_url": "https://gemilang.com/api-test",
                "new_unit": "kg"
            }),
            content_type='application/json'
        )
        
        # Call the view
        response = views_db.update_product_unit(request)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["new_unit"], "kg")
        
        # Verify service was called correctly
        mock_service.update_unit.assert_called_once_with(
            "Gemilang Store",
            "https://gemilang.com/api-test",
            "kg"
        )
    
    @patch('dashboard.views_db.UnitUpdateService')
    def test_update_unit_endpoint_failure(self, mock_service_class):
        """Test unit update failure via API."""
        # Setup mock service to return failure
        mock_service = Mock()
        mock_service.update_unit.return_value = {
            "success": False,
            "error": "Product not found"
        }
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/unit/update/',
            data=json.dumps({
                "source": "Gemilang Store",
                "product_url": "https://gemilang.com/nonexistent",
                "new_unit": "kg"
            }),
            content_type='application/json'
        )
        
        response = views_db.update_product_unit(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("error", data)
    
    def test_update_unit_endpoint_invalid_json(self):
        """Test unit update with invalid JSON."""
        request = self.factory.post(
            '/dashboard/api/unit/update/',
            data="invalid json",
            content_type='application/json'
        )
        
        response = views_db.update_product_unit(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Invalid JSON", data["error"])
    
    @patch('dashboard.views_db.UnitUpdateService')
    def test_bulk_update_units_endpoint_success(self, mock_service_class):
        """Test successful bulk unit update via API."""
        # Setup mock service
        mock_service = Mock()
        mock_service.bulk_update_units.return_value = {
            "success_count": 2,
            "failure_count": 0,
            "updates": [
                {
                    "success": True,
                    "message": "Unit updated successfully",
                    "product_name": "Product 1",
                    "old_unit": "pcs",
                    "new_unit": "kg",
                    "vendor": "Gemilang Store",
                    "updated_at": "2025-11-23T10:30:00.000Z"
                },
                {
                    "success": True,
                    "message": "Unit updated successfully",
                    "product_name": "Product 2",
                    "old_unit": "box",
                    "new_unit": "m²",
                    "vendor": "Mitra10",
                    "updated_at": "2025-11-23T10:31:00.000Z"
                }
            ]
        }
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/unit/bulk-update/',
            data=json.dumps({
                "updates": [
                    {
                        "source": "Gemilang Store",
                        "product_url": "https://gemilang.com/product1",
                        "new_unit": "kg"
                    },
                    {
                        "source": "Mitra10",
                        "product_url": "https://mitra10.com/product2",
                        "new_unit": "m²"
                    }
                ]
            }),
            content_type='application/json'
        )
        
        response = views_db.bulk_update_units(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["success_count"], 2)
        self.assertEqual(data["failure_count"], 0)
    
    @patch('dashboard.views_db.UnitUpdateService')
    def test_bulk_update_units_endpoint_partial_failure(self, mock_service_class):
        """Test bulk unit update with partial failures."""
        # Setup mock service
        mock_service = Mock()
        mock_service.bulk_update_units.return_value = {
            "success_count": 1,
            "failure_count": 1,
            "updates": [
                {
                    "success": True,
                    "message": "Unit updated successfully"
                },
                {
                    "success": False,
                    "error": "Product not found"
                }
            ]
        }
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/unit/bulk-update/',
            data=json.dumps({
                "updates": [
                    {
                        "source": "Gemilang Store",
                        "product_url": "https://gemilang.com/product1",
                        "new_unit": "kg"
                    },
                    {
                        "source": "Invalid Vendor",
                        "product_url": "https://invalid.com/product",
                        "new_unit": "m²"
                    }
                ]
            }),
            content_type='application/json'
        )
        
        response = views_db.bulk_update_units(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["success_count"], 1)
        self.assertEqual(data["failure_count"], 1)
    
    def test_bulk_update_units_endpoint_invalid_updates_type(self):
        """Test bulk update with invalid updates type."""
        request = self.factory.post(
            '/dashboard/api/unit/bulk-update/',
            data=json.dumps({
                "updates": "not a list"
            }),
            content_type='application/json'
        )
        
        response = views_db.bulk_update_units(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("must be a list", data["error"])
    
    def test_bulk_update_units_endpoint_invalid_json(self):
        """Test bulk update with invalid JSON."""
        request = self.factory.post(
            '/dashboard/api/unit/bulk-update/',
            data="invalid json",
            content_type='application/json'
        )
        
        response = views_db.bulk_update_units(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Invalid JSON", data["error"])
    
    @patch('dashboard.views_db.UnitUpdateService')
    def test_get_available_vendors_unit_endpoint(self, mock_service_class):
        """Test get available vendors endpoint."""
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
        
        request = self.factory.get('/dashboard/api/unit/vendors/')
        
        response = views_db.get_available_vendors_unit(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertIn("vendors", data)
        self.assertEqual(len(data["vendors"]), 5)
        self.assertIn("Gemilang Store", data["vendors"])
    
    @patch('dashboard.views_db.UnitUpdateService')
    def test_update_unit_endpoint_server_error(self, mock_service_class):
        """Test update unit endpoint with server error."""
        # Setup mock service to raise an unexpected exception
        mock_service = Mock()
        mock_service.update_unit.side_effect = RuntimeError("Database connection failed")
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/unit/update/',
            data=json.dumps({
                "source": "Gemilang Store",
                "product_url": "https://gemilang.com/product1",
                "new_unit": "kg"
            }),
            content_type='application/json'
        )
        
        response = views_db.update_product_unit(request)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])
    
    @patch('dashboard.views_db.UnitUpdateService')
    def test_get_available_vendors_unit_endpoint_server_error(self, mock_service_class):
        """Test get available vendors endpoint with server error."""
        # Setup mock service to raise an unexpected exception
        mock_service = Mock()
        mock_service.get_available_vendors.side_effect = RuntimeError("Service unavailable")
        mock_service_class.return_value = mock_service
        
        request = self.factory.get('/dashboard/api/unit/vendors/')
        
        response = views_db.get_available_vendors_unit(request)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])
    
    @patch('dashboard.views_db.UnitUpdateService')
    def test_bulk_update_units_endpoint_server_error(self, mock_service_class):
        """Test bulk update units endpoint with server error."""
        # Setup mock service to raise an unexpected exception
        mock_service = Mock()
        mock_service.bulk_update_units.side_effect = RuntimeError("Bulk operation failed")
        mock_service_class.return_value = mock_service
        
        request = self.factory.post(
            '/dashboard/api/unit/bulk-update/',
            data=json.dumps({
                "updates": [
                    {
                        "source": "Gemilang Store",
                        "product_url": "https://gemilang.com/product1",
                        "new_unit": "kg"
                    }
                ]
            }),
            content_type='application/json'
        )
        
        response = views_db.bulk_update_units(request)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Server error", data["error"])
