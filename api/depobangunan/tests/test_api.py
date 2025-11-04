

from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json



# Helper functions (single definition)
def create_mock_product(name, price, url, unit):
    product = MagicMock()
    product.name = name
    product.price = price
    product.url = url
    product.unit = unit
    return product

def create_mock_scraper(success=True, products=None, error_message=None, url="https://test.url"):
    mock_scraper = MagicMock()
    mock_result = MagicMock()
    mock_result.success = success
    mock_result.products = products or []
    mock_result.error_message = error_message
    mock_result.url = url
    mock_scraper.scrape_products.return_value = mock_result
    return mock_scraper

def create_mock_location(name, code):
    location = MagicMock()
    location.name = name
    location.code = code
    return location

def assert_json_response(testcase, response, expected_status=200):
    testcase.assertEqual(response.status_code, expected_status)
    testcase.assertEqual(response['Content-Type'], 'application/json')
    return json.loads(response.content)

def create_mock_db_service(save_return=True, side_effect=None):
    mock_db_service = MagicMock()
    mock_db_service.save.return_value = save_return
    if side_effect:
        mock_db_service.save.side_effect = side_effect
    return mock_db_service


class DepoBangunanAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.scrape_url = reverse('depobangunan:scrape_products')
    
    def test_scrape_url_resolves_correctly(self):
        self.assertEqual(self.scrape_url, '/api/depobangunan/scrape/')
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_successful_scrape_with_products(self, mock_create_scraper):
        products = [
            create_mock_product("Test Product 1", 5000, "https://www.depobangunan.co.id/test-product-1", "PCS"),
            create_mock_product("Test Product 2", 7500, "https://www.depobangunan.co.id/test-product-2", "KG"),
        ]
        mock_create_scraper.return_value = create_mock_scraper(products=products, url="https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high")
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        response_data = assert_json_response(self, response)
        self.assertTrue(response_data['success'])
        self.assertIsNone(response_data['error_message'])
        self.assertEqual(len(response_data['products']), 2)
        for i, prod in enumerate(products):
            self.assertEqual(response_data['products'][i]['name'], prod.name)
            self.assertEqual(response_data['products'][i]['price'], prod.price)
            self.assertEqual(response_data['products'][i]['url'], prod.url)
        self.assertEqual(response_data['url'], "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high")
        mock_create_scraper.return_value.scrape_products.assert_called_once_with(
            keyword='cat',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_successful_scrape_with_no_products(self, mock_create_scraper):
        mock_scraper = create_mock_scraper(products=[], url="https://www.depobangunan.co.id/catalogsearch/result/?q=nonexistent")
        mock_create_scraper.return_value = mock_scraper
        response = self.client.get(self.scrape_url, {
            'keyword': 'nonexistent',
            'sort_by_price': 'true',
            'page': '0'
        })
        response_data = assert_json_response(self, response)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertIsNone(response_data['error_message'])
    
    def run_error_response_test(self, url, method, data, expected_status, expected_error):
        response = getattr(self.client, method)(url, data)
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], expected_error)

    def test_keyword_error_responses(self):
        cases = [
            ({'sort_by_price': 'true', 'page': '0'}, 400, 'Keyword parameter is required'),
            ({'keyword': '', 'sort_by_price': 'true', 'page': '0'}, 400, 'Keyword parameter is required'),
            ({'keyword': '   ', 'sort_by_price': 'true', 'page': '0'}, 400, 'Keyword parameter is required'),
            ({'keyword': 'cat', 'sort_by_price': 'true', 'page': 'invalid'}, 400, 'Page parameter must be a valid integer'),
        ]
        for data, status, error in cases:
            with self.subTest(data=data):
                self.run_error_response_test(self.scrape_url, 'get', data, status, error)
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_sort_by_price_parameter_variations(self, mock_create_scraper):
        mock_scraper = create_mock_scraper()
        mock_create_scraper.return_value = mock_scraper
        truthy = ['true', '1', 'yes', 'TRUE', 'True']
        falsy = ['false', '0', 'no', 'FALSE', 'False', 'random']
        for value in truthy:
            with self.subTest(sort_by_price=value):
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
        for value in falsy:
            with self.subTest(sort_by_price=value):
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
        mock_scraper = create_mock_scraper(success=False, products=[], error_message="Unable to connect to website", url="https://www.depobangunan.co.id/test")
        mock_create_scraper.return_value = mock_scraper
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        response_data = assert_json_response(self, response)
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
    
    def test_method_not_allowed(self):
        cases = [
            ('post', self.scrape_url, {'keyword': 'cat', 'sort_by_price': 'true', 'page': '0'}),
            ('put', self.scrape_url, {'keyword': 'cat', 'sort_by_price': 'true', 'page': '0'}),
            ('delete', self.scrape_url, {}),
        ]
        for method, url, data in cases:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, data)
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
        mock_product = create_mock_product("Test Product", 1000, "https://example.com/product", "KG")
        mock_scraper = create_mock_scraper(products=[mock_product], url="https://example.com/search")
        mock_create_scraper.return_value = mock_scraper
        response = self.client.get(self.scrape_url, {
            'keyword': 'cat'
        })
        response_data = assert_json_response(self, response)
        self.assertIn('success', response_data)
        self.assertIn('products', response_data)
        self.assertIn('error_message', response_data)
        self.assertIn('url', response_data)
        self.assertEqual(len(response_data['products']), 1)
        product = response_data['products'][0]
        self.assertIn('name', product)
        self.assertIn('price', product)
        self.assertIn('url', product)
        self.assertEqual(product['name'], "Test Product")
        self.assertEqual(product['price'], 1000)
        self.assertEqual(product['url'], "https://example.com/product")


