"""
Tests for DepoBangunan Security Module (Insecure Design Prevention)
Tests OWASP A04:2021 - Insecure Design Prevention implementation
"""
from django.test import TestCase, RequestFactory
from django.http import QueryDict
from api.depobangunan.security import SecurityDesignPatterns
import logging

# Suppress logger during tests
logging.disable(logging.CRITICAL)


class SecurityDesignPatternsValidatePriceTests(TestCase):
    """Test suite for price field validation"""
    
    def test_valid_price_integer(self):
        """Test that valid integer prices are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(100)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_valid_price_float(self):
        """Test that valid float prices are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(99.99)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_valid_price_zero(self):
        """Test that zero price is accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(0)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_negative_price_rejected(self):
        """Test that negative prices are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(-50)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")
    
    def test_excessive_price_rejected(self):
        """Test that excessively high prices are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(2000000000)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price value exceeds reasonable limit")
    
    def test_max_reasonable_price_accepted(self):
        """Test that maximum reasonable price is accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(1000000000)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_string_price_rejected(self):
        """Test that string prices are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field("100")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")
    
    def test_none_price_rejected(self):
        """Test that None price is rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(None)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")


class SecurityDesignPatternsValidateNameTests(TestCase):
    """Test suite for name field validation"""
    
    def test_valid_name(self):
        """Test that valid product names are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field("Cement Bag 50kg")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_name_too_short(self):
        """Test that names shorter than 2 characters are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field("A")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Product name too short")
    
    def test_name_two_chars_accepted(self):
        """Test that 2 character names are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field("AB")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_name_too_long(self):
        """Test that names longer than 500 characters are rejected"""
        long_name = "A" * 501
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field(long_name)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Product name too long")
    
    def test_name_max_length_accepted(self):
        """Test that names exactly 500 characters are accepted"""
        max_name = "A" * 500
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field(max_name)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_empty_name_rejected(self):
        """Test that empty names are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field("")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Product name too short")


class SecurityDesignPatternsValidateURLTests(TestCase):
    """Test suite for URL field validation (SSRF protection)"""
    
    def test_valid_https_url(self):
        """Test that valid HTTPS URLs are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://example.com/product")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_http_url_rejected(self):
        """Test that HTTP URLs are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field(
            "http://example.com/product"  # NOSONAR: intentionally insecure for rejection test
        )
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "URL must use HTTPS protocol for security")

    
    def test_localhost_rejected(self):
        """Test that localhost URLs are rejected (SSRF protection)"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://localhost/admin")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")
    
    def test_127_0_0_1_rejected(self):
        """Test that 127.0.0.1 URLs are rejected (SSRF protection)"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://127.0.0.1/admin")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")
    
    def test_0_0_0_0_rejected(self):
        """Test that 0.0.0.0 URLs are rejected (SSRF protection)"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://0.0.0.0/admin")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")
    
    def test_url_with_localhost_substring(self):
        """Test that URLs containing 'localhost' substring are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://mylocalhostserver.com")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")


