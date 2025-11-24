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
        mock_product.category = "General"
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
        mock_product.price = 11000  # 10% increase - below 15% threshold, so it auto-updates
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_product.category = "General"
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
        # 10% increase - below anomaly threshold, so price DOES update
        self.assertEqual(response_data['updated'], 1)
        self.assertEqual(response_data['inserted'], 0)
        # No anomaly since change is < 15%
        self.assertEqual(response_data['anomaly_count'], 0)
    
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
        mock_product.category = "General"
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
        self.assertEqual(saved_product.location, "BANJARMASIN SUTOYO, BANJARMASIN KM")
    
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
        mock_product.category = "General"
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
        mock_product.category = "General"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        data = {'keyword': 'test', 'use_price_update': False}
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 200)
        
        saved_product = GemilangProduct.objects.first()
        self.assertIsNotNone(saved_product)
        # Strip "GEMILANG - " prefix from stores for comparison
        stores_without_prefix = [s.replace("GEMILANG - ", "") for s in stores]
        expected_location = ", ".join(stores_without_prefix)
        self.assertEqual(saved_product.location, expected_location)
        
        for store in stores_without_prefix:
            self.assertIn(store, saved_product.location)

    # Tests for 100% views.py coverage
    @patch('api.gemilang.security.AccessControlManager')
    def test_validate_api_token_calls_access_manager(self, mock_manager_class):
        """Test lines 24-29: _validate_api_token function"""
        from api.gemilang.views import _validate_api_token
        from django.http import HttpRequest
        
        mock_manager = MagicMock()
        mock_manager.validate_token.return_value = (True, None)
        mock_manager_class.return_value = mock_manager
        
        request = HttpRequest()
        is_valid, error_msg = _validate_api_token(request)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
        mock_manager.validate_token.assert_called_once_with(request)

    def test_clean_location_name_with_prefix(self):
        """Test line 35: _clean_location_name when location starts with GEMILANG"""
        from api.gemilang.views import _clean_location_name
        
        result = _clean_location_name("GEMILANG - Store 1")
        self.assertEqual(result, "Store 1")
        
        result_no_prefix = _clean_location_name("Store 2")
        self.assertEqual(result_no_prefix, "Store 2")

    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_validate_params_invalid_sort_by_price(self, mock_create_scraper):
        """Test line 189: Invalid sort_by_price validation"""
        data = {
            'keyword': 'test',
            'sort_by_price': 'invalid_value',  # Will fail validation
            'page': 0,
            'use_price_update': False
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)

    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_validate_params_invalid_use_price_update(self, mock_create_scraper):
        """Test line 196: Invalid use_price_update validation"""
        data = {
            'keyword': 'test',
            'sort_by_price': True,
            'page': 0,
            'use_price_update': 'invalid_value'  # Will fail validation
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)

    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_validate_products_business_logic_invalid(self, mock_create_scraper):
        """Test line 211: Business logic validation failure"""
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error_message = None
        
        # Create product with invalid data for business logic
        mock_product = MagicMock()
        mock_product.name = "X"  # Too short, will fail validation
        mock_product.price = 10000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_product.category = "General"
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
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)

    @patch('api.gemilang.views.GemilangDatabaseService')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_handle_price_update_save_failure(self, mock_create_scraper, mock_db_service_class):
        """Test line 220: Price update save failure"""
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error_message = None
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_product.category = "General"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        # Mock database service to return failure
        mock_db_service = MagicMock()
        mock_db_service.save_with_price_update.return_value = {
            'success': False,
            'error': 'Database error',
            'saved': 0,
            'updated': 0,
            'inserted': 0
        }
        mock_db_service_class.return_value = mock_db_service
        
        data = {
            'keyword': 'test',
            'sort_by_price': True,
            'page': 0,
            'use_price_update': True
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error'], 'Database error')

    @patch('api.gemilang.views.GemilangDatabaseService')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_handle_regular_save_tuple_return(self, mock_create_scraper, mock_db_service_class):
        """Test lines 247-248: Regular save returns tuple"""
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error_message = None
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_product.category = "General"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        # Mock database service to return tuple (False, error_message)
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = (False, "Custom error message")
        mock_db_service_class.return_value = mock_db_service
        
        data = {
            'keyword': 'test',
            'sort_by_price': True,
            'page': 0,
            'use_price_update': False
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error'], 'Custom error message')

    @patch('api.gemilang.views.GemilangDatabaseService')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_handle_regular_save_non_tuple_failure(self, mock_create_scraper, mock_db_service_class):
        """Test line 260: Regular save returns non-tuple False"""
        mock_scraper = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error_message = None
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com/product"
        mock_product.unit = "PCS"
        mock_product.category = "General"
        mock_result.products = [mock_product]
        
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        # Mock database service to return just False (not a tuple)
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = False
        mock_db_service_class.return_value = mock_db_service
        
        data = {
            'keyword': 'test',
            'sort_by_price': True,
            'page': 0,
            'use_price_update': False
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error'], 'Failed to save products to database')

    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_fetch_store_locations_failure(self, mock_create_location_scraper):
        """Test lines 286-287: Location scraping failure returns empty string"""
        from api.gemilang.views import _fetch_store_locations
        
        mock_location_scraper = MagicMock()
        mock_location_result = MagicMock()
        mock_location_result.success = False
        mock_location_result.error_message = "Network error"
        mock_location_result.locations = None
        
        mock_location_scraper.scrape_locations.return_value = mock_location_result
        mock_create_location_scraper.return_value = mock_location_scraper
        
        result = _fetch_store_locations()
        
        self.assertEqual(result, "")

    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_and_save_generic_exception(self, mock_create_scraper):
        """Test line 374: Generic exception handling"""
        mock_scraper = MagicMock()
        mock_scraper.scrape_products.side_effect = RuntimeError("Unexpected error")
        mock_create_scraper.return_value = mock_scraper
        
        data = {
            'keyword': 'test',
            'sort_by_price': True,
            'page': 0,
            'use_price_update': False
        }
        
        response = self._post_with_token(data)
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertIn('Internal server error', response_data['error'])



    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_popularity_exception(self, mock_create_scraper):
        """Test lines 407-409: scrape_popularity exception handling"""
        mock_scraper = MagicMock()
        mock_scraper.scrape_products.side_effect = ValueError("Unexpected error")
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape-popularity/', {
            'keyword': 'test',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertIn('Internal server error', response_data['error'])

    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_fetch_store_locations_empty_list(self, mock_location_scraper):
        """Test lines 286-287: _fetch_store_locations when locations list is empty"""
        mock_scraper_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.locations = []  # Empty list - triggers lines 286-287
        mock_scraper_instance.scrape_locations.return_value = mock_result
        mock_location_scraper.return_value = mock_scraper_instance

        # Test the internal function directly
        from api.gemilang.views import _fetch_store_locations
        result = _fetch_store_locations()

        self.assertEqual(result, "")
        mock_scraper_instance.scrape_locations.assert_called_once()


