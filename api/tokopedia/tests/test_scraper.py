import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase

from api.tokopedia.scraper import (
    TokopediaPriceScraper, 
    get_location_ids, 
    get_location_ids_strict,
    get_available_locations,
    TokopediaLocationError,
    TOKOPEDIA_LOCATION_IDS
)
from api.interfaces import Product, ScrapingResult, IHttpClient, IUrlBuilder, IHtmlParser
from api.playwright_client import BatchPlaywrightClient
from api.tokopedia.url_builder import TokopediaUrlBuilder
from api.tokopedia.html_parser import TokopediaHtmlParser


class TestTokopediaPriceScraper(TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.scraper = TokopediaPriceScraper()
        
        # Sample products for testing
        self.sample_products = [
            Product(name="Semen Gresik 40 KG", price=62500, url="https://tokopedia.com/product/1"),
            Product(name="Semen Tiga Roda 40 KG", price=65000, url="https://tokopedia.com/product/2"),
        ]
        
        # Sample HTML content
        self.sample_html = "<html><div>Sample HTML content</div></html>"

    def test_scraper_initialization_with_defaults(self):
        """Test scraper initialization with default components"""
        scraper = TokopediaPriceScraper()
        
        # Check that default components are used
        self.assertIsInstance(scraper.url_builder, TokopediaUrlBuilder)
        self.assertIsInstance(scraper.html_parser, TokopediaHtmlParser)
        # TokopediaPriceScraper uses BaseHttpClient as default (not BatchPlaywrightClient)
        # due to HTTP/2 issues with Tokopedia
        from api.tokopedia_core import BaseHttpClient
        self.assertIsInstance(scraper.http_client, BaseHttpClient)

    def test_scraper_initialization_with_custom_components(self):
        """Test scraper initialization with custom components"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock(spec=IUrlBuilder)
        mock_html_parser = Mock(spec=IHtmlParser)
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        self.assertIs(scraper.http_client, mock_http_client)
        self.assertIs(scraper.url_builder, mock_url_builder)
        self.assertIs(scraper.html_parser, mock_html_parser)

    def test_scrape_products_with_filters_success(self):
        """Test successful scraping with filters"""
        # Mock dependencies
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        # Configure mocks
        test_url = "https://tokopedia.com/search?q=semen&ob=3"
        mock_url_builder.build_search_url_with_filters.return_value = test_url
        mock_http_client.get.return_value = self.sample_html
        mock_html_parser.parse_products.return_value = self.sample_products
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Execute test
        result = scraper.scrape_products_with_filters(
            keyword="semen",
            sort_by_price=True,
            page=0,
            min_price=50000,
            max_price=100000,
            location="jakarta"
        )
        
        # Verify results
        self.assertIsInstance(result, ScrapingResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 2)
        self.assertEqual(result.products[0].name, "Semen Gresik 40 KG")
        self.assertEqual(result.url, test_url)
        self.assertIsNone(result.error_message)
        
        # Verify mock calls
        mock_url_builder.build_search_url_with_filters.assert_called_once_with(
            keyword="semen",
            sort_by_price=True,
            page=0,
            min_price=50000,
            max_price=100000,
            location_ids=[174, 175, 176, 177, 178, 179]  # Jakarta location IDs
        )
        mock_http_client.get.assert_called_once_with(test_url, timeout=60)
        mock_html_parser.parse_products.assert_called_once_with(self.sample_html)

    def test_scrape_products_with_filters_unknown_location(self):
        """Test scraping with unknown location shows warning but continues"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        test_url = "https://tokopedia.com/search?q=semen"
        mock_url_builder.build_search_url_with_filters.return_value = test_url
        mock_http_client.get.return_value = self.sample_html
        mock_html_parser.parse_products.return_value = self.sample_products
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Test with warnings capture instead of print
        with patch('api.tokopedia.scraper.logger') as mock_logger, \
             patch('api.tokopedia.scraper.warnings') as mock_warnings:
            result = scraper.scrape_products_with_filters(
                keyword="semen",
                location="unknown_city"
            )
            
            # Should still succeed but show warning
            self.assertTrue(result.success)
            
            # Check that warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            self.assertIn("Unknown location provided", warning_call)
            
            # Check that warning was issued
            mock_warnings.warn.assert_called_once()
            
            # Should call with location_ids=[] (since location validation returns [] for invalid locations)
            mock_url_builder.build_search_url_with_filters.assert_called_once_with(
                keyword="semen",
                sort_by_price=True,
                page=0,
                min_price=None,
                max_price=None,
                location_ids=[]
            )

    def test_scrape_products_with_filters_error_handling(self):
        """Test error handling in scrape_products_with_filters"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        # Configure mock to raise exception
        mock_http_client.get.side_effect = Exception("Network error")
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        result = scraper.scrape_products_with_filters(keyword="semen")
        
        # Verify error handling
        self.assertFalse(result.success)
        self.assertEqual(len(result.products), 0)
        self.assertEqual(result.error_message, "Network error")
        self.assertIsNone(result.url)

    @patch('api.tokopedia.scraper.BatchPlaywrightClient')
    def test_scrape_batch_with_filters_success(self, mock_batch_client_class):
        """Test successful batch scraping with filters"""
        # Setup mock BatchPlaywrightClient
        mock_batch_client = Mock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        mock_batch_client.get.return_value = self.sample_html
        
        # Setup other mocks
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_html_parser.parse_products.return_value = self.sample_products
        
        scraper = TokopediaPriceScraper(
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Execute test
        keywords = ["semen", "bata merah"]
        result = scraper.scrape_batch_with_filters(
            keywords=keywords,
            sort_by_price=True,
            min_price=50000,
            max_price=100000,
            location="bandung"
        )
        
        # Verify results
        self.assertEqual(len(result), 4)  # 2 products × 2 keywords
        self.assertEqual(result[0].name, "Semen Gresik 40 KG")
        
        # Verify correct number of calls
        self.assertEqual(mock_url_builder.build_search_url_with_filters.call_count, 2)
        self.assertEqual(mock_batch_client.get.call_count, 2)
        self.assertEqual(mock_html_parser.parse_products.call_count, 2)

    @patch('api.tokopedia.scraper.BatchPlaywrightClient')
    def test_scrape_batch_with_filters_partial_failure(self, mock_batch_client_class):
        """Test batch scraping with some keywords failing"""
        # Setup mock BatchPlaywrightClient
        mock_batch_client = Mock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        # First call succeeds, second fails
        mock_batch_client.get.side_effect = [self.sample_html, Exception("Network error")]
        
        # Setup other mocks
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_html_parser.parse_products.return_value = self.sample_products
        
        scraper = TokopediaPriceScraper(
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        with patch('api.tokopedia.scraper.logger') as mock_logger:
            keywords = ["semen", "bata merah"]
            result = scraper.scrape_batch_with_filters(keywords=keywords)
            
            # Should return products from successful keyword only
            self.assertEqual(len(result), 2)  # Only from first keyword
            
            # Should log error message for failed keyword
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn("Error scraping keyword in batch", error_call)

    @patch('api.tokopedia.scraper.BatchPlaywrightClient')
    def test_scrape_batch_override(self, mock_batch_client_class):
        """Test that scrape_batch method uses scrape_batch_with_filters"""
        # Setup mock BatchPlaywrightClient
        mock_batch_client = Mock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        mock_batch_client.get.return_value = self.sample_html
        
        # Setup other mocks
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_html_parser.parse_products.return_value = self.sample_products
        
        scraper = TokopediaPriceScraper(
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        keywords = ["semen"]
        result = scraper.scrape_batch(keywords)
        
        # Should return products
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Semen Gresik 40 KG")


class TestLocationIdFunctions(TestCase):
    """Test location ID utility functions"""
    
    def test_get_location_ids_jakarta(self):
        """Test getting location IDs for Jakarta"""
        # Test both 'jakarta' and 'dki_jakarta'
        jakarta_ids = get_location_ids('jakarta')
        dki_jakarta_ids = get_location_ids('dki_jakarta')
        
        expected_ids = [174, 175, 176, 177, 178, 179]
        self.assertEqual(jakarta_ids, expected_ids)
        self.assertEqual(dki_jakarta_ids, expected_ids)
    
    def test_get_location_ids_bandung(self):
        """Test getting location IDs for Bandung"""
        bandung_ids = get_location_ids('bandung')
        self.assertEqual(bandung_ids, [165])
    
    def test_get_location_ids_jabodetabek(self):
        """Test getting location IDs for Jabodetabek"""
        jabodetabek_ids = get_location_ids('jabodetabek')
        expected_ids = [144, 146, 150, 151, 167, 168, 171, 174, 175, 176, 177, 178, 179, 463]
        self.assertEqual(jabodetabek_ids, expected_ids)
    
    def test_get_location_ids_medan(self):
        """Test getting location IDs for Medan"""
        medan_ids = get_location_ids('medan')
        self.assertEqual(medan_ids, [46])
    
    def test_get_location_ids_surabaya(self):
        """Test getting location IDs for Surabaya"""
        surabaya_ids = get_location_ids('surabaya')
        self.assertEqual(surabaya_ids, [252])
    
    def test_get_location_ids_case_insensitive(self):
        """Test that location lookup is case insensitive"""
        jakarta_lower = get_location_ids('jakarta')
        jakarta_upper = get_location_ids('JAKARTA')
        jakarta_mixed = get_location_ids('Jakarta')
        
        expected_ids = [174, 175, 176, 177, 178, 179]
        self.assertEqual(jakarta_lower, expected_ids)
        self.assertEqual(jakarta_upper, expected_ids)
        self.assertEqual(jakarta_mixed, expected_ids)
    
    def test_get_location_ids_with_spaces(self):
        """Test location lookup with spaces converted to underscores"""
        # Note: Current implementation replaces spaces with underscores
        # If there were a location like "Dki Jakarta", it would be converted to "dki_jakarta"
        test_ids = get_location_ids('dki jakarta')  # Should convert to 'dki_jakarta'
        expected_ids = [174, 175, 176, 177, 178, 179]
        self.assertEqual(test_ids, expected_ids)
    
    def test_get_location_ids_unknown_location(self):
        """Test getting location IDs for unknown location"""
        unknown_ids = get_location_ids('unknown_city')
        self.assertEqual(unknown_ids, [])
    
    def test_get_location_ids_empty_string(self):
        """Test getting location IDs for empty string"""
        empty_ids = get_location_ids('')
        self.assertEqual(empty_ids, [])
    
    def test_tokopedia_location_ids_constant(self):
        """Test that TOKOPEDIA_LOCATION_IDS contains expected locations"""
        expected_locations = {
            'dki_jakarta', 'jakarta', 'jabodetabek', 'bandung', 'medan', 'surabaya'
        }
        
        actual_locations = set(TOKOPEDIA_LOCATION_IDS.keys())
        self.assertEqual(actual_locations, expected_locations)
        
        # Test that all values are lists of integers
        for location, ids in TOKOPEDIA_LOCATION_IDS.items():
            self.assertIsInstance(ids, list)
            for location_id in ids:
                self.assertIsInstance(location_id, int)
                self.assertGreater(location_id, 0)

    def test_get_location_ids_strict_success(self):
        """Test get_location_ids_strict with valid location"""
        jakarta_ids = get_location_ids_strict('jakarta')
        expected_ids = [174, 175, 176, 177, 178, 179]
        self.assertEqual(jakarta_ids, expected_ids)
        
        bandung_ids = get_location_ids_strict('bandung')
        self.assertEqual(bandung_ids, [165])
    
    def test_get_location_ids_strict_case_insensitive(self):
        """Test get_location_ids_strict is case insensitive"""
        jakarta_lower = get_location_ids_strict('jakarta')
        jakarta_upper = get_location_ids_strict('JAKARTA')
        jakarta_mixed = get_location_ids_strict('Jakarta')
        
        expected_ids = [174, 175, 176, 177, 178, 179]
        self.assertEqual(jakarta_lower, expected_ids)
        self.assertEqual(jakarta_upper, expected_ids)
        self.assertEqual(jakarta_mixed, expected_ids)
    
    def test_get_location_ids_strict_unknown_location_raises_error(self):
        """Test get_location_ids_strict raises TokopediaLocationError for unknown location"""
        with self.assertRaises(TokopediaLocationError) as context:
            get_location_ids_strict('unknown_city')
        
        error_msg = str(context.exception)
        self.assertIn("Unknown location 'unknown_city'", error_msg)
        self.assertIn("Available locations:", error_msg)
    
    def test_get_available_locations(self):
        """Test get_available_locations returns all location keys"""
        available_locations = get_available_locations()
        
        self.assertEqual(set(available_locations), set(TOKOPEDIA_LOCATION_IDS.keys()))
        self.assertIsInstance(available_locations, list)
        
        # Check that all expected locations are present
        expected_set = {'dki_jakarta', 'jakarta', 'jabodetabek', 'bandung', 'medan', 'surabaya'}
        self.assertEqual(set(available_locations), expected_set)


class TestScraperIntegration(TestCase):
    """Integration tests for the scraper with real components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_html = "<html><div>Sample HTML content</div></html>"
    
    def test_scraper_with_real_components_initialization(self):
        """Test that scraper initializes correctly with real components"""
        scraper = TokopediaPriceScraper()
        
        # Verify components are properly initialized
        self.assertIsNotNone(scraper.http_client)
        self.assertIsNotNone(scraper.url_builder)
        self.assertIsNotNone(scraper.html_parser)
        
        # Verify inheritance from BasePriceScraper
        self.assertTrue(hasattr(scraper, 'scrape_products'))
        
    def test_scraper_with_none_parameters(self):
        """Test scraper behavior with None parameters in filters"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_http_client.get.return_value = self.sample_html
        mock_html_parser.parse_products.return_value = []
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Test with all None parameters
        result = scraper.scrape_products_with_filters(
            keyword="semen",
            sort_by_price=True,
            page=0,
            min_price=None,
            max_price=None,
            location=None
        )
        
        self.assertTrue(result.success)
        mock_url_builder.build_search_url_with_filters.assert_called_once_with(
            keyword="semen",
            sort_by_price=True,
            page=0,
            min_price=None,
            max_price=None,
            location_ids=None
        )
    
    def test_scrape_with_limit_multiple_pages(self):
        """Test _scrape_with_limit fetches multiple pages"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        # First page returns 5 products, second page returns 5, third returns 3
        products_page1 = [Product(f"Product {i}", 1000, f"url{i}") for i in range(5)]
        products_page2 = [Product(f"Product {i}", 1000, f"url{i}") for i in range(5, 10)]
        products_page3 = [Product(f"Product {i}", 1000, f"url{i}") for i in range(10, 13)]
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_http_client.get.return_value = self.sample_html
        mock_html_parser.parse_products.side_effect = [products_page1, products_page2, products_page3]
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Request 12 products (should fetch 3 pages)
        result = scraper.scrape_products_with_filters(keyword="semen", limit=12)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 12)
        self.assertEqual(mock_http_client.get.call_count, 3)
    
    def test_scrape_with_limit_stops_when_no_products(self):
        """Test _scrape_with_limit stops when page returns no products"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        # First page returns products, second page returns empty
        products_page1 = [Product(f"Product {i}", 1000, f"url{i}") for i in range(5)]
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_http_client.get.return_value = self.sample_html
        mock_html_parser.parse_products.side_effect = [products_page1, []]  # Empty on page 2
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Request 20 products but should stop at 5 when no more products found
        result = scraper.scrape_products_with_filters(keyword="semen", limit=20)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 5)
        self.assertEqual(mock_http_client.get.call_count, 2)  # Tried 2 pages
    
    def test_scrape_with_limit_handles_exception(self):
        """Test _scrape_with_limit handles exception during multi-page fetch"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        # First page succeeds, second raises exception
        products_page1 = [Product(f"Product {i}", 1000, f"url{i}") for i in range(5)]
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_http_client.get.side_effect = [self.sample_html, Exception("Network error")]
        mock_html_parser.parse_products.return_value = products_page1
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        with patch('api.tokopedia.scraper.logger') as mock_logger:
            result = scraper.scrape_products_with_filters(keyword="semen", limit=20)
            
            # Should return products from first page only
            self.assertTrue(result.success)
            self.assertEqual(len(result.products), 5)
            
            # Should log error
            mock_logger.error.assert_called()
    
    def test_scrape_with_limit_trims_to_exact_limit(self):
        """Test _scrape_with_limit trims results to exact limit"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        # First page returns 8 products
        products_page1 = [Product(f"Product {i}", 1000, f"url{i}") for i in range(8)]
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_http_client.get.return_value = self.sample_html
        mock_html_parser.parse_products.return_value = products_page1
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Request only 5 products (should trim 8 to 5)
        result = scraper.scrape_products_with_filters(keyword="semen", limit=5)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 5)
        self.assertEqual(result.products[0].name, "Product 0")
        self.assertEqual(result.products[4].name, "Product 4")
    
    def test_scrape_products_with_limit_delegation(self):
        """Test scrape_products properly delegates to scrape_products_with_filters with limit (line 77)"""
        mock_http_client = Mock(spec=IHttpClient)
        mock_url_builder = Mock()
        mock_html_parser = Mock(spec=IHtmlParser)
        
        # Return enough products to satisfy the limit in one page
        products = [Product(f"Product {i}", 1000, f"url{i}") for i in range(15)]
        
        mock_url_builder.build_search_url_with_filters.return_value = "test_url"
        mock_http_client.get.return_value = self.sample_html
        mock_html_parser.parse_products.return_value = products
        
        scraper = TokopediaPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Call scrape_products with limit parameter (with enough products in first page)
        result = scraper.scrape_products(
            keyword="semen",
            sort_by_price=False,
            page=1,
            limit=10
        )
        
        # Should delegate to scrape_products_with_filters and only need one page
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 10)  # Trimmed to limit
        
        # Should be called once per page (limit is satisfied from first page)
        mock_url_builder.build_search_url_with_filters.assert_called_with(
            keyword="semen",
            sort_by_price=False,
            page=1,
            min_price=None,
            max_price=None,
            location_ids=None
        )


if __name__ == '__main__':
    unittest.main()



