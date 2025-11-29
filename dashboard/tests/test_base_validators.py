"""
Tests for base validators module.

This module tests the shared validation logic used by both category and unit
update validators.
"""

from django.test import TestCase
from dashboard.base_validators import BaseUpdateRequestValidator


class BaseUpdateRequestValidatorTests(TestCase):
    """Test suite for BaseUpdateRequestValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = BaseUpdateRequestValidator()
    
    # ========== Source Validation Tests ==========
    
    def test_validate_source_valid(self):
        """Test that valid source passes validation."""
        result = self.validator.validate_source("Gemilang Store")
        self.assertTrue(result["valid"])
    
    def test_validate_source_none(self):
        """Test that None source fails validation."""
        result = self.validator.validate_source(None)
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing source", result["error"])
    
    def test_validate_source_empty_string(self):
        """Test that empty string source fails validation."""
        result = self.validator.validate_source("")
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing source", result["error"])
    
    def test_validate_source_whitespace_only(self):
        """Test that whitespace-only source fails validation."""
        result = self.validator.validate_source("   ")
        self.assertFalse(result["valid"])
        self.assertIn("cannot be empty", result["error"])
    
    def test_validate_source_not_string(self):
        """Test that non-string source fails validation."""
        result = self.validator.validate_source(123)
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing source", result["error"])
    
    # ========== Product URL Validation Tests ==========
    
    def test_validate_product_url_valid(self):
        """Test that valid HTTPS URL passes validation."""
        result = self.validator.validate_product_url("https://example.com/product")
        self.assertTrue(result["valid"])
    
    def test_validate_product_url_none(self):
        """Test that None URL fails validation."""
        result = self.validator.validate_product_url(None)
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing product_url", result["error"])
    
    def test_validate_product_url_empty(self):
        """Test that empty URL fails validation."""
        result = self.validator.validate_product_url("")
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing product_url", result["error"])
    
    def test_validate_product_url_whitespace(self):
        """Test that whitespace-only URL fails validation."""
        result = self.validator.validate_product_url("   ")
        self.assertFalse(result["valid"])
        self.assertIn("cannot be empty", result["error"])
    
    def test_validate_product_url_not_string(self):
        """Test that non-string URL fails validation."""
        result = self.validator.validate_product_url(123)
        self.assertFalse(result["valid"])
        self.assertIn("Invalid or missing product_url", result["error"])
    
    # ========== Bulk Request Structure Tests ==========
    
    def test_validate_bulk_request_structure_valid(self):
        """Test that valid bulk request structure passes validation."""
        updates = [{"source": "Gemilang Store"}]
        result = self.validator.validate_bulk_request_structure(updates)
        self.assertTrue(result["valid"])
    
    def test_validate_bulk_request_structure_not_list(self):
        """Test that non-list bulk request fails validation."""
        result = self.validator.validate_bulk_request_structure("not a list")
        self.assertFalse(result["valid"])
        self.assertIn("must be a list", result["error"])
    
    def test_validate_bulk_request_structure_empty(self):
        """Test that empty bulk request fails validation."""
        result = self.validator.validate_bulk_request_structure([])
        self.assertFalse(result["valid"])
        self.assertIn("cannot be empty", result["error"])
    
    def test_validate_bulk_request_structure_too_large(self):
        """Test that oversized bulk request fails validation."""
        updates = [{"source": "Test"} for _ in range(101)]
        result = self.validator.validate_bulk_request_structure(updates)
        self.assertFalse(result["valid"])
        self.assertIn("limited to 100 items", result["error"])
    
    def test_validate_bulk_request_structure_exactly_100(self):
        """Test that exactly 100 items is allowed."""
        updates = [{"source": "Test"} for _ in range(100)]
        result = self.validator.validate_bulk_request_structure(updates)
        self.assertTrue(result["valid"])
    
    # ========== Update Item Structure Tests ==========
    
    def test_validate_update_item_structure_valid(self):
        """Test that valid update item structure passes validation."""
        update = {"source": "Gemilang Store"}
        result = self.validator.validate_update_item_structure(update, 0)
        self.assertTrue(result["valid"])
    
    def test_validate_update_item_structure_not_dict(self):
        """Test that non-dict update item fails validation."""
        result = self.validator.validate_update_item_structure("not a dict", 5)
        self.assertFalse(result["valid"])
        self.assertEqual(result["index"], 5)
        self.assertIn("must be a dictionary", result["error"])
    
    def test_validate_update_item_structure_list(self):
        """Test that list update item fails validation."""
        result = self.validator.validate_update_item_structure([1, 2, 3], 10)
        self.assertFalse(result["valid"])
        self.assertEqual(result["index"], 10)
        self.assertIn("must be a dictionary", result["error"])