class SecurityDesignPatternsValidateBusinessLogicTests(TestCase):
    """Test suite for overall business logic validation"""
    
    def test_valid_product_data(self):
        """Test that valid product data passes all validations"""
        data = {
            'name': 'Cement Bag 50kg',
            'price': 75000,
            'url': 'https://depobangunan.com/product/cement'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_invalid_price_in_data(self):
        """Test that invalid price causes validation to fail"""
        data = {
            'name': 'Cement Bag 50kg',
            'price': -100,
            'url': 'https://depobangunan.com/product/cement'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")
    
    def test_invalid_name_in_data(self):
        """Test that invalid name causes validation to fail"""
        data = {
            'name': 'A',
            'price': 75000,
            'url': 'https://depobangunan.com/product/cement'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Product name too short")
    
    def test_invalid_url_in_data(self):
        """Test that invalid URL causes validation to fail"""
        data = {
            'name': 'Cement Bag 50kg',
            'price': 75000,
            'url': 'http://depobangunan.com/product/cement',  # NOSONAR: test ensures HTTP is rejected
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "URL must use HTTPS protocol for security")

    
    def test_ssrf_attempt_detected(self):
        """Test that SSRF attempts are detected and blocked"""
        data = {
            'name': 'Cement Bag 50kg',
            'price': 75000,
            'url': 'https://localhost/admin/delete'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")
    
    def test_partial_data_validation(self):
        """Test that validation works with partial data"""
        data = {'price': 50000}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_empty_data_valid(self):
        """Test that empty data is considered valid"""
        data = {}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_multiple_invalid_fields_returns_first_error(self):
        """Test that when multiple fields are invalid, the first error is returned"""
        data = {
            'price': -100,
            'name': 'A',
            'url': 'http://example.com',  # NOSONAR: intentionally insecure for validation test
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")



class SecurityDesignPatternsEnforceResourceLimitsTests(TestCase):
    """Test suite for resource limit enforcement"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_valid_request_no_limits(self):
        """Test that requests without limit parameters are accepted"""
        request = self.factory.get('/api/products')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_valid_limit_parameter(self):
        """Test that valid limit parameters are accepted"""
        request = self.factory.get('/api/products?limit=50')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_limit_at_max_accepted(self):
        """Test that limit exactly at max is accepted"""
        request = self.factory.get('/api/products?limit=100')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request, max_page_size=100)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_limit_exceeds_max_rejected(self):
        """Test that limit exceeding max is rejected"""
        request = self.factory.get('/api/products?limit=150')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request, max_page_size=100)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Limit exceeds maximum of 100")
    
    def test_invalid_limit_format_rejected(self):
        """Test that non-integer limit is rejected"""
        request = self.factory.get('/api/products?limit=abc')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid limit parameter")
    
    def test_excessive_query_parameters_rejected(self):
        """Test that excessive query parameters are rejected"""
        # Create request with 21 parameters
        params = '&'.join([f'param{i}=value{i}' for i in range(21)])
        request = self.factory.get(f'/api/products?{params}')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Too many query parameters")
    
    def test_exactly_20_parameters_accepted(self):
        """Test that exactly 20 query parameters are accepted"""
        params = '&'.join([f'param{i}=value{i}' for i in range(20)])
        request = self.factory.get(f'/api/products?{params}')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_custom_max_page_size(self):
        """Test that custom max_page_size is respected"""
        request = self.factory.get('/api/products?limit=60')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request, max_page_size=50)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Limit exceeds maximum of 50")
    
    def test_zero_limit_accepted(self):
        """Test that zero limit is accepted (could mean no limit)"""
        request = self.factory.get('/api/products?limit=0')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_negative_limit_accepted(self):
        """Test that negative limit is accepted (handled by integer parsing)"""
        request = self.factory.get('/api/products?limit=-10')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")


class SecurityDesignPatternsIntegrationTests(TestCase):
    """Integration tests for security design patterns"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_complete_secure_request_flow(self):
        """Test a complete secure request flow"""
        # Create a valid request
        request = self.factory.get('/api/products?keyword=cement&limit=50')
        
        # Check resource limits
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        
        # Validate product data
        product_data = {
            'name': 'Premium Cement 50kg',
            'price': 75000,
            'url': 'https://depobangunan.com/product/cement-premium'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(product_data)
        self.assertTrue(is_valid)
    
    def test_attack_detection_flow(self):
        """Test that various attack attempts are detected"""
        # Test SSRF attempt
        ssrf_data = {
            'name': 'Product',
            'price': 100,
            'url': 'https://127.0.0.1/admin'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(ssrf_data)
        self.assertFalse(is_valid)
        
        # Test resource exhaustion attempt
        params = '&'.join([f'p{i}=v{i}' for i in range(25)])
        request = self.factory.get(f'/api/products?{params}')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid)
        
        # Test business logic violation
        invalid_data = {'price': 5000000000}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(invalid_data)
        self.assertFalse(is_valid)


# Re-enable logging after tests
logging.disable(logging.NOTSET)
