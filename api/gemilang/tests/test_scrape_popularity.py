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
    def test_popularity_exception_returns_500(self, mock_create_scraper):
        mock_scraper = Mock()
        mock_scraper.scrape_products.side_effect = Exception('boom')
        mock_create_scraper.return_value = mock_scraper

        response = self.client.get('/api/gemilang/scrape-popularity/', {'keyword': 'test'})
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Internal server error occurred')