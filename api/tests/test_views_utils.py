"""
Tests for shared API view utilities.
"""
import json
from django.test import TestCase, RequestFactory
from unittest.mock import Mock
from api.views_utils import validate_scraping_request, format_scraping_response, handle_scraping_exception
from api.interfaces import ScrapingResult, Product


class TestViewsUtils(TestCase):
    """Test cases for shared view utilities."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_validate_scraping_request_missing_keyword(self):
        """Test validation with missing keyword."""
        request = self.factory.get('/test/')
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        
        self.assertIsNone(keyword)
        self.assertIsNone(sort_by_price)
        self.assertIsNone(page)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, 400)
        
    def test_validate_scraping_request_empty_keyword(self):
        """Test validation with empty keyword."""
        request = self.factory.get('/test/', {'keyword': ''})
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        
        self.assertIsNone(keyword)
        self.assertIsNone(sort_by_price)
        self.assertIsNone(page)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, 400)
    
    def test_validate_scraping_request_whitespace_keyword(self):
        """Test validation with whitespace-only keyword."""
        request = self.factory.get('/test/', {'keyword': '   '})
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        
        self.assertIsNone(keyword)
        self.assertIsNone(sort_by_price)
        self.assertIsNone(page)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, 400)
    
    def test_validate_scraping_request_valid_keyword_default_params(self):
        """Test validation with valid keyword and default parameters."""
        request = self.factory.get('/test/', {'keyword': 'test'})
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        
        self.assertEqual(keyword, 'test')
        self.assertTrue(sort_by_price)
        self.assertEqual(page, 0)
        self.assertIsNone(error_response)
    
    def test_validate_scraping_request_with_all_params(self):
        """Test validation with all parameters provided."""
        request = self.factory.get('/test/', {
            'keyword': 'test product',
            'sort_by_price': 'false',
            'page': '2'
        })
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        
        self.assertEqual(keyword, 'test product')
        self.assertFalse(sort_by_price)
        self.assertEqual(page, 2)
        self.assertIsNone(error_response)
    
    def test_validate_scraping_request_keyword_trimming(self):
        """Test that keyword gets trimmed properly."""
        request = self.factory.get('/test/', {'keyword': '  test keyword  '})
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        
        self.assertEqual(keyword, 'test keyword')
        self.assertIsNone(error_response)
    
    def test_validate_scraping_request_sort_by_price_variations(self):
        """Test various sort_by_price parameter values."""
        test_cases = [
            ('true', True),
            ('1', True),
            ('yes', True),
            ('True', True),
            ('false', False),
            ('0', False),
            ('no', False),
            ('False', False),
            ('invalid', False),
            ('', False)
        ]
        
        for sort_value, expected in test_cases:
            with self.subTest(sort_value=sort_value):
                request = self.factory.get('/test/', {
                    'keyword': 'test',
                    'sort_by_price': sort_value
                })
                keyword, sort_by_price, page, error_response = validate_scraping_request(request)
                
                self.assertEqual(sort_by_price, expected)
                self.assertIsNone(error_response)
    
    def test_validate_scraping_request_invalid_page(self):
        """Test validation with invalid page parameter."""
        request = self.factory.get('/test/', {
            'keyword': 'test',
            'page': 'invalid'
        })
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        
        self.assertIsNone(keyword)
        self.assertIsNone(sort_by_price)
        self.assertIsNone(page)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, 400)
    
    def test_format_scraping_response_success(self):
        """Test formatting successful scraping response."""
        products = [
            Product(name="Product 1", price=10000, url="/product1"),
            Product(name="Product 2", price=20000, url="/product2")
        ]
        result = ScrapingResult(
            products=products,
            success=True,
            url="https://example.com/search"
        )
        
        response_data = format_scraping_response(result)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 2)
        self.assertEqual(response_data['products'][0]['name'], "Product 1")
        self.assertEqual(response_data['products'][0]['price'], 10000)
        self.assertEqual(response_data['products'][0]['url'], "/product1")
        self.assertEqual(response_data['url'], "https://example.com/search")
        self.assertIsNone(response_data['error_message'])
    
    def test_format_scraping_response_failure(self):
        """Test formatting failed scraping response."""
        result = ScrapingResult(
            products=[],
            success=False,
            error_message="Network error occurred"
        )
        
        response_data = format_scraping_response(result)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['products'], [])
        self.assertEqual(response_data['error_message'], "Network error occurred")
    
    def test_format_scraping_response_empty_products(self):
        """Test formatting response with no products."""
        result = ScrapingResult(
            products=[],
            success=True,
            url="https://example.com/search"
        )
        
        response_data = format_scraping_response(result)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['products'], [])
        self.assertEqual(response_data['url'], "https://example.com/search")
    
    def test_handle_scraping_exception(self):
        """Test exception handling utility."""
        exception = Exception("Test error")
        
        response = handle_scraping_exception(exception, "Test Scraper")
        
        self.assertEqual(response.status_code, 500)
        content = json.loads(response.content)
        self.assertEqual(content['error'], 'Internal server error occurred')
    
    def test_handle_scraping_exception_default_scraper_name(self):
        """Test exception handling with default scraper name."""
        exception = Exception("Test error")
        
        response = handle_scraping_exception(exception)
        
        self.assertEqual(response.status_code, 500)
        content = json.loads(response.content)
        self.assertEqual(content['error'], 'Internal server error occurred')