class TestDepoBangunanLocationAPI(TestCase):
    """Test cases for Depo Bangunan location API endpoint"""
    
    def setUp(self):
        self.client = Client()
        
    def test_depobangunan_locations_endpoint_exists(self):
        """Test that the locations endpoint exists"""
        response = self.client.get('/api/depobangunan/locations/')
        self.assertNotEqual(response.status_code, 404)
        
    @patch('api.depobangunan.views.create_depo_location_scraper')
    def test_depobangunan_locations_success(self, mock_create_scraper):
        """Test successful location scraping"""
        from api.interfaces import LocationScrapingResult
        mock_scraper = MagicMock()
        mock_locations = [
            create_mock_location("Depo Bangunan - Kalimalang", "Jl. Raya Kalimalang No.46, Duren Sawit, Kec. Duren Sawit, Timur, Daerah Khusus Ibukota Jakarta 13440"),
            create_mock_location("Depo Bangunan - Tangerang Selatan", "Jl. Raya Serpong No.KM.2, Pakulonan, Kec. Serpong Utara, Kota Tangerang Selatan, Banten 15325")
        ]
        mock_result = LocationScrapingResult(
            locations=mock_locations,
            success=True,
            error_message=None
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        response = self.client.get('/api/depobangunan/locations/')
        response_data = assert_json_response(self, response)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['locations']), 2)
        for i, loc in enumerate(mock_locations):
            self.assertEqual(response_data['locations'][i]['name'], loc.name)
            self.assertIn(loc.code.split()[0], response_data['locations'][i]['code'])
        self.assertIsNone(response_data['error_message'])
        mock_scraper.scrape_locations.assert_called_once_with(timeout=30)
        
    @patch('api.depobangunan.views.create_depo_location_scraper')
    def test_depobangunan_locations_scraper_error(self, mock_create_scraper):
        """Test handling of scraper errors"""
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = MagicMock()
        
        mock_result = LocationScrapingResult(
            locations=[],
            success=False,
            error_message="Failed to fetch location data"
        )
        
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/depobangunan/locations/')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['locations'], [])
        self.assertEqual(response_data['error_message'], "Failed to fetch location data")
        
    @patch('api.depobangunan.views.create_depo_location_scraper')
    def test_depobangunan_locations_with_custom_timeout(self, mock_create_scraper):
        """Test location scraping with custom timeout"""
        from api.interfaces import LocationScrapingResult
        mock_scraper = MagicMock()
        mock_result = LocationScrapingResult(
            locations=[],
            success=True,
            error_message=None
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        for timeout in [60, 9999, -10]:
            with self.subTest(timeout=timeout):
                response = self.client.get('/api/depobangunan/locations/', {'timeout': str(timeout)})
                self.assertEqual(response.status_code, 200)
                mock_scraper.scrape_locations.assert_called_with(timeout=timeout)
        
    @patch('api.depobangunan.views.create_depo_location_scraper')
    def test_depobangunan_locations_invalid_timeout(self, mock_create_scraper):
        """Test handling of invalid timeout parameter"""
        response = self.client.get('/api/depobangunan/locations/', {'timeout': 'invalid'})
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Timeout parameter must be a valid integer')
        
    @patch('api.depobangunan.views.create_depo_location_scraper')
    def test_depobangunan_locations_exception_handling(self, mock_create_scraper):
        """Test handling of unexpected exceptions"""
        mock_scraper = MagicMock()
        mock_scraper.scrape_locations.side_effect = Exception("Unexpected error")
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/depobangunan/locations/')
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Internal server error occurred')

    def test_depobangunan_locations_post_method_not_allowed(self):
        response = self.client.post('/api/depobangunan/locations/')
        self.assertEqual(response.status_code, 405)

    @patch('api.depobangunan.views.create_depo_location_scraper')
    def test_depobangunan_locations_empty_response(self, mock_create_scraper):
        """Test handling of empty location list"""
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = MagicMock()
        
        mock_result = LocationScrapingResult(
            locations=[],
            success=True,
            error_message=None
        )
        
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/depobangunan/locations/')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['locations']), 0)

    @patch('api.depobangunan.views.create_depo_location_scraper')
    def test_depobangunan_locations_large_timeout_value(self, mock_create_scraper):
        """Test handling of large timeout values"""
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = MagicMock()
        
        mock_result = LocationScrapingResult(
            locations=[],
            success=True,
            error_message=None
        )
        
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/depobangunan/locations/', {'timeout': '9999'})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_locations.assert_called_once_with(timeout=9999)

    @patch('api.depobangunan.views.create_depo_location_scraper')
    def test_depobangunan_locations_negative_timeout(self, mock_create_scraper):
        """Test handling of negative timeout values"""
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = MagicMock()
        
        mock_result = LocationScrapingResult(
            locations=[],
            success=True,
            error_message=None
        )
        
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/depobangunan/locations/', {'timeout': '-10'})
        
        self.assertEqual(response.status_code, 200)
        # Negative timeout should be passed as-is; scraper will validate it
        mock_scraper.scrape_locations.assert_called_once_with(timeout=-10)
