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
        self.assertEqual(data['error'], 'Keyword parameter is required')
        
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
        self.assertEqual(data['error'], 'Page parameter must be a valid integer')
        
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
        self.assertEqual(data['error'], 'Keyword parameter is required')
        
    def test_whitespace_only_keyword_returns_400(self):
        response = self.client.get('/api/gemilang/scrape/', {'keyword': '   '})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Keyword parameter is required')
        
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
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test',
            sort_by_price=True,
            page=-1
        )
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_sort_by_price_variations(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True)
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
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
                mock_scraper.reset_mock()
                response = self.client.get('/api/gemilang/scrape/', {
                    'keyword': 'test',
                    'sort_by_price': sort_value
                })
                
                self.assertEqual(response.status_code, 200)
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
                store_name="GEMILANG - BANJARMASIN KM",
                address="Jl. Kampung Melayu Darat 39A Rt.8\nBanjarmasin, Kalimantan Selatan\nIndonesia"
            ),
            Location(
                store_name="GEMILANG - JAKARTA PUSAT", 
                address="Jl. Veteran No. 123\nJakarta Pusat, DKI Jakarta\nIndonesia"
            )
        ]
        mock_result = LocationScrapingResult(
            locations=mock_locations,
            success=True,
            url="https://gemilang-store.com/pusat/store-locations"
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['locations']), 2)
        self.assertEqual(data['locations'][0]['store_name'], "GEMILANG - BANJARMASIN KM")
        self.assertEqual(data['locations'][0]['address'], "Jl. Kampung Melayu Darat 39A Rt.8\nBanjarmasin, Kalimantan Selatan\nIndonesia")
        self.assertEqual(data['locations'][1]['store_name'], "GEMILANG - JAKARTA PUSAT")
        self.assertEqual(data['url'], "https://gemilang-store.com/pusat/store-locations")
        self.assertIsNone(data['error_message'])
        
        mock_scraper.scrape_locations.assert_called_once_with(timeout=30)
        
    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_scraper_error(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = Mock()
        mock_result = LocationScrapingResult(
            locations=[],
            success=False,
            error_message="Connection timeout",
            url="https://gemilang-store.com/pusat/store-locations"
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
            success=True,
            url="https://gemilang-store.com/pusat/store-locations"
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
            success=True,
            url="https://gemilang-store.com/pusat/store-locations"
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/', {'timeout': 'invalid'})
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_locations.assert_called_once_with(timeout=30)
        
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
            url="https://gemilang-store.com/pusat/store-locations"
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
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_locations.assert_called_once_with(timeout=999999)

    @patch('api.gemilang.views.create_gemilang_location_scraper')
    def test_gemilang_locations_negative_timeout(self, mock_create_scraper):
        from api.interfaces import LocationScrapingResult
        
        mock_scraper = Mock()
        mock_result = LocationScrapingResult(locations=[], success=True)
        mock_scraper.scrape_locations.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/locations/', {'timeout': '-10'})
        
        self.assertEqual(response.status_code, 200)
        # Negative timeout is clamped to 0 by max(0, timeout) in parse_timeout
        mock_scraper.scrape_locations.assert_called_once_with(timeout=0)