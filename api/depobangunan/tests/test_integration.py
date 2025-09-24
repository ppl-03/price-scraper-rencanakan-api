import unittest
from unittest.mock import Mock, patch
from api.depobangunan.scraper import DepoPriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, Product, ScrapingResult
from api.interfaces import HttpClientError, UrlBuilderError, HtmlParserError


class TestDepoIntegration(unittest.TestCase):
    
    def setUp(self):
        self.mock_http_client = Mock(spec=IHttpClient)
        self.mock_url_builder = Mock(spec=IUrlBuilder)
        self.mock_html_parser = Mock(spec=IHtmlParser)
        
        self.scraper = DepoPriceScraper(
            self.mock_http_client,
            self.mock_url_builder,
            self.mock_html_parser
        )
    
    def test_scrape_products_success(self):
        # Setup mocks
        test_url = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high"
        test_html = "<html>mock html</html>"
        test_products = [
            Product(name="Product 1", price=1000, url="/product1"),
            Product(name="Product 2", price=2000, url="/product2")
        ]
        
        self.mock_url_builder.build_search_url.return_value = test_url
        self.mock_http_client.get.return_value = test_html
        self.mock_html_parser.parse_products.return_value = test_products
        
        # Execute
        result = self.scraper.scrape_products("cat")
        
        # Verify
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 2)
        self.assertEqual(result.products[0].name, "Product 1")
        self.assertEqual(result.products[1].name, "Product 2")
        self.assertEqual(result.url, test_url)
        self.assertIsNone(result.error_message)
        
        # Verify method calls
        self.mock_url_builder.build_search_url.assert_called_once_with("cat", True, 0)
        self.mock_http_client.get.assert_called_once_with(test_url)
        self.mock_html_parser.parse_products.assert_called_once_with(test_html)
    
    def test_scrape_products_with_custom_parameters(self):
        test_url = "https://www.depobangunan.co.id/catalogsearch/result/?q=semen"
        
        self.mock_url_builder.build_search_url.return_value = test_url
        self.mock_http_client.get.return_value = "<html></html>"
        self.mock_html_parser.parse_products.return_value = []
        
        # Execute with custom parameters
        result = self.scraper.scrape_products("semen", sort_by_price=False, page=1)
        
        # Verify parameters passed correctly
        self.mock_url_builder.build_search_url.assert_called_once_with("semen", False, 1)
        self.assertTrue(result.success)
    
    def test_scrape_products_url_builder_error(self):
        self.mock_url_builder.build_search_url.side_effect = UrlBuilderError("Invalid keyword")
        
        result = self.scraper.scrape_products("cat")
        
        self.assertFalse(result.success)
        self.assertEqual(result.products, [])
        self.assertEqual(result.error_message, "Invalid keyword")
        self.assertIsNone(result.url)
    
    def test_scrape_products_http_client_error(self):
        test_url = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high"
        
        self.mock_url_builder.build_search_url.return_value = test_url
        self.mock_http_client.get.side_effect = HttpClientError("Connection failed")
        
        result = self.scraper.scrape_products("cat")
        
        self.assertFalse(result.success)
        self.assertEqual(result.products, [])
        self.assertEqual(result.error_message, "Connection failed")
        self.assertIsNone(result.url)
    
    def test_scrape_products_html_parser_error(self):
        test_url = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high"
        test_html = "<html>invalid</html>"
        
        self.mock_url_builder.build_search_url.return_value = test_url
        self.mock_http_client.get.return_value = test_html
        self.mock_html_parser.parse_products.side_effect = HtmlParserError("Parse failed")
        
        result = self.scraper.scrape_products("cat")
        
        self.assertFalse(result.success)
        self.assertEqual(result.products, [])
        self.assertEqual(result.error_message, "Parse failed")
        self.assertIsNone(result.url)
    
    def test_scrape_products_unexpected_error(self):
        self.mock_url_builder.build_search_url.side_effect = Exception("Unexpected error")
        
        result = self.scraper.scrape_products("cat")
        
        self.assertFalse(result.success)
        self.assertEqual(result.products, [])
        self.assertIn("Unexpected error", result.error_message)
        self.assertIsNone(result.url)
    
    def test_scrape_products_empty_results(self):
        test_url = "https://www.depobangunan.co.id/catalogsearch/result/?q=nonexistent"
        
        self.mock_url_builder.build_search_url.return_value = test_url
        self.mock_http_client.get.return_value = "<html></html>"
        self.mock_html_parser.parse_products.return_value = []
        
        result = self.scraper.scrape_products("nonexistent")
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 0)
        self.assertEqual(result.url, test_url)
    
    @patch('api.core.logger')
    def test_scrape_products_logging(self, mock_logger):
        self.mock_url_builder.build_search_url.side_effect = UrlBuilderError("Test error")
        
        result = self.scraper.scrape_products("cat")
        
        self.assertFalse(result.success)
        mock_logger.error.assert_called_once()


if __name__ == '__main__':
    unittest.main()