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
        # Add API token for authentication (required for OWASP A01:2021 - Broken Access Control)
        self.api_token = 'dev-token-12345'
        self.auth_headers = {'HTTP_X_API_TOKEN': self.api_token}
    
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
    
    def _get(self, url, data=None):
        """Helper method to make authenticated GET request"""
        return self.client.get(url, data or {}, **self.auth_headers)
    
    def _post(self, url, data=None):
        """Helper method to make authenticated POST request"""
        return self.client.post(url, data or {}, **self.auth_headers)


class TokopediaAPITest(BaseTokopediaAPITest):
    
    def test_scrape_url_resolves_correctly(self):
        self.assertEqual(self.scrape_url, '/api/tokopedia/scrape/')
    
    def test_scrape_with_filters_url_resolves_correctly(self):
        self.assertEqual(self.scrape_with_filters_url, '/api/tokopedia/scrape-with-filters/')
    
    # ========== Tests for scrape_products endpoint ==========
    
    class TokopediaDatabaseAndUlasanTests(TestCase):
        """Tests to increase coverage for database saving and ulasan endpoint paths."""

        def test_save_products_to_database_with_categorization(self):
            from api.tokopedia import views as tok_views
            # Patch the DB service to return inserted items
            with patch('api.tokopedia.views.TokopediaDatabaseService') as mock_db_service_cls, \
                 patch('db_pricing.models.TokopediaProduct') as mock_product_model, \
                 patch('api.tokopedia.views.AutoCategorizationService') as mock_cat_cls:

                mock_db_service = mock_db_service_cls.return_value
                mock_db_service.save_with_price_update.return_value = {
                    'success': True,
                    'inserted': 2,
                    'updated': 0,
                    'anomalies': []
                }

                # Prepare a mock queryset that supports slicing and values_list
                mock_uncat = MagicMock()
                mock_uncat.__getitem__.return_value = mock_uncat
                mock_uncat.values_list.return_value = [11, 12]

                mock_product_model.objects.filter.return_value.order_by.return_value = mock_uncat

                mock_cat = mock_cat_cls.return_value
                mock_cat.categorize_products.return_value = {'categorized': 1}

                # Call the function with a non-empty products list
                result = tok_views._save_products_to_database([{'name': 'p', 'price': 1}])

                # Assertions
                self.assertIn('categorized', result)
                self.assertEqual(result['categorized'], 1)
                mock_db_service.save_with_price_update.assert_called_once()
                mock_cat.categorize_products.assert_called_once()

        def test_save_products_to_database_handles_exception(self):
            from api.tokopedia import views as tok_views
            with patch('api.tokopedia.views.TokopediaDatabaseService') as mock_db_service_cls:
                mock_db_service = mock_db_service_cls.return_value
                mock_db_service.save_with_price_update.side_effect = Exception('DB fail')

                result = tok_views._save_products_to_database([{'name': 'p'}])

                # Should return failure structure
                self.assertFalse(result.get('success'))
                self.assertEqual(result.get('categorized'), 0)

        def test_scrape_products_ulasan_success_and_exception(self):
            from api.tokopedia import views as tok_views
            from django.test import RequestFactory
            import json

            factory = RequestFactory()
            req = factory.get('/?q=semen')

            # Success path: patch TokopediaPriceScraper to return a successful result
            with patch('api.tokopedia.views.TokopediaPriceScraper') as mock_scraper_cls:
                mock_scraper = mock_scraper_cls.return_value
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.products = []
                mock_result.url = 'https://tokopedia/search?q=semen&ob=5'
                mock_result.error_message = None
                mock_scraper.scrape_products_with_filters.return_value = mock_result

                response = tok_views.scrape_products_ulasan(req)
                data = json.loads(response.content)
                self.assertTrue(data['success'])
                self.assertEqual(data['url'], 'https://tokopedia/search?q=semen&ob=5')

            # Exception path: make scraper raise
            req2 = factory.get('/?q=semen')
            with patch('api.tokopedia.views.TokopediaPriceScraper') as mock_scraper_cls:
                mock_scraper = mock_scraper_cls.return_value
                mock_scraper.scrape_products_with_filters.side_effect = Exception('boom')

                response = tok_views.scrape_products_ulasan(req2)
                data = json.loads(response.content)
                self.assertFalse(data['success'])
                self.assertIn('Tokopedia scraper (ulasan) error', data['error_message'])
    
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
        response = self._get(self.scrape_url, {
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
        
        response = self._get(self.scrape_url, {
            'q': 'nonexistent',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        response_data = self._assert_success_response(response, expected_product_count=0)
        self.assertIsNone(response_data['error_message'])
    
    def test_missing_query_parameter(self):
        response = self._get(self.scrape_url, {
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self._assert_error_response(response, 400, 'Query parameter is required')
    
    def test_empty_query_parameter(self):
        response = self._get(self.scrape_url, {
            'q': '',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self._assert_error_response(response, 400, 'Query parameter cannot be empty')
    
    def test_whitespace_only_query_parameter(self):
        response = self._get(self.scrape_url, {
            'q': '   ',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self._assert_error_response(response, 400, 'Query parameter cannot be empty')
    
    def test_invalid_page_parameter(self):
        response = self._get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': 'invalid'
        })
        
        self._assert_error_response(response, 400, 'page parameter must be a valid integer')
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_sort_by_price_parameter_variations(self, mock_create_scraper):
        """Test that sort_by_price accepts various true/false values"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        # Test truthy value
        response = self._get(self.scrape_url, {'q': 'semen', 'sort_by_price': 'true'})
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(keyword='semen', sort_by_price=True, page=0, limit=20)
        
        # Test falsy value
        response = self._get(self.scrape_url, {'q': 'semen', 'sort_by_price': 'false'})
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(keyword='semen', sort_by_price=False, page=0, limit=20)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_default_parameters(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_url, {
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
        
        response = self._get(self.scrape_url, {
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
        """Test handling of unexpected exceptions during scraping"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
        
        response = self._get(self.scrape_url, {'q': 'semen'})
        
        self._assert_error_response(response, 500, 'Tokopedia scraper error: Unexpected error')
    
    def test_method_not_allowed(self):
        """Test that only GET method is allowed"""
        response = self._post(self.scrape_url, {'q': 'semen'})
        self.assertEqual(response.status_code, 405)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_query_with_special_characters(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_url, {
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
        
        response = self._get(self.scrape_url, {
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
        
        response = self._get(self.scrape_url, {'q': 'semen', 'page': '-1'})
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 0', response_data['error_message'])
        mock_scraper.scrape_products.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_limit_exceeds_maximum(self, mock_create_scraper):
        """Test that limit values exceeding 100 are rejected for security"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_url, {'q': 'semen', 'limit': '200'})
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertIn('exceeds maximum', response_data['error'])
        mock_scraper.scrape_products.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_limit_below_minimum(self, mock_create_scraper):
        """Test that zero and negative limits are rejected"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_url, {'q': 'semen', 'limit': '0'})
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 1', response_data['error_message'])
        mock_scraper.scrape_products.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_limit_at_maximum_allowed(self, mock_create_scraper):
        """Test that limit at exactly 100 is accepted"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_url, {'q': 'semen', 'limit': '100'})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(keyword='semen', sort_by_price=True, page=0, limit=100)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_factory_exception_handling(self, mock_create_scraper):
        """Test exception handling when scraper factory fails"""
        mock_create_scraper.side_effect = Exception("Factory error")
        
        response = self._get(self.scrape_url, {'q': 'semen'})
        
        self._assert_error_response(response, 500, 'Tokopedia scraper error: Factory error')
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_json_response_structure_with_products(self, mock_create_scraper):
        product = self._create_mock_product("Test Product", 100000, "https://www.tokopedia.com/product")
        result = self._create_mock_result(
            products=[product],
            url="https://www.tokopedia.com/search"
        )
        self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_url, {'q': 'semen'})
        
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
        
        response = self._get(self.scrape_url, {'q': '  semen  '})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(keyword='semen', sort_by_price=True, page=0, limit=20)


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
        
        response = self._get(self.scrape_with_filters_url, {
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
        
        response = self._get(self.scrape_with_filters_url, {
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
        
        response = self._get(self.scrape_with_filters_url, {
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
        
        response = self._get(self.scrape_with_filters_url, {
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
        
        response = self._get(self.scrape_with_filters_url, {'q': 'semen'})
        
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
        response = self._get(self.scrape_with_filters_url, {
            'min_price': '50000',
            'max_price': '100000'
        })
        
        self._assert_error_response(response, 400, 'Query parameter is required')
    
    def test_filters_empty_query_parameter(self):
        response = self._get(self.scrape_with_filters_url, {
            'q': '',
            'min_price': '50000'
        })
        
        self._assert_error_response(response, 400, 'Query parameter cannot be empty')
    
    def test_filters_invalid_min_price(self):
        response = self._get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': 'invalid'
        })
        
        self._assert_error_response(response, 400, 'min_price parameter must be a valid integer')
    
    def test_filters_invalid_max_price(self):
        response = self._get(self.scrape_with_filters_url, {
            'q': 'semen',
            'max_price': 'invalid'
        })
        
        self._assert_error_response(response, 400, 'max_price parameter must be a valid integer')
    
    def test_filters_invalid_page_parameter(self):
        response = self._get(self.scrape_with_filters_url, {
            'q': 'semen',
            'page': 'invalid'
        })
        
        self._assert_error_response(response, 400, 'page parameter must be a valid integer')
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_sort_by_price_variations(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        # Test truthy value
        response = self._get(self.scrape_with_filters_url, {
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
        response = self._get(self.scrape_with_filters_url, {
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
        
        response = self._get(self.scrape_with_filters_url, {
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
        """Test exception handling in filters endpoint"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        mock_scraper.scrape_products_with_filters.side_effect = Exception("Unexpected error")
        
        response = self._get(self.scrape_with_filters_url, {'q': 'semen'})
        
        self._assert_error_response(response, 500, 'Tokopedia scraper with filters error: Unexpected error')
    
    def test_filters_method_not_allowed(self):
        """Test that only GET method is allowed for filters endpoint"""
        response = self._post(self.scrape_with_filters_url, {'q': 'semen'})
        self.assertEqual(response.status_code, 405)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_all_parameters(self, mock_create_scraper):
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_with_filters_url, {
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
        
        response = self._get(self.scrape_with_filters_url, {
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
        
        response = self._get(self.scrape_with_filters_url, {'q': '  semen  ', 'min_price': '50000'})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen', sort_by_price=True, page=0, min_price=50000, max_price=None, location=None, limit=20
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_zero_prices(self, mock_create_scraper):
        """Test filters with zero prices"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_with_filters_url, {
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
        
        response = self._get(self.scrape_url, {'q': 'semen'})
        
        self._assert_error_response(response, 500, "Tokopedia scraper error: Unexpected error occurred")
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_products_generic_exception(self, mock_create_scraper):
        """Test generic exception handling in scrape_products (line 115)"""
        mock_create_scraper.side_effect = RuntimeError("Factory initialization failed")
        
        response = self._get(self.scrape_url, {'q': 'semen'})
        
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
        
        response = self._get(self.scrape_with_filters_url, {'q': 'semen'})
        
        self._assert_error_response(response, 500, "Tokopedia scraper with filters error: Network timeout")
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_with_filters_generic_exception(self, mock_create_scraper):
        """Test generic exception in scrape_products_with_filters (line 165)"""
        mock_create_scraper.side_effect = ValueError("Invalid configuration")
        
        response = self._get(self.scrape_with_filters_url, {'q': 'semen'})
        
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
        """Test that limit values exceeding 100 are rejected for security in filters endpoint"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_with_filters_url, {
            'q': 'semen',
            'limit': '200'  # Exceeds max of 100
        })
        
        # Should reject excessive limits with 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertIn('exceeds maximum', response_data['error'])
        mock_scraper.scrape_products_with_filters.assert_not_called()
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_negative_page(self, mock_create_scraper):
        """Test that negative page numbers are rejected in filters endpoint"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_with_filters_url, {
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
    def test_filters_negative_prices(self, mock_create_scraper):
        """Test that negative prices are rejected in filters endpoint"""
        result = self._create_mock_result()
        mock_scraper = self._setup_mock_scraper(mock_create_scraper, result)
        
        response = self._get(self.scrape_with_filters_url, {'q': 'semen', 'min_price': '-1000'})
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('must be at least 0', response_data['error_message'])
        mock_scraper.scrape_products_with_filters.assert_not_called()
    



class TokopediaViewsHelpersCoverage(TestCase):
    def test_sanitize_string_and_format_result(self):
        from api.tokopedia.views import _sanitize_string, _format_scrape_result
        from unittest.mock import MagicMock

        raw = "  abc\t\n\r \x01\x02def  " + ("x" * 500)
        # _sanitize_string truncates before removing control chars
        self.assertEqual(_sanitize_string(raw, max_length=10), "abc")

        product = MagicMock()
        product.name = "Name"
        product.price = 1
        product.url = "https://u"
        # product.unit intentionally left as MagicMock to be coerced to None

        result = MagicMock()
        result.success = True
        result.products = [product]
        result.url = "https://search"
        result.error_message = None

        payload = _format_scrape_result(result)
        self.assertTrue(payload['success'])
        self.assertEqual(payload['url'], "https://search")
        self.assertEqual(payload['products'][0]['name'], "Name")
        self.assertIsNone(payload['products'][0]['unit'])

    def test_parse_integer_parameter_required_and_default_clamp(self):
        from api.tokopedia.views import _parse_integer_parameter
        from django.test import RequestFactory

        factory = RequestFactory()
        # Missing param with required=True -> error
        request = factory.get('/test')
        value, err = _parse_integer_parameter(request, 'must', required=True)
        self.assertIsNone(value)
        self.assertIsNotNone(err)

        # Default provided beyond max should be clamped
        value, err = _parse_integer_parameter(request, 'lim', default='5000', required=False, min_value=1, max_value=1000)
        self.assertEqual(value, 1000)
        self.assertIsNone(err)

    def test_sanitize_string_none_and_boolean_default(self):
        from api.tokopedia.views import _sanitize_string, _parse_boolean_parameter
        class Req:
            GET = {}
        # Empty string input returns empty string
        self.assertEqual(_sanitize_string(""), "")
        # Missing param uses default path
        self.assertFalse(_parse_boolean_parameter(Req(), 'flag', default='false'))
    
    def test_parse_default_value_below_min(self):
        """Test _parse_default_value when default is below min_value (line 97)"""
        from api.tokopedia.views import _parse_default_value
        
        # Default value below min should be clamped to min
        result = _parse_default_value('5', min_value=10, max_value=100)
        self.assertEqual(result, 10)
        
        # Default value above max should be clamped to max  
        result = _parse_default_value('200', min_value=10, max_value=100)
        self.assertEqual(result, 100)
    
    def test_parse_integer_parameter_invalid_sanitized_value(self):
        """Test _parse_integer_parameter with value that fails int conversion (lines 147-148)"""
        from api.tokopedia import views
        from unittest.mock import patch
        
        class MockRequest:
            GET = {'param': '123'}  # Valid integer string
        
        request = MockRequest()
        
        # Mock int() only in the views module to test the exception handler
        original_int = int
        def selective_int(value):
            if value == '123':  # Only raise for our test value
                raise ValueError("test error")
            return original_int(value)
        
        with patch.object(views, 'int', side_effect=selective_int):
            value, error = views._parse_integer_parameter(request, 'param', required=False)
            
            # Should catch ValueError and return error response
            self.assertIsNone(value)
            self.assertIsNotNone(error)
            self.assertEqual(error.status_code, 400)


