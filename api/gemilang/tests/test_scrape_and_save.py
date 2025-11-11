from django.test import TestCase, Client
from db_pricing.models import GemilangProduct
from unittest.mock import patch, MagicMock
import json


class TestScrapeAndSaveEndpoint(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.url = '/api/gemilang/scrape-and-save/'
        self.valid_token = 'dev-token-12345'
    
    def _post_with_token(self, data, token=None):
        token = token or self.valid_token
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_X_API_TOKEN=token
        )
    
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_and_save_success_insert_mode(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error_message = None
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        data = {
            'keyword': 'test',
            'sort_by_price': True,
            'page': 0,
            'use_price_update': False
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['saved'], 1)
        self.assertEqual(response_data['inserted'], 1)
        self.assertEqual(response_data['updated'], 0)
    
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_and_save_with_price_update(self, mock_create_scraper):
        GemilangProduct.objects.create(
            name="Test Product",
            price=10000,
            url="https://test.com/product",
            unit="PCS"
        )
        
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error_message = None
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 12000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        data = {
            'keyword': 'test',
            'use_price_update': True
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['updated'], 1)
        self.assertEqual(response_data['inserted'], 0)
        self.assertEqual(response_data['anomaly_count'], 1)
    
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_and_save_no_products(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        data = {'keyword': 'test'}
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['saved'], 0)
    
    def test_scrape_and_save_missing_keyword(self):
        data = {}
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    def test_scrape_and_save_invalid_json(self):
        response = self.client.post(
            self.url,
            data='invalid json',
            content_type='application/json',
            HTTP_X_API_TOKEN=self.valid_token
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_and_save_scraper_failure(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Scraping failed"
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        data = {'keyword': 'test'}
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
    
    def test_scrape_and_save_missing_token(self):
        data = {'keyword': 'test'}
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'API token required')
    
    def test_scrape_and_save_invalid_token(self):
        data = {'keyword': 'test'}
        response = self._post_with_token(data, token='invalid-token')
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Invalid API token')
    
    def test_scrape_and_save_get_method_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
    
    def test_scrape_and_save_read_only_token_denied(self):
        data = {'keyword': 'test'}
        response = self._post_with_token(data, token='read-only-token')
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertIn('Insufficient permissions', response_data['error'])
    
    def test_scrape_and_save_invalid_keyword_sql_injection(self):
        data = {'keyword': "'; DROP TABLE users; --"}
        response = self._post_with_token(data)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    def test_scrape_and_save_invalid_keyword_xss(self):
        data = {'keyword': "<script>alert('XSS')</script>"}
        response = self._post_with_token(data)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    def test_scrape_and_save_keyword_too_long(self):
        data = {'keyword': 'a' * 101}
        response = self._post_with_token(data)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    def test_scrape_and_save_empty_keyword(self):
        data = {'keyword': ''}
        response = self._post_with_token(data)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    def test_scrape_and_save_invalid_page_negative(self):
        data = {'keyword': 'test', 'page': -1}
        response = self._post_with_token(data)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    def test_scrape_and_save_invalid_page_exceeds_max(self):
        data = {'keyword': 'test', 'page': 101}
        response = self._post_with_token(data)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_and_save_with_location_success(self, mock_create_scraper, mock_create_location_scraper):
        mock_location_scraper = MagicMock()
        mock_location_result = MagicMock()
        mock_location_result.success = True
        
        mock_location1 = MagicMock()
        mock_location1.name = "GEMILANG - BANJARMASIN SUTOYO"
        mock_location2 = MagicMock()
        mock_location2.name = "GEMILANG - BANJARMASIN KM"
        mock_location_result.locations = [mock_location1, mock_location2]
        
        mock_location_scraper.scrape_locations.return_value = mock_location_result
        mock_create_location_scraper.return_value = mock_location_scraper
        
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        data = {
            'keyword': 'test',
            'sort_by_price': True,
            'page': 0,
            'use_price_update': False
        }
        
        response = self._post_with_token(data)
        
        mock_create_location_scraper.assert_called_once()
        mock_location_scraper.scrape_locations.assert_called_once_with(timeout=30)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        saved_product = GemilangProduct.objects.first()
        self.assertIsNotNone(saved_product)
        self.assertEqual(saved_product.location, "GEMILANG - BANJARMASIN SUTOYO, GEMILANG - BANJARMASIN KM")
    
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_and_save_location_scraping_fails(self, mock_create_scraper, mock_create_location_scraper):
        mock_location_scraper = MagicMock()
        mock_location_result = MagicMock()
        mock_location_result.success = False
        mock_location_result.locations = []
        
        mock_location_scraper.scrape_locations.return_value = mock_location_result
        mock_create_location_scraper.return_value = mock_location_scraper
        
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        data = {
            'keyword': 'test',
            'use_price_update': False
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        saved_product = GemilangProduct.objects.first()
        self.assertIsNotNone(saved_product)
        self.assertEqual(saved_product.location, "")
    
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_and_save_all_five_stores(self, mock_create_scraper, mock_create_location_scraper):
        mock_location_scraper = MagicMock()
        mock_location_result = MagicMock()
        mock_location_result.success = True
        
        stores = [
            "GEMILANG - BANJARMASIN SUTOYO",
            "GEMILANG - BANJARMASIN KM",
            "GEMILANG - BANJARBARU",
            "GEMILANG - PALANGKARAYA",
            "GEMILANG - PALANGKARAYA KM.8"
        ]
        
        mock_locations = []
        for store_name in stores:
            mock_loc = MagicMock()
            mock_loc.name = store_name
            mock_locations.append(mock_loc)
        
        mock_location_result.locations = mock_locations
        mock_location_scraper.scrape_locations.return_value = mock_location_result
        mock_create_location_scraper.return_value = mock_location_scraper
        
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        data = {'keyword': 'test', 'use_price_update': False}
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 200)
        
        saved_product = GemilangProduct.objects.first()
        self.assertIsNotNone(saved_product)
        expected_location = ", ".join(stores)
        self.assertEqual(saved_product.location, expected_location)
        
        for store in stores:
            self.assertIn(store, saved_product.location)
