import json
from django.test import TestCase, Client
from unittest.mock import patch, Mock
from api.interfaces import ScrapingResult, Product


class TestGemilangAPI(TestCase):
    def setUp(self):
        self.client = Client()
        
    def test_gemilang_scrape_endpoint_exists(self):
        response = self.client.get('/api/gemilang/scrape/')
        self.assertNotEqual(response.status_code, 404)
        
    def test_gemilang_scrape_missing_keyword_returns_400(self):
        response = self.client.get('/api/gemilang/scrape/')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Validation failed', data['error'])
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_gemilang_scrape_success(self, mock_create_scraper):
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
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
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
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_gemilang_scrape_with_optional_parameters(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(
            products=[],
            success=True,
            url="https://example.com"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {
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
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_gemilang_scrape_failure(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(
            products=[],
            success=False,
            error_message="Network error occurred"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['error_message'], "Network error occurred")
        self.assertEqual(data['products'], [])
        
    def test_gemilang_scrape_invalid_page_parameter(self):
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': 'test',
            'page': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Validation failed')
        self.assertIn('details', data)
        self.assertIn('page', data['details'])
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_gemilang_scrape_exception_handling(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Internal server error occurred')
        
    def test_post_method_not_allowed(self):
        response = self.client.post('/api/gemilang/scrape/', {'keyword': 'test'})
        self.assertEqual(response.status_code, 405)
        
    def test_empty_keyword_returns_400(self):
        response = self.client.get('/api/gemilang/scrape/', {'keyword': ''})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('Validation failed', data['error'])
        
    def test_whitespace_only_keyword_returns_400(self):
        response = self.client.get('/api/gemilang/scrape/', {'keyword': '   '})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('Validation failed', data['error'])
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_negative_page_parameter(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True)
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': 'test',
            'page': '-1'
        })
        
        # Negative page values now fail validation (security requirement)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_sort_by_price_variations(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True)
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        test_cases = [
            ('1', True, 200),
            ('yes', True, 200),
            ('True', True, 200),
            ('false', False, 200),
            ('0', False, 200),
            ('no', False, 200),
            ('invalid', False, 400),  # Invalid values now fail validation
            ('', False, 400)  # Empty values now fail validation
        ]
        
        for sort_value, expected, expected_status in test_cases:
            with self.subTest(sort_value=sort_value, expected=expected):
                mock_scraper.reset_mock()
                response = self.client.get('/api/gemilang/scrape/', {
                    'keyword': 'test',
                    'sort_by_price': sort_value
                })
                
                self.assertEqual(response.status_code, expected_status)
                if expected_status == 200:
                    mock_scraper.scrape_products.assert_called_once_with(
                        keyword='test',
                        sort_by_price=expected,
                        page=0
                    )
                
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_keyword_with_leading_trailing_spaces(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True)
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': '  test keyword  '
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test keyword',
            sort_by_price=True,
            page=0
        )


class TestGemilangLocationAPI(TestCase):
    def setUp(self):
        self.client = Client()
        
    def test_gemilang_locations_endpoint_exists(self):
        response = self.client.get('/api/gemilang/locations/')
        self.assertNotEqual(response.status_code, 404)
        
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_success(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult, Location
        
        mock_scraper = Mock()
        mock_locations = [
            Location(
                name="GEMILANG - BANJARMASIN KM",
                code="Jl. Kampung Melayu Darat 39A Rt.8\nBanjarmasin, Kalimantan Selatan\nIndonesia"
            ),
            Location(
                name="GEMILANG - JAKARTA PUSAT", 
                code="Jl. Veteran No. 123\nJakarta Pusat, DKI Jakarta\nIndonesia"
            )
        ]
        mock_result = LocationScrapingResult(
            locations=mock_locations,
            success=True
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['locations']), 2)
        self.assertEqual(data['locations'][0]['name'], "GEMILANG - BANJARMASIN KM")
        self.assertEqual(data['locations'][0]['code'], "Jl. Kampung Melayu Darat 39A Rt.8\nBanjarmasin, Kalimantan Selatan\nIndonesia")
        self.assertEqual(data['locations'][1]['name'], "GEMILANG - JAKARTA PUSAT")
        self.assertIsNone(data['error_message'])
        
        mock_scraper.scrape_locations.assert_called_once_with(timeout=30)
        
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_scraper_error(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = Mock()
        mock_result = LocationScrapingResult(
            locations=[],
            success=False,
            error_message="Connection timeout"
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(len(data['locations']), 0)
        self.assertEqual(data['error_message'], "Connection timeout")
        
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_with_custom_timeout(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = Mock()
        mock_result = LocationScrapingResult(
            locations=[],
            success=True
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/', {'timeout': '60'})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_locations.assert_called_once_with(timeout=60)
        
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_invalid_timeout(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = Mock()
        mock_result = LocationScrapingResult(
            locations=[],
            success=True
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/', {'timeout': 'invalid'})
        
        # Invalid timeout now fails validation (security requirement)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_exception_handling(self, mock_create_scraper):
        mock_create_scraper.side_effect = Exception("Unexpected error")
        
        response = self.client.get('/api/gemilang/locations/')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(len(data['locations']), 0)
        self.assertIn("Unexpected error", data['error_message'])

    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_post_method_not_allowed(self, mock_create_scraper):
        response = self.client.post('/api/gemilang/locations/')
        self.assertEqual(response.status_code, 405)

    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_empty_response(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = Mock()
        mock_result = LocationScrapingResult(
            locations=[],
            success=True,
            error_message=None,
            attempts_made=1
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['locations']), 0)

    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_large_timeout_value(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = Mock()
        mock_result = LocationScrapingResult(locations=[], success=True)
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/', {'timeout': '999999'})
        
        # Large timeout values now fail validation (max is 120)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_negative_timeout(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = Mock()
        mock_result = LocationScrapingResult(locations=[], success=True)
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/', {'timeout': '0'})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_locations.assert_called_once_with(timeout=0)


class TestGemilangAPIValidation(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_scrape_with_sql_injection_attempt(self):
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': "'; DROP TABLE users; --"
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_scrape_with_xss_attempt(self):
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': "<script>alert('XSS')</script>"
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_scrape_with_long_keyword(self):
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': 'a' * 101
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_scrape_with_invalid_page(self):
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': 'cement',
            'page': 'invalid'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_scrape_with_negative_page(self):
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': 'cement',
            'page': '-1'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_scrape_with_page_exceeds_max(self):
        response = self.client.get('/api/gemilang/scrape/', {
            'keyword': 'cement',
            'page': '101'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_locations_with_timeout_exceeds_max(self):
        response = self.client.get('/api/gemilang/locations/', {
            'timeout': '121'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_locations_with_negative_timeout(self):
        response = self.client.get('/api/gemilang/locations/', {
            'timeout': '-1'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_includes_location_in_response(self, mock_create_scraper, mock_create_location_scraper):
        mock_location_scraper = Mock()
        mock_location_result = Mock()
        mock_location_result.success = True
        
        mock_location1 = Mock()
        mock_location1.name = "GEMILANG - BANJARMASIN SUTOYO"
        mock_location2 = Mock()
        mock_location2.name = "GEMILANG - BANJARMASIN KM"
        mock_location_result.locations = [mock_location1, mock_location2]
        
        mock_location_scraper.scrape_locations.return_value = mock_location_result
        mock_create_location_scraper.return_value = mock_location_scraper
        
        mock_scraper = Mock()
        mock_products = [
            Product(name="Test Product", price=10000, url="/product1", unit="PCS")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://example.com/search"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        mock_create_location_scraper.assert_called_once()
        mock_location_scraper.scrape_locations.assert_called_once_with(timeout=30)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['products']), 1)
        self.assertIn('location', data['products'][0])
        self.assertEqual(data['products'][0]['location'], "BANJARMASIN SUTOYO, BANJARMASIN KM")
    
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_with_location_failure(self, mock_create_scraper, mock_create_location_scraper):
        mock_location_scraper = Mock()
        mock_location_result = Mock()
        mock_location_result.success = False
        mock_location_result.locations = []
        
        mock_location_scraper.scrape_locations.return_value = mock_location_result
        mock_create_location_scraper.return_value = mock_location_scraper
        
        mock_scraper = Mock()
        mock_products = [
            Product(name="Test Product", price=10000, url="/product1", unit="PCS")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://example.com/search"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['products']), 1)
        
        self.assertIn('location', data['products'][0])
        self.assertEqual(data['products'][0]['location'], "")
    
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_with_all_five_stores_in_location(self, mock_create_scraper, mock_create_location_scraper):
        mock_location_scraper = Mock()
        mock_location_result = Mock()
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
            mock_loc = Mock()
            mock_loc.name = store_name
            mock_locations.append(mock_loc)
        
        mock_location_result.locations = mock_locations
        mock_location_scraper.scrape_locations.return_value = mock_location_result
        mock_create_location_scraper.return_value = mock_location_scraper
        
        mock_scraper = Mock()
        mock_products = [
            Product(name="Test Product", price=10000, url="/product1", unit="PCS")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://example.com/search"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        stores_without_prefix = [s.replace("GEMILANG - ", "") for s in stores]
        expected_location = ", ".join(stores_without_prefix)
        self.assertEqual(data['products'][0]['location'], expected_location)
        
        for store in stores_without_prefix:
            self.assertIn(store, data['products'][0]['location'])