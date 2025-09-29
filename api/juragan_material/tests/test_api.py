import json
from django.test import TestCase, Client
from unittest.mock import patch, Mock
from api.interfaces import ScrapingResult, Product


class TestJuraganMaterialAPI(TestCase):
    def setUp(self):
        self.client = Client()
        
    def test_juragan_material_scrape_endpoint_exists(self):
        response = self.client.get('/api/juragan_material/scrape/')
        self.assertNotEqual(response.status_code, 404)
        
    def test_juragan_material_scrape_missing_keyword_returns_400(self):
        response = self.client.get('/api/juragan_material/scrape/')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Keyword parameter is required')

    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_juragan_material_scrape_success(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_products = [
            Product(name="Semen Holcim 40Kg", price=60500, url="/products/semen-holcim-40kg"),
            Product(name="Pasir Bangunan", price=120000, url="/products/pasir-bangunan-murah")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://juraganmaterial.id/produk?keyword=semen"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/juragan_material/scrape/', {'keyword': 'semen'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['products']), 2)
        self.assertEqual(data['products'][0]['name'], "Semen Holcim 40Kg")
        self.assertEqual(data['products'][0]['price'], 60500)
        self.assertEqual(data['products'][0]['url'], "/products/semen-holcim-40kg")
        self.assertEqual(data['url'], "https://juraganmaterial.id/produk?keyword=semen")
        self.assertIsNone(data['error_message'])
        
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0
        )

    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_juragan_material_scrape_with_optional_parameters(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(
            products=[],
            success=True,
            url="https://juraganmaterial.id/produk"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/juragan_material/scrape/', {
            'keyword': 'besi',
            'sort_by_price': 'false',
            'page': '2'
        })
        
        self.assertEqual(response.status_code, 200)
        
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='besi',
            sort_by_price=False,
            page=2
        )

    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_juragan_material_scrape_failure(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(
            products=[],
            success=False,
            error_message="Connection timeout occurred"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/juragan_material/scrape/', {'keyword': 'semen'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['error_message'], "Connection timeout occurred")
        self.assertEqual(data['products'], [])

    def test_juragan_material_scrape_invalid_page_parameter(self):
        response = self.client.get('/api/juragan_material/scrape/', {
            'keyword': 'semen',
            'page': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Page parameter must be a valid integer')
        
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_juragan_material_scrape_exception_handling(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/juragan_material/scrape/', {'keyword': 'semen'})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Internal server error occurred')

    def test_post_method_not_allowed(self):
        response = self.client.post('/api/juragan_material/scrape/', {'keyword': 'semen'})
        self.assertEqual(response.status_code, 405)
        
    def test_empty_keyword_returns_400(self):
        response = self.client.get('/api/juragan_material/scrape/', {'keyword': ''})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Keyword parameter is required')
        
    def test_whitespace_only_keyword_returns_400(self):
        response = self.client.get('/api/juragan_material/scrape/', {'keyword': '   '})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Keyword parameter is required')

    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_negative_page_parameter(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True)
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/juragan_material/scrape/', {
            'keyword': 'semen',
            'page': '-1'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=-1
        )

    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
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
                response = self.client.get('/api/juragan_material/scrape/', {
                    'keyword': 'semen',
                    'sort_by_price': sort_value
                })
                
                self.assertEqual(response.status_code, 200)
                mock_scraper.scrape_products.assert_called_once_with(
                    keyword='semen',
                    sort_by_price=expected,
                    page=0
                )

    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_keyword_with_leading_trailing_spaces(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True)
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/juragan_material/scrape/', {
            'keyword': '  semen keyword  '
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen keyword',
            sort_by_price=True,
            page=0
        )