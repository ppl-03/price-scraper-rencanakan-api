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
            Product(name="Product 1", price=1000, url="/product1", unit=None),  # No unit, will trigger detail page fetch
            Product(name="Product 2", price=2000, url="/product2", unit=None)   # No unit, will trigger detail page fetch
        ]
        
        self.mock_url_builder.build_search_url.return_value = test_url
        self.mock_http_client.get.return_value = test_html  # Same HTML for all requests (main + detail pages)
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
        
        # Verify method calls - enhanced scraper makes additional calls for detail pages
        self.mock_url_builder.build_search_url.assert_called_once_with("cat", True, 0)
        # HTTP client should be called 3 times: main page + 2 detail pages
        self.assertEqual(self.mock_http_client.get.call_count, 3)
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
    
    def test_factory_integration_creates_working_scraper(self):
        """Test that the factory creates a working scraper with all components integrated"""
        from api.depobangunan.factory import create_depo_scraper
        
        # Create scraper using factory
        scraper = create_depo_scraper()
        
        # Verify scraper is created correctly
        self.assertIsNotNone(scraper)
        self.assertIsInstance(scraper, DepoPriceScraper)
        
        # Verify all components exist and are properly wired
        self.assertIsNotNone(scraper.http_client)
        self.assertIsNotNone(scraper.url_builder)
        self.assertIsNotNone(scraper.html_parser)
        
        # Verify component types are correct
        from api.core import BaseHttpClient
        from api.depobangunan.url_builder import DepoUrlBuilder
        from api.depobangunan.html_parser import DepoHtmlParser
        
        self.assertIsInstance(scraper.http_client, BaseHttpClient)
        self.assertIsInstance(scraper.url_builder, DepoUrlBuilder)
        self.assertIsInstance(scraper.html_parser, DepoHtmlParser)
    
    @patch('api.depobangunan.factory.DepoHtmlParser')
    @patch('api.depobangunan.factory.DepoUrlBuilder')
    @patch('api.depobangunan.factory.BaseHttpClient')
    def test_factory_integration_component_creation_order(self, mock_http_client, mock_url_builder, mock_html_parser):
        """Test that factory creates components in the correct order"""
        from api.depobangunan.factory import create_depo_scraper
        
        # Setup mock instances
        mock_http_instance = Mock()
        mock_url_instance = Mock()
        mock_html_instance = Mock()
        
        mock_http_client.return_value = mock_http_instance
        mock_url_builder.return_value = mock_url_instance
        mock_html_parser.return_value = mock_html_instance
        
        # Create scraper
        scraper = create_depo_scraper()
        
        # Verify all components were created
        mock_http_client.assert_called_once()
        mock_url_builder.assert_called_once()
        mock_html_parser.assert_called_once()
        
        # Verify scraper was created with the mocked components
        self.assertEqual(scraper.http_client, mock_http_instance)
        self.assertEqual(scraper.url_builder, mock_url_instance)
        self.assertEqual(scraper.html_parser, mock_html_instance)
    
    def test_factory_creates_unique_instances(self):
        """Test that factory creates new instances each time it's called"""
        from api.depobangunan.factory import create_depo_scraper
        
        # Create two scrapers
        scraper1 = create_depo_scraper()
        scraper2 = create_depo_scraper()
        
        # Verify they are different instances
        self.assertIsNot(scraper1, scraper2)
        self.assertIsNot(scraper1.http_client, scraper2.http_client)
        self.assertIsNot(scraper1.url_builder, scraper2.url_builder)
        self.assertIsNot(scraper1.html_parser, scraper2.html_parser)
        
        # But they should be the same types
        self.assertEqual(type(scraper1), type(scraper2))
        self.assertEqual(type(scraper1.http_client), type(scraper2.http_client))
        self.assertEqual(type(scraper1.url_builder), type(scraper2.url_builder))
        self.assertEqual(type(scraper1.html_parser), type(scraper2.html_parser))


if __name__ == '__main__':
    unittest.main()