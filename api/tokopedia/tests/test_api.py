from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json


class BaseTokopediaAPITest(TestCase):
    """Base test class with common helper methods"""
    
    def setUp(self):
        self.client = Client()
        self.scrape_url = reverse('tokopedia:scrape_products')
        self.scrape_with_filters_url = reverse('tokopedia:scrape_products_with_filters')
    
    def _create_mock_product(self, name: str, price: int, url: str, location: str = None):
        """Create a mock product object"""
        mock_product = MagicMock()
        mock_product.name = name
        mock_product.price = price
        mock_product.url = url
        mock_product.location = location
        return mock_product
    
    def _create_mock_result(self, success: bool = True, products: list = None, 
                           error_message: str = None, url: str = "https://www.tokopedia.com/test"):
        """Create a mock scraper result"""
        mock_result = MagicMock()
        mock_result.success = success
        mock_result.products = products or []
        mock_result.error_message = error_message
        mock_result.url = url
        return mock_result
    
    def _setup_mock_scraper(self, mock_create_scraper, result=None):
        """Setup mock scraper with default or custom result"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        if result is None:
            result = self._create_mock_result()
        
        mock_scraper.scrape_products.return_value = result
        mock_scraper.scrape_products_with_filters.return_value = result
        
        return mock_scraper
    
    def _assert_error_response(self, response, status_code: int, error_message: str):
        """Assert error response structure and content"""
        self.assertEqual(response.status_code, status_code)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], error_message)
        self.assertEqual(len(response_data['products']), 0)
    
    def _assert_success_response(self, response, expected_product_count: int = 0):
        """Assert successful response structure"""
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), expected_product_count)
        return response_data
    
    def _assert_product_data(self, product_data: dict, name: str, price: int, url: str):
        """Assert product data matches expected values"""
        self.assertEqual(product_data['name'], name)
        self.assertEqual(product_data['price'], price)
        self.assertEqual(product_data['url'], url)
    
    def _assert_response_structure(self, response_data: dict):
        """Assert response has all required fields"""
        self.assertIn('success', response_data)
        self.assertIn('products', response_data)
        self.assertIn('error_message', response_data)
        self.assertIn('url', response_data)


class TokopediaAPITest(BaseTokopediaAPITest):
    
    def test_scrape_url_resolves_correctly(self):
        self.assertEqual(self.scrape_url, '/api/tokopedia/scrape/')
    
    def test_scrape_with_filters_url_resolves_correctly(self):
        self.assertEqual(self.scrape_with_filters_url, '/api/tokopedia/scrape-with-filters/')
    
    # ========== Tests for scrape_products endpoint ==========
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_successful_scrape_with_products(self, mock_create_scraper):
        # Create mock products
        products = [
            self._create_mock_product("Test Product 1", 50000, "https://www.tokopedia.com/test-product-1"),
            self._create_mock_product("Test Product 2", 75000, "https://www.tokopedia.com/test-product-2")
        ]
        
        result = self._create_mock_result(
            success=True,
            products=products,
            url="https://www.tokopedia.com/search?q=semen&ob=5"
        )
        
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        # Make the API call
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        # Assertions
        response_data = self._assert_success_response(response, expected_product_count=2)
        self.assertIsNone(response_data['error_message'])
        
        # Check products
        self._assert_product_data(response_data['products'][0], "Test Product 1", 50000, 
                                 "https://www.tokopedia.com/test-product-1")
        self._assert_product_data(response_data['products'][1], "Test Product 2", 75000, 
                                 "https://www.tokopedia.com/test-product-2")
        
        self.assertEqual(response_data['url'], "https://www.tokopedia.com/search?q=semen&ob=5")
        
        # Verify scraper was called with correct parameters
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_successful_scrape_with_no_products(self, mock_create_scraper):
        result = self._create_mock_result(url="https://www.tokopedia.com/search?q=nonexistent")
        self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'nonexistent',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        response_data = self._assert_success_response(response, expected_product_count=0)
        self.assertIsNone(response_data['error_message'])
    
    def test_missing_query_parameter(self):
        response = self.client.get(self.scrape_url, {
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self._assert_error_response(response, 400, 'Query parameter is required')
    
    def test_empty_query_parameter(self):
        response = self.client.get(self.scrape_url, {
            'q': '',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self._assert_error_response(response, 400, 'Query parameter cannot be empty')
    
    def test_whitespace_only_query_parameter(self):
        response = self.client.get(self.scrape_url, {
            'q': '   ',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self._assert_error_response(response, 400, 'Query parameter cannot be empty')
    
    def test_invalid_page_parameter(self):
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': 'invalid'
        })
        
        self._assert_error_response(response, 400, 'page parameter must be a valid integer')
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_sort_by_price_parameter_variations(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        # Test various truthy values
        for value in ['true', '1', 'yes', 'TRUE', 'True']:
            response = self.client.get(self.scrape_url, {
                'q': 'semen',
                'sort_by_price': value,
                'page': '0'
            })
            self.assertEqual(response.status_code, 200)
            mock_scraper.scrape_products.assert_called_with(
                keyword='semen',
                sort_by_price=True,
                page=0,
                limit=20
            )
        
        # Test various falsy values
        for value in ['false', '0', 'no', 'FALSE', 'False', 'random']:
            response = self.client.get(self.scrape_url, {
                'q': 'semen',
                'sort_by_price': value,
                'page': '0'
            })
            self.assertEqual(response.status_code, 200)
            mock_scraper.scrape_products.assert_called_with(
                keyword='semen',
                sort_by_price=False,
                page=0,
                limit=20
            )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_default_parameters(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen'
        })
        
        self.assertEqual(response.status_code, 200)
        # Should default to sort_by_price=True and page=0
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scraper_failure(self, mock_create_scraper):
        result = self._create_mock_result(
            success=False,
            error_message="Unable to connect to website"
        )
        self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], "Unable to connect to website")
        self.assertEqual(len(response_data['products']), 0)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_unexpected_exception(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self._assert_error_response(response, 500, 'Tokopedia scraper error: Unexpected error')
    
    def test_post_method_not_allowed(self):
        response = self.client.post(self.scrape_url, {'q': 'semen'})
        self.assertEqual(response.status_code, 405)
    
    def test_put_method_not_allowed(self):
        response = self.client.put(self.scrape_url, {'q': 'semen'})
        self.assertEqual(response.status_code, 405)
    
    def test_delete_method_not_allowed(self):
        response = self.client.delete(self.scrape_url)
        self.assertEqual(response.status_code, 405)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_query_with_special_characters(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen & tablet',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen & tablet',
            sort_by_price=True,
            page=0,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_large_page_number(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '999'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=999,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_negative_page_number(self, mock_create_scraper):
        """Test that negative page numbers are rejected for security"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '-1'
        })
        
        # Should reject negative page numbers with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 0', response_data['error_message'])
        # Scraper should not be called with invalid input
        mock_scraper.scrape_products.assert_not_called()
    
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_zero_page_number(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_limit_exceeds_maximum(self, mock_create_scraper):
        """Test that limit values exceeding 1000 are rejected for security"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'limit': '5000'  # Exceeds max of 1000
        })
        
        # Should reject excessive limits with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must not exceed 1000', response_data['error_message'])
        mock_scraper.scrape_products.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_limit_zero_rejected(self, mock_create_scraper):
        """Test that zero limit is rejected"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'limit': '0'
        })
        
        # Should reject zero limit with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 1', response_data['error_message'])
        mock_scraper.scrape_products.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_limit_negative_rejected(self, mock_create_scraper):
        """Test that negative limits are rejected"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'limit': '-10'
        })
        
        # Should reject negative limit with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 1', response_data['error_message'])
        mock_scraper.scrape_products.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_limit_at_maximum_allowed(self, mock_create_scraper):
        """Test that limit at exactly 1000 is accepted"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'limit': '1000'  # Exactly at max
        })
        
        # Should accept limit at maximum
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            limit=1000
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_factory_exception_handling(self, mock_create_scraper):
        mock_create_scraper.side_effect = Exception("Factory error")
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self._assert_error_response(response, 500, 'Tokopedia scraper error: Factory error')
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_json_response_structure_with_products(self, mock_create_scraper):
        product = self._create_mock_product("Test Product", 100000, "https://www.tokopedia.com/product")
        result = self._create_mock_result(
            products=[product],
            url="https://www.tokopedia.com/search"
        )
        self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {'q': 'semen'})
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Check response structure
        self._assert_response_structure(response_data)
        
        # Check product structure
        self.assertEqual(len(response_data['products']), 1)
        product_data = response_data['products'][0]
        self.assertIn('name', product_data)
        self.assertIn('price', product_data)
        self.assertIn('url', product_data)
        
        self._assert_product_data(product_data, "Test Product", 100000, "https://www.tokopedia.com/product")
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_query_trimming(self, mock_create_scraper):
        """Test that query parameter is trimmed"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_url, {
            'q': '  semen  ',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        # Verify that the query was trimmed
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            limit=20
        )


class TokopediaAPIWithFiltersTest(BaseTokopediaAPITest):
    
    # ========== Tests for scrape_products_with_filters endpoint ==========
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_successful_scrape_with_filters(self, mock_create_scraper):
        # Create mock products
        products = [
            self._create_mock_product("Filtered Product 1", 50000, "https://www.tokopedia.com/filtered-1"),
            self._create_mock_product("Filtered Product 2", 60000, "https://www.tokopedia.com/filtered-2")
        ]
        
        result = self._create_mock_result(
            products=products,
            url="https://www.tokopedia.com/search?q=semen&pmin=40000&pmax=70000"
        )
        
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0',
            'min_price': '40000',
            'max_price': '70000',
            'location': 'Jakarta'
        })
        
        response_data = self._assert_success_response(response, expected_product_count=2)
        self._assert_product_data(response_data['products'][0], "Filtered Product 1", 50000, 
                                 "https://www.tokopedia.com/filtered-1")
        self._assert_product_data(response_data['products'][1], "Filtered Product 2", 60000, 
                                 "https://www.tokopedia.com/filtered-2")
        
        # Verify scraper was called with correct parameters
        mock_scraper.scrape_products_with_filters.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=40000,
            max_price=70000,
            location='Jakarta',
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_min_price_only(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': '50000'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=50000,
            max_price=None,
            location=None,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_max_price_only(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'max_price': '100000'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=None,
            max_price=100000,
            location=None,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_location_only(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'location': 'Bandung'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=None,
            max_price=None,
            location='Bandung',
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_no_optional_parameters(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {'q': 'semen'})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=None,
            max_price=None,
            location=None,
            limit=20
        )
    
    def test_filters_missing_query_parameter(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'min_price': '50000',
            'max_price': '100000'
        })
        
        self._assert_error_response(response, 400, 'Query parameter is required')
    
    def test_filters_empty_query_parameter(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'q': '',
            'min_price': '50000'
        })
        
        self._assert_error_response(response, 400, 'Query parameter cannot be empty')
    
    def test_filters_invalid_min_price(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': 'invalid'
        })
        
        self._assert_error_response(response, 400, 'min_price parameter must be a valid integer')
    
    def test_filters_invalid_max_price(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'max_price': 'invalid'
        })
        
        self._assert_error_response(response, 400, 'max_price parameter must be a valid integer')
    
    def test_filters_invalid_page_parameter(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'page': 'invalid'
        })
        
        self._assert_error_response(response, 400, 'page parameter must be a valid integer')
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_sort_by_price_variations(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        # Test truthy value
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'sort_by_price': 'true'
        })
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=None,
            max_price=None,
            location=None,
            limit=20
        )
        
        # Test falsy value
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'sort_by_price': 'false'
        })
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=False,
            page=0,
            min_price=None,
            max_price=None,
            location=None,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_scraper_failure(self, mock_create_scraper):
        result = self._create_mock_result(
            success=False,
            error_message="Filter scraping failed"
        )
        self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': '50000'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], "Filter scraping failed")
        self.assertEqual(len(response_data['products']), 0)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_unexpected_exception(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        mock_scraper.scrape_products_with_filters.side_effect = Exception("Unexpected error")
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': '50000'
        })
        
        self._assert_error_response(response, 500, 'Tokopedia scraper with filters error: Unexpected error')
    
    def test_filters_post_method_not_allowed(self):
        response = self.client.post(self.scrape_with_filters_url, {'q': 'semen'})
        self.assertEqual(response.status_code, 405)
    
    def test_filters_put_method_not_allowed(self):
        response = self.client.put(self.scrape_with_filters_url, {'q': 'semen'})
        self.assertEqual(response.status_code, 405)
    
    def test_filters_delete_method_not_allowed(self):
        response = self.client.delete(self.scrape_with_filters_url)
        self.assertEqual(response.status_code, 405)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_all_parameters(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen gaming',
            'sort_by_price': 'false',
            'page': '2',
            'min_price': '5000000',
            'max_price': '10000000',
            'location': 'Surabaya'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen gaming',
            sort_by_price=False,
            page=2,
            min_price=5000000,
            max_price=10000000,
            location='Surabaya',
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_json_response_structure(self, mock_create_scraper):
        product = self._create_mock_product("Filtered Product", 75000, "https://www.tokopedia.com/filtered")
        result = self._create_mock_result(
            products=[product],
            url="https://www.tokopedia.com/search"
        )
        self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': '50000'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Check response structure
        self._assert_response_structure(response_data)
        
        # Check product structure
        self.assertEqual(len(response_data['products']), 1)
        product_data = response_data['products'][0]
        self.assertIn('name', product_data)
        self.assertIn('price', product_data)
        self.assertIn('url', product_data)
        
        self._assert_product_data(product_data, "Filtered Product", 75000, "https://www.tokopedia.com/filtered")
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_query_trimming(self, mock_create_scraper):
        """Test that query parameter is trimmed in filters endpoint"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': '  semen  ',
            'min_price': '50000'
        })
        
        self.assertEqual(response.status_code, 200)
        # Verify that the query was trimmed
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=50000,
            max_price=None,
            location=None,
            limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_zero_prices(self, mock_create_scraper):
        """Test filters with zero prices"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': '0',
            'max_price': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=0,
            max_price=0,
            location=None,
            limit=20
        )
    
    def test_parse_int_param_with_invalid_default(self):
        """Test _parse_integer_parameter when default value cannot be converted to int (lines 61, 66-67)"""
        # Import the internal function
        from api.tokopedia.views import _parse_integer_parameter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/test/')  # No parameters
        
        # Test with invalid default value (will trigger ValueError in line 66)
        result, error = _parse_integer_parameter(request, 'test_param', required=False, default='invalid')
        self.assertIsNone(result)
        self.assertIsNone(error)
        
        # Test with valid default value for comparison
        result, error = _parse_integer_parameter(request, 'test_param', required=False, default='10')
        self.assertEqual(result, 10)
        self.assertIsNone(error)
        
        # Test with no default (should return None, None)
        result, error = _parse_integer_parameter(request, 'test_param', required=False, default=None)
        self.assertIsNone(result)
        self.assertIsNone(error)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_products_exception_handling(self, mock_create_scraper):
        """Test exception handling in scrape_products endpoint (line 115)"""
        # Setup mock to raise exception during scraping
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        mock_scraper.scrape_products.side_effect = Exception("Unexpected error occurred")
        
        response = self.client.get(self.scrape_url, {'q': 'semen'})
        
        self._assert_error_response(response, 500, "Tokopedia scraper error: Unexpected error occurred")
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_products_generic_exception(self, mock_create_scraper):
        """Test generic exception handling in scrape_products (line 115)"""
        mock_create_scraper.side_effect = RuntimeError("Factory initialization failed")
        
        response = self.client.get(self.scrape_url, {'q': 'semen'})
        
        # Should catch and wrap the exception
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn("Factory initialization failed", response_data['error_message'])
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_with_filters_exception_handling(self, mock_create_scraper):
        """Test exception handling in scrape_products_with_filters endpoint (line 165)"""
        # Setup mock to raise exception during scraping
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        mock_scraper.scrape_products_with_filters.side_effect = Exception("Network timeout")
        
        response = self.client.get(self.scrape_with_filters_url, {'q': 'semen'})
        
        self._assert_error_response(response, 500, "Tokopedia scraper with filters error: Network timeout")
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_with_filters_generic_exception(self, mock_create_scraper):
        """Test generic exception in scrape_products_with_filters (line 165)"""
        mock_create_scraper.side_effect = ValueError("Invalid configuration")
        
        response = self.client.get(self.scrape_with_filters_url, {'q': 'semen'})
        
        # Should catch and wrap the exception
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn("Invalid configuration", response_data['error_message'])
    
    def test_parse_integer_with_none_default_and_no_param(self):
        """Test _parse_integer_parameter returning None when no param and no default (line 61)"""
        from api.tokopedia.views import _parse_integer_parameter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/test/')  # No parameters
        
        # When default is None and param is missing, should return (None, None)
        result, error = _parse_integer_parameter(request, 'missing_param', default=None, required=False)
        
        self.assertIsNone(result)
        self.assertIsNone(error)
    
    def test_parse_integer_with_invalid_default_value(self):
        """Test _parse_integer_parameter with invalid default that causes ValueError (line 61)"""
        from api.tokopedia.views import _parse_integer_parameter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/test/')  # No parameters
        
        # When default conversion fails with ValueError, should return (None, None)
        result, error = _parse_integer_parameter(request, 'missing_param', default='invalid', required=False)
        
        self.assertIsNone(result)
        self.assertIsNone(error)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_limit_exceeds_maximum(self, mock_create_scraper):
        """Test that limit values exceeding 1000 are rejected for security in filters endpoint"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'limit': '2000'  # Exceeds max of 1000
        })
        
        # Should reject excessive limits with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must not exceed 1000', response_data['error_message'])
        mock_scraper.scrape_products_with_filters.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_negative_page(self, mock_create_scraper):
        """Test that negative page numbers are rejected in filters endpoint"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'page': '-5'
        })
        
        # Should reject negative page with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 0', response_data['error_message'])
        mock_scraper.scrape_products_with_filters.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_negative_min_price(self, mock_create_scraper):
        """Test that negative min_price is rejected"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': '-1000'
        })
        
        # Should reject negative price with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 0', response_data['error_message'])
        mock_scraper.scrape_products_with_filters.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_negative_max_price(self, mock_create_scraper):
        """Test that negative max_price is rejected"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'max_price': '-5000'
        })
        
        # Should reject negative price with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 0', response_data['error_message'])
        mock_scraper.scrape_products_with_filters.assert_not_called()


