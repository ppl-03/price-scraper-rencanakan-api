from unittest import TestCase
from unittest.mock import Mock, patch
from api.interfaces import IPriceScraper, HttpClientError, Product
from api.playwright_client import PlaywrightHttpClient
from api.mitra10.factory import create_mitra10_scraper
from api.mitra10.scraper import Mitra10PriceScraper
from api.mitra10.url_builder import Mitra10UrlBuilder
from api.mitra10.html_parser import Mitra10HtmlParser
from pathlib import Path


class BatchPlaywrightClientHelper:
    """Helper class for setting up BatchPlaywrightClient mocks in integration tests"""
    
    @staticmethod
    def setup_successful_mock(mock_batch_client, return_html):
        """Setup BatchPlaywrightClient mock for successful requests"""
        mock_client_instance = Mock()
        mock_batch_client.return_value.__enter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = return_html
        return mock_client_instance
    
    @staticmethod
    def setup_error_mock(mock_batch_client, error_message="Request timeout after 30s"):
        """Setup BatchPlaywrightClient mock to raise an error"""
        mock_batch_client.return_value.__enter__.side_effect = Exception(error_message)
    
    @staticmethod
    def assert_batch_client_called(mock_batch_client, mock_client_instance, expected_url_fragment):
        """Assert BatchPlaywrightClient was called correctly"""
        mock_batch_client.assert_called_once_with(headless=True)
        mock_client_instance.get.assert_called_once()
        called_url = mock_client_instance.get.call_args[0][0]
        return expected_url_fragment in called_url


class IntegrationTestHelper:
    """Helper class for common integration test operations"""
    
    @staticmethod
    def assert_successful_scraping_result(test_case, result, expected_url_fragment):
        """Assert successful scraping result with common checks"""
        test_case.assertTrue(result.success)
        test_case.assertIsNone(result.error_message)
        test_case.assertIsNotNone(result.url)
        test_case.assertIn(expected_url_fragment, result.url)
        test_case.assertGreater(len(result.products), 0)
        
        # Verify first product structure
        product = result.products[0]
        test_case.assertIsInstance(product, Product)
        test_case.assertIsNotNone(product.name)
        test_case.assertGreater(product.price, 0)
        test_case.assertIsNotNone(product.url)
    
    @staticmethod
    def assert_failed_scraping_result(test_case, result, expected_error_fragment):
        """Assert failed scraping result with common checks"""
        test_case.assertFalse(result.success)
        test_case.assertIn(expected_error_fragment, result.error_message)
        test_case.assertEqual(len(result.products), 0)
    
    @staticmethod
    def assert_empty_scraping_result(test_case, result):
        """Assert successful but empty scraping result"""
        test_case.assertTrue(result.success)
        test_case.assertEqual(len(result.products), 0)


