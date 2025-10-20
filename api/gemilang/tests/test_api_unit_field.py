import json
from django.test import TestCase, Client
from unittest.mock import patch, Mock
from api.interfaces import ScrapingResult, Product


class TestGemilangAPIUnitField(TestCase):
    def setUp(self):
        self.client = Client()
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_response_includes_unit_field(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_products = [
            Product(name="Semen 50kg", price=65000, url="/semen", unit="KG"),
            Product(name="Keramik 40x40", price=45000, url="/keramik", unit="M²")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://example.com"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('unit', data['products'][0])
        self.assertIn('unit', data['products'][1])
        self.assertEqual(data['products'][0]['unit'], "KG")
        self.assertEqual(data['products'][1]['unit'], "M²")
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_response_handles_null_unit(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_products = [
            Product(name="Product without unit", price=10000, url="/product", unit=None)
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://example.com"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('unit', data['products'][0])
        self.assertIsNone(data['products'][0]['unit'])
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_response_preserves_all_fields_with_unit(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_products = [
            Product(name="Complete Product", price=50000, url="/complete", unit="M²")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://example.com"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        data = json.loads(response.content)
        product = data['products'][0]
        
        self.assertEqual(product['name'], "Complete Product")
        self.assertEqual(product['price'], 50000)
        self.assertEqual(product['url'], "/complete")
        self.assertEqual(product['unit'], "M²")
        
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_scrape_multiple_products_all_have_unit_field(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_products = [
            Product(name="Product 1", price=1000, url="/p1", unit="KG"),
            Product(name="Product 2", price=2000, url="/p2", unit="M"),
            Product(name="Product 3", price=3000, url="/p3", unit=None),
            Product(name="Product 4", price=4000, url="/p4", unit="LITER")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://example.com"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        data = json.loads(response.content)
        
        for product in data['products']:
            self.assertIn('unit', product)
