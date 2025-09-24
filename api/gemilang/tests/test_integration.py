from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
from api.interfaces import IPriceScraper, HttpClientError, Product
from api.gemilang.factory import create_gemilang_scraper
from api.gemilang.scraper import GemilangPriceScraper
from api.gemilang.url_builder import GemilangUrlBuilder
from api.gemilang.html_parser import GemilangHtmlParser
from api.core import BaseHttpClient
from pathlib import Path


class TestGemilangIntegration(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        fixture_path = base / "gemilang_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")
    def setUp(self):
        self.mock_http_client = Mock(spec=BaseHttpClient)
        self.url_builder = GemilangUrlBuilder()
        self.html_parser = GemilangHtmlParser()
        self.scraper = GemilangPriceScraper(
            self.mock_http_client, 
            self.url_builder, 
            self.html_parser
        )
    def test_complete_scraping_pipeline_success(self):
        keyword = "cat"
        self.mock_http_client.get.return_value = self.mock_html
        result = self.scraper.scrape_products(keyword)
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertIsNotNone(result.url)
        self.assertIn("keyword=cat", result.url)
        self.assertIn("sort=price_asc", result.url)
        self.assertEqual(len(result.products), 2)
        product1 = result.products[0]
        self.assertEqual(product1.name, "GML KUAS CAT 1inch")
        self.assertEqual(product1.price, 3600)
        self.assertEqual(product1.url, "/pusat/gml-kuas-cat-1inch")
        product2 = result.products[1]
        self.assertEqual(product2.name, "Cat Tembok Spectrum 5Kg")
        self.assertEqual(product2.price, 55000)
        self.assertEqual(product2.url, "/pusat/cat-tembok-spectrum-5kg")
        self.mock_http_client.get.assert_called_once()
        called_url = self.mock_http_client.get.call_args[0][0]
        self.assertIn("keyword=cat", called_url)
    def test_scraping_with_pagination(self):
        keyword = "semen"
        page = 2
        self.mock_http_client.get.return_value = self.mock_html
        result = self.scraper.scrape_products(keyword, sort_by_price=False, page=page)
        self.assertTrue(result.success)
        self.assertIn("keyword=semen", result.url)
        self.assertIn("page=2", result.url)
        self.assertNotIn("sort=price_asc", result.url)
    def test_scraping_with_http_error(self):
        keyword = "cat"
        self.mock_http_client.get.side_effect = HttpClientError("Connection timeout")
        result = self.scraper.scrape_products(keyword)
        self.assertFalse(result.success)
        self.assertIn("Connection timeout", result.error_message)
        self.assertEqual(len(result.products), 0)
    def test_scraping_with_empty_html(self):
        keyword = "cat"
        self.mock_http_client.get.return_value = ""
        result = self.scraper.scrape_products(keyword)
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 0)
    def test_scraping_with_no_products_found(self):
        keyword = "cat"
        html_no_products = "<html><body><div>No products found</div></body></html>"
        self.mock_http_client.get.return_value = html_no_products
        result = self.scraper.scrape_products(keyword)
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 0)
    def test_invalid_keyword_handling(self):
        result = self.scraper.scrape_products("")
        self.assertFalse(result.success)
        self.assertIn("Keyword cannot be empty", result.error_message)
        result = self.scraper.scrape_products("   ")
        self.assertFalse(result.success)
        self.assertIn("Keyword cannot be empty", result.error_message)
    def test_factory_function(self):
        scraper = create_gemilang_scraper()
        self.assertIsInstance(scraper, IPriceScraper)
        self.assertIsInstance(scraper, GemilangPriceScraper)
        self.assertIsNotNone(scraper.http_client)
        self.assertIsNotNone(scraper.url_builder)
        self.assertIsNotNone(scraper.html_parser)
        self.assertIsInstance(scraper.http_client, BaseHttpClient)
        self.assertIsInstance(scraper.url_builder, GemilangUrlBuilder)
        self.assertIsInstance(scraper.html_parser, GemilangHtmlParser)
    def test_dependency_injection_flexibility(self):
        mock_http_client = Mock()
        mock_http_client.get.return_value = self.mock_html
        mock_url_builder = Mock()
        mock_url_builder.build_search_url.return_value = "https://test.com/search?q=test"
        mock_html_parser = Mock()
        mock_html_parser.parse_products.return_value = [
            Product(name="Test Product", price=100, url="/test")
        ]
        scraper = GemilangPriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        result = scraper.scrape_products("test")
        mock_url_builder.build_search_url.assert_called_once_with("test", True, 0)
        mock_http_client.get.assert_called_once_with("https://test.com/search?q=test")
        mock_html_parser.parse_products.assert_called_once_with(self.mock_html)
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 1)
        self.assertEqual(result.products[0].name, "Test Product")
    def test_error_propagation(self):
        mock_url_builder = Mock()
        mock_url_builder.build_search_url.side_effect = Exception("URL error")
        scraper = GemilangPriceScraper(self.mock_http_client, mock_url_builder, self.html_parser)
        result = scraper.scrape_products("test")
        self.assertFalse(result.success)
        self.assertIn("Unexpected error", result.error_message)
    @patch('api.gemilang.factory.BaseHttpClient')
    @patch('api.gemilang.factory.GemilangUrlBuilder')
    @patch('api.gemilang.factory.GemilangHtmlParser')
    def test_factory_creates_new_instances(self, mock_parser_class, mock_builder_class, mock_client_class):
        mock_client = Mock()
        mock_builder = Mock()
        mock_parser = Mock()
        mock_client_class.return_value = mock_client
        mock_builder_class.return_value = mock_builder
        mock_parser_class.return_value = mock_parser
        scraper = create_gemilang_scraper()
        mock_client_class.assert_called_once()
        mock_builder_class.assert_called_once()
        mock_parser_class.assert_called_once()
        self.assertEqual(scraper.http_client, mock_client)
        self.assertEqual(scraper.url_builder, mock_builder)
        self.assertEqual(scraper.html_parser, mock_parser)
