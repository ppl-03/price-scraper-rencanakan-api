from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json


class TokopediaAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.scrape_url = reverse('tokopedia:scrape_products')
        self.scrape_with_filters_url = reverse('tokopedia:scrape_products_with_filters')
    
    def test_scrape_url_resolves_correctly(self):
        self.assertEqual(self.scrape_url, '/api/tokopedia/scrape/')
    
    def test_scrape_with_filters_url_resolves_correctly(self):
        self.assertEqual(self.scrape_with_filters_url, '/api/tokopedia/scrape-with-filters/')
    
    # ========== Tests for scrape_products endpoint ==========
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_successful_scrape_with_products(self, mock_create_scraper):
        # Mock the scraper and its result
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        # Create mock products
        mock_product1 = MagicMock()
        mock_product1.name = "Test Product 1"
        mock_product1.price = 50000
        mock_product1.url = "https://www.tokopedia.com/test-product-1"
        
        mock_product2 = MagicMock()
        mock_product2.name = "Test Product 2"
        mock_product2.price = 75000
        mock_product2.url = "https://www.tokopedia.com/test-product-2"
        
        # Mock the scraping result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product1, mock_product2]
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/search?q=semen&ob=5"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        # Make the API call
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertIsNone(response_data['error_message'])
        self.assertEqual(len(response_data['products']), 2)
        
        # Check first product
        self.assertEqual(response_data['products'][0]['name'], "Test Product 1")
        self.assertEqual(response_data['products'][0]['price'], 50000)
        self.assertEqual(response_data['products'][0]['url'], "https://www.tokopedia.com/test-product-1")
        
        # Check second product
        self.assertEqual(response_data['products'][1]['name'], "Test Product 2")
        self.assertEqual(response_data['products'][1]['price'], 75000)
        self.assertEqual(response_data['products'][1]['url'], "https://www.tokopedia.com/test-product-2")
        
        self.assertEqual(response_data['url'], "https://www.tokopedia.com/search?q=semen&ob=5")
        
        # Verify scraper was called with correct parameters
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_successful_scrape_with_no_products(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/search?q=nonexistent"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'q': 'nonexistent',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertIsNone(response_data['error_message'])
    
    def test_missing_query_parameter(self):
        response = self.client.get(self.scrape_url, {
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'Query parameter is required')
        self.assertEqual(len(response_data['products']), 0)
    
    def test_empty_query_parameter(self):
        response = self.client.get(self.scrape_url, {
            'q': '',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'Query parameter cannot be empty')
    
    def test_whitespace_only_query_parameter(self):
        response = self.client.get(self.scrape_url, {
            'q': '   ',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'Query parameter cannot be empty')
    
    def test_invalid_page_parameter(self):
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'Page parameter must be a valid integer')
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_sort_by_price_parameter_variations(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
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
                page=0
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
                page=0
            )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_default_parameters(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen'
        })
        
        self.assertEqual(response.status_code, 200)
        # Should default to sort_by_price=True and page=0
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scraper_failure(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.products = []
        mock_result.error_message = "Unable to connect to website"
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
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
        
        # Make the scraper raise an exception
        mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('Tokopedia scraper error:', response_data['error_message'])
    
    def test_post_method_not_allowed(self):
        response = self.client.post(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 405)
    
    def test_put_method_not_allowed(self):
        response = self.client.put(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 405)
    
    def test_delete_method_not_allowed(self):
        response = self.client.delete(self.scrape_url)
        
        self.assertEqual(response.status_code, 405)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_query_with_special_characters(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen & tablet',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen & tablet',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_large_page_number(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '999'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=999
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_negative_page_number(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '-1'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=-1
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_zero_page_number(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_factory_exception_handling(self, mock_create_scraper):
        mock_create_scraper.side_effect = Exception("Factory error")
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('Tokopedia scraper error:', response_data['error_message'])
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_json_response_structure_with_products(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        # Create mock product with all attributes
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 100000
        mock_product.url = "https://www.tokopedia.com/product"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/search"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'q': 'semen'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Check response structure
        self.assertIn('success', response_data)
        self.assertIn('products', response_data)
        self.assertIn('error_message', response_data)
        self.assertIn('url', response_data)
        
        # Check product structure
        self.assertEqual(len(response_data['products']), 1)
        product = response_data['products'][0]
        self.assertIn('name', product)
        self.assertIn('price', product)
        self.assertIn('url', product)
        
        self.assertEqual(product['name'], "Test Product")
        self.assertEqual(product['price'], 100000)
        self.assertEqual(product['url'], "https://www.tokopedia.com/product")
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_query_trimming(self, mock_create_scraper):
        """Test that query parameter is trimmed"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
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
            page=0
        )


class TokopediaAPIWithFiltersTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.scrape_with_filters_url = reverse('tokopedia:scrape_products_with_filters')
    
    # ========== Tests for scrape_products_with_filters endpoint ==========
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_successful_scrape_with_filters(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        # Create mock products
        mock_product1 = MagicMock()
        mock_product1.name = "Filtered Product 1"
        mock_product1.price = 50000
        mock_product1.url = "https://www.tokopedia.com/filtered-1"
        
        mock_product2 = MagicMock()
        mock_product2.name = "Filtered Product 2"
        mock_product2.price = 60000
        mock_product2.url = "https://www.tokopedia.com/filtered-2"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product1, mock_product2]
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/search?q=semen&pmin=40000&pmax=70000"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'sort_by_price': 'true',
            'page': '0',
            'min_price': '40000',
            'max_price': '70000',
            'location': 'Jakarta'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 2)
        self.assertEqual(response_data['products'][0]['name'], "Filtered Product 1")
        self.assertEqual(response_data['products'][1]['name'], "Filtered Product 2")
        
        # Verify scraper was called with correct parameters
        mock_scraper.scrape_products_with_filters.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=40000,
            max_price=70000,
            location='Jakarta'
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_min_price_only(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
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
            location=None
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_max_price_only(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
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
            location=None
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_location_only(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
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
            location='Bandung'
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_no_optional_parameters(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products_with_filters.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=0,
            min_price=None,
            max_price=None,
            location=None
        )
    
    def test_filters_missing_query_parameter(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'min_price': '50000',
            'max_price': '100000'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'Query parameter is required')
    
    def test_filters_empty_query_parameter(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'q': '',
            'min_price': '50000'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'Query parameter cannot be empty')
    
    def test_filters_invalid_min_price(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'min_price must be a valid integer')
    
    def test_filters_invalid_max_price(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'max_price': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'max_price must be a valid integer')
    
    def test_filters_invalid_page_parameter(self):
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'page': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], 'Page parameter must be a valid integer')
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_sort_by_price_variations(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
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
            location=None
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
            location=None
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_scraper_failure(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.products = []
        mock_result.error_message = "Filter scraping failed"
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
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
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('Tokopedia scraper with filters error:', response_data['error_message'])
    
    def test_filters_post_method_not_allowed(self):
        response = self.client.post(self.scrape_with_filters_url, {
            'q': 'semen'
        })
        
        self.assertEqual(response.status_code, 405)
    
    def test_filters_put_method_not_allowed(self):
        response = self.client.put(self.scrape_with_filters_url, {
            'q': 'semen'
        })
        
        self.assertEqual(response.status_code, 405)
    
    def test_filters_delete_method_not_allowed(self):
        response = self.client.delete(self.scrape_with_filters_url)
        
        self.assertEqual(response.status_code, 405)
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_with_all_parameters(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
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
            location='Surabaya'
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_json_response_structure(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_product = MagicMock()
        mock_product.name = "Filtered Product"
        mock_product.price = 75000
        mock_product.url = "https://www.tokopedia.com/filtered"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/search"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
        response = self.client.get(self.scrape_with_filters_url, {
            'q': 'semen',
            'min_price': '50000'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Check response structure
        self.assertIn('success', response_data)
        self.assertIn('products', response_data)
        self.assertIn('error_message', response_data)
        self.assertIn('url', response_data)
        
        # Check product structure
        self.assertEqual(len(response_data['products']), 1)
        product = response_data['products'][0]
        self.assertIn('name', product)
        self.assertIn('price', product)
        self.assertIn('url', product)
        
        self.assertEqual(product['name'], "Filtered Product")
        self.assertEqual(product['price'], 75000)
        self.assertEqual(product['url'], "https://www.tokopedia.com/filtered")
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_query_trimming(self, mock_create_scraper):
        """Test that query parameter is trimmed in filters endpoint"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
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
            location=None
        )
    
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_filters_zero_prices(self, mock_create_scraper):
        """Test filters with zero prices"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.tokopedia.com/test"
        
        mock_scraper.scrape_products_with_filters.return_value = mock_result
        
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
            location=None
        )
