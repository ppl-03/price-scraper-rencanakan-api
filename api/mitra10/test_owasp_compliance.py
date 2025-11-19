"""
OWASP A04:2021 Compliance Test Suite for Mitra10 Module
Tests Insecure Design Prevention

This test suite simulates real-world attack scenarios and verifies that 
security controls are properly implemented according to OWASP guidelines.
"""
import unittest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.http import JsonResponse

# Import security modules
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from .security import (
    SecurityDesignPatterns,
    enforce_resource_limits,
)
from .database_service import Mitra10DatabaseService


class TestA04InsecureDesign(TestCase):
    """
    Test suite for OWASP A04:2021 - Insecure Design
    
    Tests:
    1. Business logic validation
    2. Resource consumption limits
    3. Plausibility checks
    4. SSRF prevention
    5. Secure design patterns
    """
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_business_logic_price_validation(self):
        """Test that business logic validates prices"""
        print("\n[A04] Test: Business logic - Price validation")
        
        # Valid price
        data = {'price': 50000, 'name': 'Product', 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid, "Valid price should be accepted")
        print("✓ Valid price accepted: 50000")
        
        # Negative price (business rule violation)
        data = {'price': -1000, 'name': 'Product', 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid, "Negative price should be rejected")
        self.assertIn('positive', error_msg)
        print("✓ Negative price rejected")
        
        # Unreasonably high price (plausibility check)
        data = {'price': 2000000000, 'name': 'Product', 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid, "Unreasonably high price should be rejected")
        print("✓ Unreasonably high price rejected (plausibility check)")
    
    def test_business_logic_name_validation(self):
        """Test that business logic validates product names"""
        print("\n[A04] Test: Business logic - Name validation")
        
        # Valid name
        data = {'name': 'Semen Gresik 50kg', 'price': 65000, 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid, "Valid name should be accepted")
        print("✓ Valid name accepted")
        
        # Name too short
        data = {'name': 'A', 'price': 1000, 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertIn('too short', error_msg)
        print("✓ Too short name rejected")
        
        # Name too long
        data = {'name': 'A' * 501, 'price': 1000, 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertIn('too long', error_msg)
        print("✓ Too long name rejected")
    
    def test_ssrf_prevention(self):
        """Test that SSRF attacks are prevented"""
        print("\n[A04] Test: SSRF prevention")
        
        # Valid external URL
        data = {'name': 'Product', 'price': 1000, 'url': 'https://www.mitra10.co.id/product/123'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid, "Valid external URL should be accepted")
        print("✓ Valid external URL accepted")
        
        # SSRF attempts - internal hosts
        ssrf_attempts = [
            'https://localhost/admin',
            'https://127.0.0.1/secret',
            'https://0.0.0.0/internal'
        ]
        
        for ssrf_url in ssrf_attempts:
            data = {'name': 'Product', 'price': 1000, 'url': ssrf_url}
            is_valid, _ = SecurityDesignPatterns.validate_business_logic(data)
            self.assertFalse(is_valid, f"SSRF should be prevented: {ssrf_url}")
            print(f"✓ SSRF prevented: {ssrf_url}")
        
        # HTTP URLs should be rejected (HTTPS required)
        data = {'name': 'Product', 'price': 1000, 'url': 'http://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid, "HTTP URL should be rejected")
        self.assertIn('HTTPS', error_msg)
        print("✓ HTTP URL rejected (HTTPS required)")
    
    def test_resource_limit_page_size(self):
        """Test that resource limits are enforced"""
        print("\n[A04] Test: Resource limit - Page size")
        
        # Reasonable limit
        request = self.factory.get('/api/test', {'limit': '50'})
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid, "Reasonable limit should be accepted")
        print("✓ Reasonable limit accepted: 50")
        
        # Limit at maximum
        request = self.factory.get('/api/test', {'limit': '100'})
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid, "Limit at maximum should be accepted")
        print("✓ Maximum limit accepted: 100")
        
        # Excessive limit
        request = self.factory.get('/api/test', {'limit': '10000'})
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid, "Excessive limit should be rejected")
        self.assertIn('exceeds maximum', error_msg)
        print("✓ Excessive limit rejected: 10000")
        
        # Invalid limit (non-numeric)
        request = self.factory.get('/api/test', {'limit': 'abc'})
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid, "Invalid limit should be rejected")
        self.assertIn('Invalid limit', error_msg)
        print("✓ Invalid limit rejected: 'abc'")
    
    def test_resource_limit_query_complexity(self):
        """Test that query complexity is limited"""
        print("\n[A04] Test: Resource limit - Query complexity")
        
        # Normal query (10 parameters)
        params = {f'param{i}': f'value{i}' for i in range(10)}
        request = self.factory.get('/api/test', params)
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid, "Normal query should be accepted")
        print("✓ Normal query accepted: 10 parameters")
        
        # Query at maximum (20 parameters)
        params = {f'param{i}': f'value{i}' for i in range(20)}
        request = self.factory.get('/api/test', params)
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid, "Query at maximum should be accepted")
        print("✓ Maximum query accepted: 20 parameters")
        
        # Excessive parameters (DoS attempt - 25 parameters)
        params = {f'param{i}': f'value{i}' for i in range(25)}
        request = self.factory.get('/api/test', params)
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid, "Excessive parameters should be rejected")
        self.assertIn('Too many', error_msg)
        print("✓ Excessive parameters rejected: 25 parameters")
    
    def test_database_validation_comprehensive(self):
        """Test comprehensive database input validation"""
        print("\n[A04] Test: Comprehensive database validation")
        
        db_service = Mitra10DatabaseService()
        
        # Valid data
        valid_data = [{
            'name': 'Semen Gresik 50kg',
            'price': 65000,
            'url': 'https://www.mitra10.co.id/product/123',
            'unit': 'sak'
        }]
        is_valid, error_msg = db_service._validate_data(valid_data)
        self.assertTrue(is_valid, "Valid data should be accepted")
        print("✓ Valid data accepted")
        
        # Missing required fields
        invalid_data = [{'name': 'Product'}]
        is_valid, error_msg = db_service._validate_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn('missing required fields', error_msg)
        print("✓ Missing fields rejected")
        
        # Invalid price type
        invalid_data = [{
            'name': 'Product',
            'price': 'expensive',
            'url': 'https://test.com',
            'unit': 'pcs'
        }]
        is_valid, error_msg = db_service._validate_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn('must be a number', error_msg)
        print("✓ Invalid price type rejected")
        
        # Negative price
        invalid_data = [{
            'name': 'Product',
            'price': -500,
            'url': 'https://test.com',
            'unit': 'pcs'
        }]
        is_valid, error_msg = db_service._validate_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn('positive', error_msg)
        print("✓ Negative price rejected")
        
        # Invalid URL format (HTTP instead of HTTPS)
        invalid_data = [{
            'name': 'Product',
            'price': 1000,
            'url': 'http://test.com',
            'unit': 'pcs'
        }]
        is_valid, error_msg = db_service._validate_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn('HTTPS protocol', error_msg)
        print("✓ HTTP URL rejected (HTTPS required)")
        
        # SSRF attempt in URL
        invalid_data = [{
            'name': 'Product',
            'price': 1000,
            'url': 'https://localhost/admin',
            'unit': 'pcs'
        }]
        is_valid, error_msg = db_service._validate_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn('Invalid URL', error_msg)
        print("✓ SSRF attempt in URL rejected")
    
    def test_decorator_enforce_resource_limits(self):
        """Test that the enforce_resource_limits decorator works correctly"""
        print("\n[A04] Test: Decorator - enforce_resource_limits")
        
        # Create a mock view function
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Test with valid request
        request = self.factory.get('/api/test', {'limit': '50'})
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        print("✓ Decorator allows valid request")
        
        # Test with excessive limit
        request = self.factory.get('/api/test', {'limit': '10000'})
        response = test_view(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('exceeds maximum', data['error'])
        print("✓ Decorator blocks excessive limit")
        
        # Test with too many parameters
        params = {f'param{i}': f'value{i}' for i in range(25)}
        request = self.factory.get('/api/test', params)
        response = test_view(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Too many', data['error'])
        print("✓ Decorator blocks excessive parameters")
    
    def test_plausibility_checks(self):
        """Test that plausibility checks are properly implemented"""
        print("\n[A04] Test: Plausibility checks")
        
        # Test price plausibility
        test_cases = [
            (0, True, "Zero price (free item)"),
            (100, True, "Very low price"),
            (50000, True, "Normal price"),
            (999999, True, "High price"),
            (1000000, True, "Maximum reasonable price"),
            (1000000001, False, "Exceeds plausibility limit"),
            (2000000000, False, "Extremely high price"),
        ]
        
        for price, should_pass, description in test_cases:
            data = {'name': 'Test Product', 'price': price, 'url': 'https://example.com'}
            is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
            
            if should_pass:
                self.assertTrue(is_valid, f"{description} should be accepted")
                print(f"✓ {description} accepted: {price}")
            else:
                self.assertFalse(is_valid, f"{description} should be rejected")
                print(f"✓ {description} rejected: {price}")


class TestIntegratedSecurityScenarios(TestCase):
    """
    Test integrated security scenarios combining multiple controls.
    """
    
    def setUp(self):
        self.factory = RequestFactory()
        self.db_service = Mitra10DatabaseService()
    
    def test_end_to_end_data_flow_with_validation(self):
        """Test complete data flow from input to database with all validations"""
        print("\n[A04] Test: End-to-end data flow with validation")
        
        # Simulate valid product data
        valid_products = [
            {
                'name': 'Semen Gresik 50kg',
                'price': 65000,
                'url': 'https://www.mitra10.co.id/semen-gresik',
                'unit': 'sak'
            },
            {
                'name': 'Cat Tembok Avian 5L',
                'price': 125000,
                'url': 'https://www.mitra10.co.id/cat-avian',
                'unit': 'kaleng'
            }
        ]
        
        # Validate data
        is_valid, error_msg = self.db_service._validate_data(valid_products)
        self.assertTrue(is_valid, "Valid products should pass validation")
        self.assertEqual(error_msg, "")
        print("✓ Valid products passed all validations")
        
        # Test with attack payloads
        attack_products = [
            {
                'name': 'A',  # Too short
                'price': 50000,
                'url': 'https://www.mitra10.co.id/product',
                'unit': 'pcs'
            }
        ]
        
        is_valid, error_msg = self.db_service._validate_data(attack_products)
        self.assertFalse(is_valid, "Attack payload should be rejected")
        print("✓ Attack payload rejected: too short name")
        
        # Test with SSRF payload
        ssrf_products = [
            {
                'name': 'Test Product',
                'price': 50000,
                'url': 'https://127.0.0.1/internal',  # SSRF attempt
                'unit': 'pcs'
            }
        ]
        
        is_valid, error_msg = self.db_service._validate_data(ssrf_products)
        self.assertFalse(is_valid, "SSRF payload should be rejected")
        print("✓ SSRF payload rejected")


def run_tests():
    """Run all A04:2021 compliance tests"""
    print("=" * 80)
    print("OWASP A04:2021 - Insecure Design Prevention Test Suite")
    print("Mitra10 Module")
    print("=" * 80)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestA04InsecureDesign))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegratedSecurityScenarios))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ All A04:2021 compliance tests passed!")
    else:
        print("\n✗ Some tests failed. Please review the output above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