class TestMitra10Integration(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        fixture_path = base / "mitra10_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")
        
    def setUp(self):
        self.mock_http_client = Mock(spec=PlaywrightHttpClient)
        self.url_builder = Mitra10UrlBuilder()
        self.html_parser = Mitra10HtmlParser()
        self.scraper = Mitra10PriceScraper(
            self.mock_http_client, 
            self.url_builder, 
            self.html_parser
        )
        self.batch_helper = BatchPlaywrightClientHelper()
        self.test_helper = IntegrationTestHelper()
        
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_complete_scraping_pipeline_success(self, mock_batch_client):
        keyword = "semen"
        
        mock_client_instance = self.batch_helper.setup_successful_mock(mock_batch_client, self.mock_html)
        
        result = self.scraper.scrape_products(keyword)
        
        self.test_helper.assert_successful_scraping_result(self, result, "q=semen")
        self.assertIn("sort=", result.url)
        
        # Verify BatchPlaywrightClient was used correctly
        self.assertTrue(self.batch_helper.assert_batch_client_called(
            mock_batch_client, mock_client_instance, "q=semen"
        ))
        
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scraping_with_price_sorting(self, mock_batch_client):
        keyword = "semen"
        
        self.batch_helper.setup_successful_mock(mock_batch_client, self.mock_html)
        
        result = self.scraper.scrape_products(keyword, sort_by_price=True)
        
        self.test_helper.assert_successful_scraping_result(self, result, "q=semen")
        self.assertIn("sort=", result.url)
        self.assertTrue(
            "%7B%22key%22%3A%22price%22%2C%22value%22%3A%22ASC%22%7D" in result.url or
            "sort=%7B%22key%22%3A%22price%22%2C%22value%22%3A%22ASC%22%7D" in result.url
        )
        
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scraping_with_http_error(self, mock_batch_client):
        keyword = "semen"
        error_message = "Request timeout after 30s for https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22%3A%22price%22%2C%22value%22%3A%22ASC%22%7D&page=1"
        
        self.batch_helper.setup_error_mock(mock_batch_client, error_message)
        
        result = self.scraper.scrape_products(keyword)
        
        self.test_helper.assert_failed_scraping_result(self, result, "Request timeout after 30s")
        
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scraping_with_empty_html(self, mock_batch_client):
        keyword = "semen"
        
        self.batch_helper.setup_successful_mock(mock_batch_client, "")
        
        result = self.scraper.scrape_products(keyword)
        
        self.test_helper.assert_empty_scraping_result(self, result)
        
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scraping_with_no_products_found(self, mock_batch_client):
        keyword = "nonexistent"
        no_products_html = "<html><body><div>No products found</div></body></html>"
        
        self.batch_helper.setup_successful_mock(mock_batch_client, no_products_html)
        
        result = self.scraper.scrape_products(keyword)
        
        self.test_helper.assert_empty_scraping_result(self, result)
        
    def test_invalid_keyword_handling(self):
        # These should fail at URL building stage before BatchPlaywrightClient is used
        for invalid_keyword in ["", "   "]:
            result = self.scraper.scrape_products(invalid_keyword)
            self.test_helper.assert_failed_scraping_result(self, result, "Keyword cannot be empty")
        
    def test_factory_function(self):
        scraper = create_mitra10_scraper()
        
        self.assertIsInstance(scraper, IPriceScraper)
        self.assertIsInstance(scraper, Mitra10PriceScraper)
        self.assertIsNone(scraper.http_client)  # Factory passes None, scraper handles BatchPlaywrightClient internally
        self.assertIsNotNone(scraper.url_builder)
        self.assertIsNotNone(scraper.html_parser)

        self.assertIsInstance(scraper.url_builder, Mitra10UrlBuilder)
        self.assertIsInstance(scraper.html_parser, Mitra10HtmlParser)
        
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_dependency_injection_flexibility(self, mock_batch_client):
        mock_http_client = Mock()
        
        mock_url_builder = Mock()
        mock_url_builder.build_search_url.return_value = "https://www.mitra10.com/catalogsearch/result?q=test"
        
        mock_html_parser = Mock()
        mock_html_parser.parse_products.return_value = [
            Product(name="Test Mitra10 Product", price=50000, url="/product/test")
        ]
        
        mock_client_instance = self.batch_helper.setup_successful_mock(mock_batch_client, self.mock_html)
        
        scraper = Mitra10PriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        result = scraper.scrape_products("test")
        
        mock_url_builder.build_search_url.assert_called_once_with("test", True, 0)
        mock_client_instance.get.assert_called_once_with("https://www.mitra10.com/catalogsearch/result?q=test")
        mock_html_parser.parse_products.assert_called_once_with(self.mock_html)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 1)
        self.assertEqual(result.products[0].name, "Test Mitra10 Product")
        
    def test_error_propagation(self):
        mock_url_builder = Mock()
        mock_url_builder.build_search_url.side_effect = Exception("URL error")
        
        scraper = Mitra10PriceScraper(self.mock_http_client, mock_url_builder, self.html_parser)
        result = scraper.scrape_products("test")
        
        self.test_helper.assert_failed_scraping_result(self, result, "URL error")
        
    @patch('api.mitra10.factory.Mitra10UrlBuilder')
    @patch('api.mitra10.factory.Mitra10HtmlParser')
    def test_factory_creates_new_instances(self, mock_parser_class, mock_builder_class):
        mock_builder = Mock()
        mock_parser = Mock()
        
        mock_builder_class.return_value = mock_builder
        mock_parser_class.return_value = mock_parser
        
        scraper = create_mitra10_scraper()
        
        mock_builder_class.assert_called_once()
        mock_parser_class.assert_called_once()
        
        self.assertIsNone(scraper.http_client)  # Factory passes None as http_client
        self.assertEqual(scraper.url_builder, mock_builder)
        self.assertEqual(scraper.html_parser, mock_parser)