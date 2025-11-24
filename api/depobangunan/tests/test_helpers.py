"""
Common test helpers and base classes for Depobangunan tests.
Reduces code duplication across test files.
"""
from unittest.mock import Mock, patch
from django.test import RequestFactory
from api.interfaces import ScrapingResult, Product


class BaseDepoBangunanTestCase:
    """Base test case with common setup and helper methods."""
    
    def setUp(self):
        """Common setup for all tests."""
        self.factory = RequestFactory()
    
    def create_mock_request(self, path='/', method='GET', token=None, ip='127.0.0.1'):
        """Create a mock request with common attributes."""
        if method == 'GET':
            request = self.factory.get(path)
        elif method == 'POST':
            request = self.factory.post(path)
        else:
            request = self.factory.generic(method, path)
        
        if token:
            request.META['HTTP_X_API_TOKEN'] = token
        request.META['REMOTE_ADDR'] = ip
        
        return request
    
    def create_mock_scraper(self, products=None, success=True, error_message=""):
        """Create a mock scraper with configurable return values."""
        if products is None:
            products = [
                Product(name="Product 1", price=10000, url="/p1", unit="pcs"),
                Product(name="Product 2", price=20000, url="/p2", unit="kg")
            ]
        
        mock_scraper = Mock()
        mock_scraper.scrape_products.return_value = ScrapingResult(
            success=success,
            products=products,
            error_message=error_message,
            url="test.com"
        )
        return mock_scraper


class ProfilerTestHelpers:
    """Helper methods for profiler tests."""
    
    @staticmethod
    def assert_profiler_result_structure(test_case, result):
        """Assert that profiler result has expected structure."""
        test_case.assertIsInstance(result, dict)
        test_case.assertIn('component', result)
        test_case.assertIn('iterations', result)
    
    @staticmethod
    def create_mock_profiler_components():
        """Create mock profiler components."""
        return {
            'html_parser': Mock(),
            'price_cleaner': Mock(),
            'url_builder': Mock(),
            'scraper': Mock()
        }
    
    @staticmethod
    def run_profiler_with_mocks(profiler, mock_create_scraper, iterations=1):
        """Run profiler with mock scraper."""
        mock_scraper = Mock()
        mock_scraper.scrape_products.return_value = []
        mock_create_scraper.return_value = mock_scraper
        
        with patch.object(profiler, '_profile_component') as mock_profile:
            mock_profile.return_value = {
                'component': 'test',
                'iterations': iterations,
                'total_time': 0.1
            }
            return mock_profile


class SecurityTestHelpers:
    """Helper methods for security/OWASP tests."""
    
    @staticmethod
    def assert_validation_failed(test_case, is_valid, error_msg, expected_error_substring=None):
        """Assert that validation failed with expected error."""
        test_case.assertFalse(is_valid, "Validation should have failed")
        test_case.assertIsNotNone(error_msg)
        if expected_error_substring:
            test_case.assertIn(expected_error_substring, error_msg)
    
    @staticmethod
    def assert_validation_succeeded(test_case, is_valid, error_msg):
        """Assert that validation succeeded."""
        test_case.assertTrue(is_valid, "Validation should have succeeded")
        test_case.assertEqual(error_msg, '')
    
    @staticmethod
    def create_test_token_info(permissions=None, allowed_ips=None):
        """Create test token info dictionary."""
        if permissions is None:
            permissions = ['read', 'write']
        if allowed_ips is None:
            allowed_ips = []
        
        return {
            'name': 'Test Token',
            'permissions': permissions,
            'allowed_ips': allowed_ips,
            'rate_limit': {'requests': 100, 'window': 60}
        }
    
    @staticmethod
    def run_rate_limit_test(rate_limiter, client_id, max_requests, expect_block=True):
        """Helper to run rate limit tests."""
        results = []
        for i in range(max_requests + 1):
            is_allowed, error = rate_limiter.check_rate_limit(
                client_id, max_requests=max_requests, window_seconds=60
            )
            results.append((is_allowed, error))
        
        return results
