import json
from django.test import TestCase, Client
from unittest.mock import patch, Mock
from api.interfaces import ScrapingResult, Product


class TestGemilangScrapePopularity(TestCase):
    def setUp(self):
        self.client = Client()

    def test_popularity_missing_keyword_returns_400(self):
        response = self.client.get('/api/gemilang/scrape-popularity/')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Keyword is required')

    def test_popularity_negative_page_returns_400(self):
        response = self.client.get('/api/gemilang/scrape-popularity/', {
            'keyword': 'test',
            'page': '-1'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_popularity_success_calls_scraper_with_sort_new(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_products = [
            Product(name='P1', price=1000, url='/p1'),
            Product(name='P2', price=2000, url='/p2')
        ]
        mock_result = ScrapingResult(products=mock_products, success=True, url='https://example.com')
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper

        response = self.client.get('/api/gemilang/scrape-popularity/', {
            'keyword': 'test',
            'page': '2'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['products']), 2)
        # ensure sort_by_price was set to False for popularity (i.e., sort=new)
        mock_scraper.scrape_products.assert_called_once_with(keyword='test', sort_by_price=False, page=2)

    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_popularity_exception_returns_500(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_scraper.scrape_products.side_effect = Exception('boom')
        mock_create_scraper.return_value = mock_scraper

        response = self.client.get('/api/gemilang/scrape-popularity/', {'keyword': 'test'})
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Internal server error occurred')
