from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from api.interfaces import Product, IHttpClient, IUrlBuilder, IHtmlParser
from api.mitra10.scraper import Mitra10PriceScraper


class TestMitra10PriceScraper(TestCase):
    
    def setUp(self):
        self.mock_http_client = Mock(spec=IHttpClient)
        self.mock_url_builder = Mock(spec=IUrlBuilder)
        self.mock_html_parser = Mock(spec=IHtmlParser)
        
        self.scraper = Mitra10PriceScraper(
            http_client=self.mock_http_client,
            url_builder=self.mock_url_builder,
            html_parser=self.mock_html_parser
        )
    
    def test_init(self):
        scraper = Mitra10PriceScraper(
            self.mock_http_client,
            self.mock_url_builder,
            self.mock_html_parser
        )
        
        self.assertEqual(scraper.http_client, self.mock_http_client)
        self.assertEqual(scraper.url_builder, self.mock_url_builder)
        self.assertEqual(scraper.html_parser, self.mock_html_parser)

    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_products_success(self, mock_batch_client_class):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client

        test_keyword = "semen"
        test_url = "https://test.com/search?q=semen&sort=true&page=0"
        test_html = "<html>list</html>"
        test_products = [Product(name="A", price=1000, url="/a")]

        self.mock_url_builder.build_search_url.return_value = test_url
        mock_batch_client.get.return_value = test_html
        self.mock_html_parser.parse_products.return_value = test_products

        result = self.scraper.scrape_products(test_keyword, sort_by_price=True, page=0)

        self.assertTrue(result.success)
        self.assertEqual(result.url, test_url)
        self.assertEqual(len(result.products), 1)
        mock_batch_client.get.assert_called_once_with(test_url, timeout=60)
        self.mock_html_parser.parse_products.assert_called_once_with(test_html)

    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_products_failure(self, mock_batch_client_class):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client

        test_keyword = "semen"
        test_url = "https://test.com/search?q=semen&sort=true&page=0"

        self.mock_url_builder.build_search_url.return_value = test_url
        mock_batch_client.get.side_effect = Exception("network boom")

        result = self.scraper.scrape_products(test_keyword, sort_by_price=True, page=0)

        self.assertFalse(result.success)
        self.assertIn("Scraping failed", result.error_message)
        self.assertEqual(result.url, test_url)
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_success_single_keyword(self, mock_batch_client_class):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keyword = "semen"
        test_url = "https://test.com/search?q=semen"
        test_html = "<html>test content</html>"
        test_products = [
            Product(name="Test Product", price=15000, url="https://test.com/product1")
        ]
        
        self.mock_url_builder.build_search_url.return_value = test_url
        mock_batch_client.get.return_value = test_html
        self.mock_html_parser.parse_products.return_value = test_products
        
        result = self.scraper.scrape_batch([test_keyword])
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Test Product")
        self.assertEqual(result[0].price, 15000)
        self.assertEqual(result[0].url, "https://test.com/product1")
        
        self.mock_url_builder.build_search_url.assert_called_once_with(test_keyword)
        mock_batch_client.get.assert_called_once_with(test_url, timeout=60)
        self.mock_html_parser.parse_products.assert_called_once_with(test_html)
        
        mock_batch_client_class.assert_called_once()
        mock_batch_client_class.return_value.__enter__.assert_called_once()
        mock_batch_client_class.return_value.__exit__.assert_called_once()
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_success_multiple_keywords(self, mock_batch_client_class):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keywords = ["semen", "cat", "paku"]
        test_urls = [
            "https://test.com/search?q=semen",
            "https://test.com/search?q=cat",
            "https://test.com/search?q=paku"
        ]
        test_html = "<html>test content</html>"
        test_products_per_keyword = [
            [Product(name="Semen Product", price=15000, url="https://test.com/semen1")],
            [Product(name="Cat Product", price=25000, url="https://test.com/cat1")],
            [Product(name="Paku Product", price=5000, url="https://test.com/paku1")]
        ]
        
        self.mock_url_builder.build_search_url.side_effect = test_urls
        mock_batch_client.get.return_value = test_html
        self.mock_html_parser.parse_products.side_effect = test_products_per_keyword
        
        result = self.scraper.scrape_batch(test_keywords)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].name, "Semen Product")
        self.assertEqual(result[1].name, "Cat Product")
        self.assertEqual(result[2].name, "Paku Product")
        self.assertEqual(self.mock_url_builder.build_search_url.call_count, 3)
        self.assertEqual(mock_batch_client.get.call_count, 3)
        self.assertEqual(self.mock_html_parser.parse_products.call_count, 3)
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_empty_keywords_list(self, mock_batch_client_class):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        result = self.scraper.scrape_batch([])
        
        self.assertEqual(result, [])
        
        self.mock_url_builder.build_search_url.assert_not_called()
        mock_batch_client.get.assert_not_called()
        self.mock_html_parser.parse_products.assert_not_called()
    
    @patch('builtins.print')  
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_url_builder_error(self, mock_batch_client_class, mock_print):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keywords = ["test_keyword"]
        
        self.mock_url_builder.build_search_url.side_effect = Exception("URL builder error")
        
        result = self.scraper.scrape_batch(test_keywords)
        
        self.assertEqual(result, [])
        
        mock_print.assert_called_once_with("Error scraping test_keyword: URL builder error")
        
        self.mock_url_builder.build_search_url.assert_called_once_with("test_keyword")
        mock_batch_client.get.assert_not_called()
        self.mock_html_parser.parse_products.assert_not_called()
    
    @patch('builtins.print') 
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_http_client_error(self, mock_batch_client_class, mock_print):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keywords = ["test_keyword"]
        test_url = "https://test.com/search?q=test_keyword"
        
        self.mock_url_builder.build_search_url.return_value = test_url
        mock_batch_client.get.side_effect = Exception("HTTP client error")
        
        result = self.scraper.scrape_batch(test_keywords)
        
        self.assertEqual(result, [])
        
        mock_print.assert_called_once_with("Error scraping test_keyword: HTTP client error")
        
        self.mock_url_builder.build_search_url.assert_called_once_with("test_keyword")
        mock_batch_client.get.assert_called_once_with(test_url)
        self.mock_html_parser.parse_products.assert_not_called()
    
    @patch('builtins.print')  
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_html_parser_error(self, mock_batch_client_class, mock_print):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keywords = ["test_keyword"]
        test_url = "https://test.com/search?q=test_keyword"
        test_html = "<html>test content</html>"
        
        self.mock_url_builder.build_search_url.return_value = test_url
        mock_batch_client.get.return_value = test_html
        self.mock_html_parser.parse_products.side_effect = Exception("HTML parser error")
        
        result = self.scraper.scrape_batch(test_keywords)
        
        self.assertEqual(result, [])
        
        mock_print.assert_called_once_with("Error scraping test_keyword: HTML parser error")
        
        self.mock_url_builder.build_search_url.assert_called_once_with("test_keyword")
        mock_batch_client.get.assert_called_once_with(test_url)
        self.mock_html_parser.parse_products.assert_called_once_with(test_html)
    
    @patch('builtins.print')  
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_mixed_success_and_failure(self, mock_batch_client_class, mock_print):

        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keywords = ["success_keyword", "fail_keyword", "another_success"]
        test_urls = [
            "https://test.com/search?q=success_keyword",
            "https://test.com/search?q=fail_keyword",
            "https://test.com/search?q=another_success"
        ]
        test_html = "<html>test content</html>"
        
        success_products_1 = [Product(name="Success Product 1", price=10000, url="https://test.com/success1")]
        success_products_2 = [Product(name="Success Product 2", price=20000, url="https://test.com/success2")]
        
        def mock_build_url(keyword):
            if keyword == "success_keyword":
                return test_urls[0]
            elif keyword == "fail_keyword":
                return test_urls[1]
            elif keyword == "another_success":
                return test_urls[2]
        
        def mock_get_html(url, **kwargs):
            if url == test_urls[1]:  
                raise ConnectionError("Network error")
            return test_html
        
        def mock_parse_products(html):
            call_count = mock_parse_products.call_count
            mock_parse_products.call_count += 1
            if call_count == 0:
                return success_products_1
            else:
                return success_products_2
        
        mock_parse_products.call_count = 0
        
        self.mock_url_builder.build_search_url.side_effect = mock_build_url
        mock_batch_client.get.side_effect = mock_get_html
        self.mock_html_parser.parse_products.side_effect = mock_parse_products
        
        result = self.scraper.scrape_batch(test_keywords)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Success Product 1")
        self.assertEqual(result[1].name, "Success Product 2")
        
        mock_print.assert_called_once_with("Error scraping fail_keyword: Network error")
        
        self.assertEqual(self.mock_url_builder.build_search_url.call_count, 3)
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_no_products_found(self, mock_batch_client_class):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keywords = ["no_results_keyword"]
        test_url = "https://test.com/search?q=no_results_keyword"
        test_html = "<html>no products found</html>"
        
        self.mock_url_builder.build_search_url.return_value = test_url
        mock_batch_client.get.return_value = test_html
        self.mock_html_parser.parse_products.return_value = []
        
        result = self.scraper.scrape_batch(test_keywords)
        
        self.assertEqual(result, [])

        self.mock_url_builder.build_search_url.assert_called_once_with("no_results_keyword")
        mock_batch_client.get.assert_called_once_with(test_url, timeout=60)
        self.mock_html_parser.parse_products.assert_called_once_with(test_html)
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_batch_extends_products_correctly(self, mock_batch_client_class):
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keywords = ["keyword1", "keyword2"]
        test_html = "<html>test content</html>"
        
        products_keyword1 = [
            Product(name="Product 1A", price=10000, url="https://test.com/1a"),
            Product(name="Product 1B", price=15000, url="https://test.com/1b")
        ]
        products_keyword2 = [
            Product(name="Product 2A", price=20000, url="https://test.com/2a"),
            Product(name="Product 2B", price=25000, url="https://test.com/2b"),
            Product(name="Product 2C", price=30000, url="https://test.com/2c")
        ]
        
        self.mock_url_builder.build_search_url.side_effect = [
            "https://test.com/search?q=keyword1",
            "https://test.com/search?q=keyword2"
        ]
        mock_batch_client.get.return_value = test_html
        self.mock_html_parser.parse_products.side_effect = [products_keyword1, products_keyword2]
        
        result = self.scraper.scrape_batch(test_keywords)
        
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0].name, "Product 1A")
        self.assertEqual(result[1].name, "Product 1B")
        self.assertEqual(result[2].name, "Product 2A")
        self.assertEqual(result[3].name, "Product 2B")
        self.assertEqual(result[4].name, "Product 2C")

    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    @patch('builtins.print')
    def test_scrape_batch_with_error_handling_comprehensive(self, mock_print, mock_batch_client_class):
        """Test comprehensive error handling in scrape_batch"""
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keywords = ["keyword1", "keyword2", "keyword3"]
        
        # Mock url_builder to fail on second keyword
        self.mock_url_builder.build_search_url.side_effect = [
            "https://test.com/search?q=keyword1",
            Exception("URL builder error"),
            "https://test.com/search?q=keyword3"
        ]
        
        # Mock successful response for keywords that don't error
        mock_batch_client.get.return_value = "<html>test</html>"
        self.mock_html_parser.parse_products.return_value = [
            Product(name="Test Product", price=10000, url="https://test.com/product")
        ]
        
        result = self.scraper.scrape_batch(test_keywords)
        
        # Should get products from keyword1 and keyword3, skip keyword2 due to error
        self.assertEqual(len(result), 2)
        
        # Verify error was printed
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        self.assertIn("Error scraping keyword2", call_args)
        self.assertIn("URL builder error", call_args)

    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    @patch('builtins.print')
    def test_scrape_batch_http_client_error(self, mock_print, mock_batch_client_class):
        """Test error handling when HTTP client fails"""
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keyword = "test_keyword"
        self.mock_url_builder.build_search_url.return_value = "https://test.com/search"
        mock_batch_client.get.side_effect = Exception("Network error")
        
        result = self.scraper.scrape_batch([test_keyword])
        
        self.assertEqual(len(result), 0)
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        self.assertIn("Error scraping test_keyword", call_args)
        self.assertIn("Network error", call_args)

    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    @patch('builtins.print')
    def test_scrape_batch_html_parser_error(self, mock_print, mock_batch_client_class):
        """Test error handling when HTML parser fails"""
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keyword = "test_keyword"
        self.mock_url_builder.build_search_url.return_value = "https://test.com/search"
        mock_batch_client.get.return_value = "<html>test</html>"
        self.mock_html_parser.parse_products.side_effect = Exception("Parser error")
        
        result = self.scraper.scrape_batch([test_keyword])
        
        self.assertEqual(len(result), 0)
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        self.assertIn("Error scraping test_keyword", call_args)
        self.assertIn("Parser error", call_args)


