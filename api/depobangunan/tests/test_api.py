from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json


class DepoBangunanAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.scrape_url = reverse('depobangunan:scrape_products')
    
    def test_scrape_url_resolves_correctly(self):
        self.assertEqual(self.scrape_url, '/api/depobangunan/scrape/')
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_successful_scrape_with_products(self, mock_create_scraper):
        # Mock the scraper and its result
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        # Create mock products
        mock_product1 = MagicMock()
        mock_product1.name = "Test Product 1"
        mock_product1.price = 5000
        mock_product1.url = "https://www.depobangunan.co.id/test-product-1"
        
        mock_product2 = MagicMock()
        mock_product2.name = "Test Product 2"
        mock_product2.price = 7500
        mock_product2.url = "https://www.depobangunan.co.id/test-product-2"
        
        # Mock the scraping result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product1, mock_product2]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        # Make the API call
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
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
        self.assertEqual(response_data['products'][0]['price'], 5000)
        self.assertEqual(response_data['products'][0]['url'], "https://www.depobangunan.co.id/test-product-1")
        
        # Check second product
        self.assertEqual(response_data['products'][1]['name'], "Test Product 2")
        self.assertEqual(response_data['products'][1]['price'], 7500)
        self.assertEqual(response_data['products'][1]['url'], "https://www.depobangunan.co.id/test-product-2")
        
        self.assertEqual(response_data['url'], "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high")
        
        # Verify scraper was called with correct parameters
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='cat',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_successful_scrape_with_no_products(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/catalogsearch/result/?q=nonexistent"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'nonexistent',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertIsNone(response_data['error_message'])
    
    def test_missing_keyword_parameter(self):
        response = self.client.get(self.scrape_url, {
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Keyword parameter is required')
    
    def test_empty_keyword_parameter(self):
        response = self.client.get(self.scrape_url, {
            'keyword': '',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Keyword parameter is required')
    
    def test_whitespace_only_keyword_parameter(self):
        response = self.client.get(self.scrape_url, {
            'keyword': '   ',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Keyword parameter is required')
    
    def test_invalid_page_parameter(self):
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Page parameter must be a valid integer')
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_sort_by_price_parameter_variations(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        # Test various truthy values
        for value in ['true', '1', 'yes', 'TRUE', 'True']:
            response = self.client.get(self.scrape_url, {
                'keyword': 'cat',
                'sort_by_price': value,
                'page': '0'
            })
            self.assertEqual(response.status_code, 200)
            mock_scraper.scrape_products.assert_called_with(
                keyword='cat',
                sort_by_price=True,
                page=0
            )
        
        # Test various falsy values
        for value in ['false', '0', 'no', 'FALSE', 'False', 'random']:
            response = self.client.get(self.scrape_url, {
                'keyword': 'cat',
                'sort_by_price': value,
                'page': '0'
            })
            self.assertEqual(response.status_code, 200)
            mock_scraper.scrape_products.assert_called_with(
                keyword='cat',
                sort_by_price=False,
                page=0
            )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_default_parameters(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat'
        })
        
        self.assertEqual(response.status_code, 200)
        # Should default to sort_by_price=True and page=0
        mock_scraper.scrape_products.assert_called_with(
            keyword='cat',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scraper_failure(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.products = []
        mock_result.error_message = "Unable to connect to website"
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_message'], "Unable to connect to website")
        self.assertEqual(len(response_data['products']), 0)
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_unexpected_exception(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        # Make the scraper raise an exception
        mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Internal server error occurred')
    
    def test_post_method_not_allowed(self):
        response = self.client.post(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 405) 
    
    def test_put_method_not_allowed(self):
        response = self.client.put(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 405)
    
    def test_delete_method_not_allowed(self):
        response = self.client.delete(self.scrape_url)
        
        self.assertEqual(response.status_code, 405)  
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_keyword_with_special_characters(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat & dog',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='cat & dog',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_large_page_number(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '999'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='cat',
            sort_by_price=True,
            page=999
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_negative_page_number(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '-1'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='cat',
            sort_by_price=True,
            page=-1
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_zero_page_number(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='cat',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_factory_exception_handling(self, mock_create_scraper):
        mock_create_scraper.side_effect = Exception("Factory error")
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Internal server error occurred')
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_json_response_structure_with_products(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        # Create mock product with all attributes
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 1000
        mock_product.url = "https://example.com/product"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://example.com/search"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat'
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
        self.assertEqual(product['price'], 1000)
        self.assertEqual(product['url'], "https://example.com/product")