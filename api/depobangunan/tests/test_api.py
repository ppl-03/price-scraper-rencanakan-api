
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json

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

def assert_json_response(testcase, response, expected_status=200):
    testcase.assertEqual(response.status_code, expected_status)
    testcase.assertEqual(response['Content-Type'], 'application/json')
    return json.loads(response.content)


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
        self.assertEqual(response_data['products'][0]['name'], "Test Product 1")
        self.assertEqual(response_data['products'][0]['price'], 5000)
        self.assertEqual(response_data['products'][0]['url'], "https://www.depobangunan.co.id/test-product-1")
        self.assertEqual(response_data['products'][1]['name'], "Test Product 2")
        self.assertEqual(response_data['products'][1]['price'], 7500)
        self.assertEqual(response_data['products'][1]['url'], "https://www.depobangunan.co.id/test-product-2")
        self.assertEqual(response_data['url'], "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high")
        mock_create_scraper.return_value.scrape_products.assert_called_once_with(
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
        mock_product.unit = "KG"  # Add proper unit attribute
        
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
        from api.interfaces import LocationScrapingResult, Location
        
        mock_scraper = MagicMock()
        
        mock_locations = [
            Location(
                name="Depo Bangunan - Kalimalang",
                code="Jl. Raya Kalimalang No.46, Duren Sawit, Kec. Duren Sawit, Timur, Daerah Khusus Ibukota Jakarta 13440"
            ),
            Location(
                name="Depo Bangunan - Tangerang Selatan",
                code="Jl. Raya Serpong No.KM.2, Pakulonan, Kec. Serpong Utara, Kota Tangerang Selatan, Banten 15325"
            )
        ]
        
        mock_result = LocationScrapingResult(
            locations=mock_locations,
            success=True,
            error_message=None
        )
        
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/depobangunan/locations/')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['locations']), 2)
        
        # Check first location
        self.assertEqual(response_data['locations'][0]['name'], "Depo Bangunan - Kalimalang")
        self.assertIn("Jl. Raya Kalimalang", response_data['locations'][0]['code'])
        
        # Check second location
        self.assertEqual(response_data['locations'][1]['name'], "Depo Bangunan - Tangerang Selatan")
        self.assertIn("Jl. Raya Serpong", response_data['locations'][1]['code'])
        
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
        
        response = self.client.get('/api/depobangunan/locations/', {'timeout': '60'})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_locations.assert_called_once_with(timeout=60)
        
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
        """Test that POST method is not allowed"""
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


class TestDepoBangunanScrapeAndSaveAPI(TestCase):
    """Test cases for Depo Bangunan scrape-and-save API endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.scrape_and_save_url = reverse('depobangunan:scrape_and_save_products')
    
    def test_scrape_and_save_url_resolves_correctly(self):
        """Test that the URL resolves correctly"""
        self.assertEqual(self.scrape_and_save_url, '/api/depobangunan/scrape-and-save/')
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_successful_scrape_and_save(self, mock_create_scraper, mock_db_service_class):
        """Test successful scraping and saving of products"""
        # Mock the scraper
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        # Create mock products
        mock_product1 = MagicMock()
        mock_product1.name = "Test Product 1"
        mock_product1.price = 5000
        mock_product1.url = "https://www.depobangunan.co.id/test-product-1"
        mock_product1.unit = "PCS"
        
        mock_product2 = MagicMock()
        mock_product2.name = "Test Product 2"
        mock_product2.price = 7500
        mock_product2.url = "https://www.depobangunan.co.id/test-product-2"
        mock_product2.unit = "KG"
        
        # Mock scraping result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product1, mock_product2]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/catalogsearch/result/?q=semen"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        # Mock database service
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = True
        mock_db_service_class.return_value = mock_db_service
        
        # Make the API call
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message'], 'Products scraped and saved successfully')
        self.assertEqual(response_data['scraped_count'], 2)
        self.assertEqual(response_data['saved_count'], 2)
        self.assertEqual(response_data['url'], "https://www.depobangunan.co.id/catalogsearch/result/?q=semen")
        
        # Verify scraper was called correctly
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0
        )
        
        # Verify database save was called
        mock_db_service.save.assert_called_once()
        saved_data = mock_db_service.save.call_args[0][0]
        self.assertEqual(len(saved_data), 2)
        self.assertEqual(saved_data[0]['name'], 'Test Product 1')
        self.assertEqual(saved_data[1]['name'], 'Test Product 2')
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_no_products_found(self, mock_create_scraper):
        """Test handling when no products are found"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = []
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/catalogsearch/result/?q=nonexistent"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'nonexistent',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message'], 'No products found to save')
        self.assertEqual(response_data['scraped_count'], 0)
        self.assertEqual(response_data['saved_count'], 0)
    
    def test_scrape_and_save_missing_keyword(self):
        """Test error when keyword parameter is missing"""
        response = self.client.post(self.scrape_and_save_url, {
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Keyword parameter is required')
    
    def test_scrape_and_save_empty_keyword(self):
        """Test error when keyword is empty"""
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': '',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Keyword parameter is required')
    
    def test_scrape_and_save_whitespace_keyword(self):
        """Test error when keyword is only whitespace"""
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': '   ',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Keyword parameter is required')
    
    def test_scrape_and_save_invalid_page_parameter(self):
        """Test error when page parameter is not a valid integer"""
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_by_price': 'true',
            'page': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Page parameter must be a valid integer')
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_scraping_failure(self, mock_create_scraper):
        """Test handling when scraping fails"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.products = []
        mock_result.error_message = "Failed to connect to website"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Scraping failed: Failed to connect to website')
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_database_save_failure(self, mock_create_scraper, mock_db_service_class):
        """Test handling when database save fails"""
        # Mock scraper
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 5000
        mock_product.url = "https://www.depobangunan.co.id/test-product"
        mock_product.unit = "PCS"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        # Mock database service to return False (save failed)
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = False
        mock_db_service_class.return_value = mock_db_service
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Failed to save products to database')
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_unexpected_exception(self, mock_create_scraper):
        """Test handling of unexpected exceptions"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        # Make scraper raise an exception
        mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Internal server error occurred')
    
    def test_scrape_and_save_get_method_not_allowed(self):
        """Test that GET method is not allowed"""
        response = self.client.get(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 405)
    
    def test_scrape_and_save_put_method_not_allowed(self):
        """Test that PUT method is not allowed"""
        response = self.client.put(self.scrape_and_save_url)
        
        self.assertEqual(response.status_code, 405)
    
    def test_scrape_and_save_delete_method_not_allowed(self):
        """Test that DELETE method is not allowed"""
        response = self.client.delete(self.scrape_and_save_url)
        
        self.assertEqual(response.status_code, 405)
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_default_parameters(self, mock_create_scraper, mock_db_service_class):
        """Test that default parameters are used correctly"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 5000
        mock_product.url = "https://www.depobangunan.co.id/test"
        mock_product.unit = "PCS"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = True
        mock_db_service_class.return_value = mock_db_service
        
        # Call with only keyword (defaults: sort_by_price=true, page=0)
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify defaults were used
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_sort_by_price_variations(self, mock_create_scraper, mock_db_service_class):
        """Test various truthy and falsy values for sort_by_price"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 5000
        mock_product.url = "https://www.depobangunan.co.id/test"
        mock_product.unit = "PCS"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = True
        mock_db_service_class.return_value = mock_db_service
        
        # Test truthy values
        for value in ['true', '1', 'yes', 'TRUE', 'True', 'YES']:
            response = self.client.post(self.scrape_and_save_url, {
                'keyword': 'semen',
                'sort_by_price': value,
                'page': '0'
            })
            self.assertEqual(response.status_code, 200)
        
        # Test falsy values
        for value in ['false', '0', 'no', 'FALSE', 'random']:
            response = self.client.post(self.scrape_and_save_url, {
                'keyword': 'semen',
                'sort_by_price': value,
                'page': '0'
            })
            self.assertEqual(response.status_code, 200)
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_with_special_characters_in_keyword(self, mock_create_scraper, mock_db_service_class):
        """Test handling of special characters in keyword"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 5000
        mock_product.url = "https://www.depobangunan.co.id/test"
        mock_product.unit = "PCS"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = True
        mock_db_service_class.return_value = mock_db_service
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen & cat',
            'sort_by_price': 'true',
            'page': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen & cat',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_large_page_number(self, mock_create_scraper, mock_db_service_class):
        """Test handling of large page numbers"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 5000
        mock_product.url = "https://www.depobangunan.co.id/test"
        mock_product.unit = "PCS"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = True
        mock_db_service_class.return_value = mock_db_service
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_by_price': 'true',
            'page': '999'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_with(
            keyword='semen',
            sort_by_price=True,
            page=999
        )
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_response_structure(self, mock_create_scraper, mock_db_service_class):
        """Test the structure of successful response"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 5000
        mock_product.url = "https://www.depobangunan.co.id/test"
        mock_product.unit = "PCS"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        mock_db_service = MagicMock()
        mock_db_service.save.return_value = True
        mock_db_service_class.return_value = mock_db_service
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen'
        })
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Check all required fields are present
        self.assertIn('success', response_data)
        self.assertIn('message', response_data)
        self.assertIn('scraped_count', response_data)
        self.assertIn('saved_count', response_data)
        self.assertIn('url', response_data)
        
        # Check field types
        self.assertIsInstance(response_data['success'], bool)
        self.assertIsInstance(response_data['message'], str)
        self.assertIsInstance(response_data['scraped_count'], int)
        self.assertIsInstance(response_data['saved_count'], int)
        self.assertIsInstance(response_data['url'], str)
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_database_service_exception(self, mock_create_scraper, mock_db_service_class):
        """Test handling when database service raises an exception"""
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 5000
        mock_product.url = "https://www.depobangunan.co.id/test"
        mock_product.unit = "PCS"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.products = [mock_product]
        mock_result.error_message = None
        mock_result.url = "https://www.depobangunan.co.id/test"
        
        mock_scraper.scrape_products.return_value = mock_result
        
        # Make database service raise an exception
        mock_db_service = MagicMock()
        mock_db_service.save.side_effect = Exception("Database connection error")
        mock_db_service_class.return_value = mock_db_service
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen'
        })
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Internal server error occurred')