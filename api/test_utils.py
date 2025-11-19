"""
Shared test utilities for API testing.
"""
import json
from django.test import TestCase, Client
from unittest.mock import patch, Mock
from api.interfaces import ScrapingResult, Product


class BaseScraperAPITestCase(TestCase):
    """
    Base test case for scraper API endpoints.
    Provides common test methods that can be used by all scraper API tests.
    """
    
    # These should be overridden in subclasses
    endpoint_url = None
    patch_path = None
    scraper_name = None
    api_token = 'dev-token-12345'  # Default API token for testing
    
    @classmethod
    def __subclasshook__(cls, candidate):
        return NotImplemented
    
    def setUp(self):
        self.client = Client()
        if not self.endpoint_url or not self.patch_path or not self.scraper_name:
            self.skipTest("Base test case should not be run directly")
    
    def get(self, url, data=None, **extra):
        """Helper method to make GET requests with API token."""
        extra['HTTP_X_API_TOKEN'] = self.api_token
        return self.client.get(url, data, **extra)
    
    def test_scrape_endpoint_exists(self):
        """Test that the scrape endpoint exists."""
        response = self.get(self.endpoint_url)
        self.assertNotEqual(response.status_code, 404)
        
    def test_scrape_missing_keyword_returns_400(self):
        """Test that missing keyword parameter returns 400."""
        response = self.get(self.endpoint_url)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Keyword parameter is required')

    def test_scrape_success(self):
        """Test successful scraping with mocked data."""
        with patch(self.patch_path) as mock_create_scraper:
            mock_scraper = Mock()
            mock_products = [
                Product(name="Test Product 1", price=10000, url="/product1"),
                Product(name="Test Product 2", price=20000, url="/product2")
            ]
            mock_result = ScrapingResult(
                products=mock_products,
                success=True,
                url="https://example.com/search?keyword=test"
            )
            mock_scraper.scrape_products.return_value = mock_result
            mock_create_scraper.return_value = mock_scraper
            
            response = self.get(self.endpoint_url, {'keyword': 'test'})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            self.assertTrue(data['success'])
            self.assertEqual(len(data['products']), 2)
            self.assertEqual(data['products'][0]['name'], "Test Product 1")
            self.assertEqual(data['products'][0]['price'], 10000)
            self.assertEqual(data['products'][0]['url'], "/product1")
            self.assertEqual(data['url'], "https://example.com/search?keyword=test")
            self.assertIsNone(data['error_message'])
            
            mock_scraper.scrape_products.assert_called_once_with(
                keyword='test',
                sort_by_price=True,
                page=0
            )

    def test_scrape_with_optional_parameters(self):
        """Test scraping with optional parameters."""
        with patch(self.patch_path) as mock_create_scraper:
            mock_scraper = Mock()
            mock_result = ScrapingResult(
                products=[],
                success=True,
                url="https://example.com/search"
            )
            mock_scraper.scrape_products.return_value = mock_result
            mock_create_scraper.return_value = mock_scraper
            
            response = self.get(self.endpoint_url, {
                'keyword': 'test',
                'sort_by_price': 'false',
                'page': '2'
            })
            
            self.assertEqual(response.status_code, 200)
            
            mock_scraper.scrape_products.assert_called_once_with(
                keyword='test',
                sort_by_price=False,
                page=2
            )

    def test_scrape_failure(self):
        """Test scraping failure scenario."""
        with patch(self.patch_path) as mock_create_scraper:
            mock_scraper = Mock()
            mock_result = ScrapingResult(
                products=[],
                success=False,
                error_message="Connection timeout occurred"
            )
            mock_scraper.scrape_products.return_value = mock_result
            mock_create_scraper.return_value = mock_scraper
            
            response = self.get(self.endpoint_url, {'keyword': 'test'})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            self.assertFalse(data['success'])
            self.assertEqual(data['error_message'], "Connection timeout occurred")
            self.assertEqual(data['products'], [])

    def test_scrape_invalid_page_parameter(self):
        """Test invalid page parameter returns 400."""
        response = self.get(self.endpoint_url, {
            'keyword': 'test',
            'page': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Page parameter must be a valid integer')
        
    def test_scrape_exception_handling(self):
        """Test exception handling in scraper."""
        with patch(self.patch_path) as mock_create_scraper:
            mock_scraper = Mock()
            mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
            mock_create_scraper.return_value = mock_scraper
            
            response = self.get(self.endpoint_url, {'keyword': 'test'})
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Internal server error occurred')

    def test_post_method_not_allowed(self):
        """Test that POST method is not allowed."""
        response = self.client.post(self.endpoint_url, {'keyword': 'test'})
        self.assertEqual(response.status_code, 405)
        
    def test_empty_keyword_returns_400(self):
        """Test that empty keyword returns 400."""
        response = self.get(self.endpoint_url, {'keyword': ''})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Keyword parameter is required')
        
    def test_whitespace_only_keyword_returns_400(self):
        """Test that whitespace-only keyword returns 400."""
        response = self.get(self.endpoint_url, {'keyword': '   '})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Keyword parameter is required')

    def test_negative_page_parameter(self):
        """Test negative page parameter handling."""
        with patch(self.patch_path) as mock_create_scraper:
            mock_scraper = Mock()
            mock_result = ScrapingResult(products=[], success=True)
            mock_scraper.scrape_products.return_value = mock_result
            mock_create_scraper.return_value = mock_scraper
            
            response = self.get(self.endpoint_url, {
                'keyword': 'test',
                'page': '-1'
            })
            
            self.assertEqual(response.status_code, 200)
            mock_scraper.scrape_products.assert_called_once_with(
                keyword='test',
                sort_by_price=True,
                page=-1
            )

    def test_sort_by_price_variations(self):
        """Test various sort_by_price parameter values."""
        test_cases = [
            ('1', True),
            ('yes', True),
            ('True', True),
            ('false', False),
            ('0', False),
            ('no', False),
            ('invalid', False),
            ('', False)
        ]
        
        for sort_value, expected in test_cases:
            with self.subTest(sort_value=sort_value, expected=expected):
                with patch(self.patch_path) as mock_create_scraper:
                    mock_scraper = Mock()
                    mock_result = ScrapingResult(products=[], success=True)
                    mock_scraper.scrape_products.return_value = mock_result
                    mock_create_scraper.return_value = mock_scraper
                    
                    response = self.get(self.endpoint_url, {
                        'keyword': 'test',
                        'sort_by_price': sort_value
                    })
                    
                    self.assertEqual(response.status_code, 200)
                    mock_scraper.scrape_products.assert_called_once_with(
                        keyword='test',
                        sort_by_price=expected,
                        page=0
                    )

    def test_keyword_with_leading_trailing_spaces(self):
        """Test keyword trimming functionality."""
        with patch(self.patch_path) as mock_create_scraper:
            mock_scraper = Mock()
            mock_result = ScrapingResult(products=[], success=True)
            mock_scraper.scrape_products.return_value = mock_result
            mock_create_scraper.return_value = mock_scraper
            
            response = self.get(self.endpoint_url, {
                'keyword': '  test keyword  '
            })
            
            self.assertEqual(response.status_code, 200)
            mock_scraper.scrape_products.assert_called_once_with(
                keyword='test keyword',
                sort_by_price=True,
                page=0
            )