class TestMitra10PriceScraperPopularity(TestCase):
    """Tests for scrape_by_popularity functionality"""
    
    def setUp(self):
        self.mock_http_client = Mock(spec=IHttpClient)
        self.mock_url_builder = Mock(spec=IUrlBuilder)
        self.mock_html_parser = Mock(spec=IHtmlParser)
        
        self.scraper = Mitra10PriceScraper(
            http_client=self.mock_http_client,
            url_builder=self.mock_url_builder,
            html_parser=self.mock_html_parser
        )
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_by_popularity_success(self, mock_batch_client_class):
        """Test successful scrape_by_popularity with default top_n=5"""
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keyword = "palu"
        test_url = "https://test.com/search?q=palu"
        test_html = "<html>test content</html>"
        
        # Create products with sold_count
        test_products = [
            Product(name="Popular Product 1", price=150000, url="https://test.com/p1", sold_count=1000),
            Product(name="Popular Product 2", price=120000, url="https://test.com/p2", sold_count=800),
            Product(name="Popular Product 3", price=100000, url="https://test.com/p3", sold_count=600),
            Product(name="Popular Product 4", price=90000, url="https://test.com/p4", sold_count=400),
            Product(name="Popular Product 5", price=80000, url="https://test.com/p5", sold_count=200),
            Product(name="Popular Product 6", price=70000, url="https://test.com/p6", sold_count=100),
        ]
        
        self.mock_url_builder.build_search_url.return_value = test_url
        mock_batch_client.get.return_value = test_html
        self.mock_html_parser.parse_products.return_value = test_products
        
        result = self.scraper.scrape_by_popularity(keyword=test_keyword, top_n=5, page=0)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 5)
        self.assertEqual(result.products[0].name, "Popular Product 1")
        self.assertEqual(result.products[0].sold_count, 1000)
        self.assertEqual(result.url, test_url)
        
        # Verify sort_by_price=False was passed
        self.mock_url_builder.build_search_url.assert_called_once_with(test_keyword, sort_by_price=False, page=0)
        mock_batch_client.get.assert_called_once_with(test_url, timeout=60)
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_by_popularity_custom_top_n(self, mock_batch_client_class):
        """Test scrape_by_popularity with custom top_n value"""
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keyword = "semen"
        test_html = "<html>test</html>"
        
        test_products = [
            Product(name=f"Product {i}", price=10000*i, url=f"https://test.com/p{i}", sold_count=1000-i*100)
            for i in range(1, 11)
        ]
        
        self.mock_url_builder.build_search_url.return_value = "https://test.com/search"
        mock_batch_client.get.return_value = test_html
        self.mock_html_parser.parse_products.return_value = test_products
        
        result = self.scraper.scrape_by_popularity(keyword=test_keyword, top_n=3, page=0)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 3)
        self.assertEqual(result.products[0].sold_count, 900)
        self.assertEqual(result.products[1].sold_count, 800)
        self.assertEqual(result.products[2].sold_count, 700)
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_by_popularity_filters_null_sold_count(self, mock_batch_client_class):
        """Test that products with null sold_count are filtered out"""
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_products = [
            Product(name="Product 1", price=10000, url="https://test.com/p1", sold_count=500),
            Product(name="Product 2", price=20000, url="https://test.com/p2", sold_count=None),
            Product(name="Product 3", price=30000, url="https://test.com/p3", sold_count=300),
            Product(name="Product 4", price=40000, url="https://test.com/p4", sold_count=0),
        ]
        
        self.mock_url_builder.build_search_url.return_value = "https://test.com/search"
        mock_batch_client.get.return_value = "<html>test</html>"
        self.mock_html_parser.parse_products.return_value = test_products
        
        result = self.scraper.scrape_by_popularity(keyword="test", top_n=5, page=0)
        
        self.assertTrue(result.success)
        # Should only include products with sold_count > 0
        self.assertEqual(len(result.products), 2)
        self.assertEqual(result.products[0].sold_count, 500)
        self.assertEqual(result.products[1].sold_count, 300)
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_by_popularity_failure(self, mock_batch_client_class):
        """Test scrape_by_popularity error handling"""
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_keyword = "test"
        mock_batch_client.get.side_effect = Exception("Network error")
        self.mock_url_builder.build_search_url.return_value = "https://test.com/search"
        
        result = self.scraper.scrape_by_popularity(keyword=test_keyword, top_n=5, page=0)
        
        self.assertFalse(result.success)
        self.assertEqual(len(result.products), 0)
        self.assertIn("Network error", result.error_message)
        self.assertEqual(result.url, "https://test.com/search")
    
    @patch('api.mitra10.scraper.BatchPlaywrightClient')
    def test_scrape_by_popularity_no_products_with_sales(self, mock_batch_client_class):
        """Test when no products have valid sold_count"""
        mock_batch_client = MagicMock()
        mock_batch_client_class.return_value.__enter__.return_value = mock_batch_client
        
        test_products = [
            Product(name="Product 1", price=10000, url="https://test.com/p1", sold_count=None),
            Product(name="Product 2", price=20000, url="https://test.com/p2", sold_count=0),
        ]
        
        self.mock_url_builder.build_search_url.return_value = "https://test.com/search"
        mock_batch_client.get.return_value = "<html>test</html>"
        self.mock_html_parser.parse_products.return_value = test_products
        
        result = self.scraper.scrape_by_popularity(keyword="test", top_n=5, page=0)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 0)
