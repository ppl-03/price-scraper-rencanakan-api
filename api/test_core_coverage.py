from unittest import TestCase
from unittest.mock import Mock, patch
from api.interfaces import HttpClientError, UrlBuilderError, HtmlParserError
from api.core import BaseHttpClient, BaseUrlBuilder, BasePriceScraper, clean_price_digits
class TestCoreModuleCoverage(TestCase):
    def test_clean_price_digits_none_input(self):
        with self.assertRaises(TypeError) as context:
            clean_price_digits(None)
        self.assertIn("price_string cannot be None", str(context.exception))
    def test_clean_price_digits_non_string_input(self):
        with self.assertRaises(TypeError) as context:
            clean_price_digits(123)
        self.assertIn("price_string must be a string", str(context.exception))
    def test_clean_price_digits_empty_string(self):
        result = clean_price_digits("")
        self.assertEqual(result, 0)
    def test_clean_price_digits_no_digits(self):
        result = clean_price_digits("No digits here!")
        self.assertEqual(result, 0)
    def test_clean_price_digits_with_digits(self):
        result = clean_price_digits("Rp 55.000")
        self.assertEqual(result, 55000)
    @patch('api.core.requests.Session')
    def test_http_client_request_retry_mechanism(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = [
            Exception("Connection failed"),
            Exception("Timeout"),
            Mock(content=b"Success", encoding="utf-8")
        ]
        client = BaseHttpClient(max_retries=3)
        result = client.get("https://example.com")
        self.assertEqual(result, "Success")
        self.assertEqual(mock_session.get.call_count, 3)
    @patch('api.core.requests.Session')
    def test_http_client_max_retries_exhausted(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = Exception("Always fails")
        client = BaseHttpClient(max_retries=2)
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        self.assertIn("Always fails", str(context.exception))
        self.assertEqual(mock_session.get.call_count, 2)
    @patch('api.core.time.sleep')
    @patch('api.core.time.time')
    def test_http_client_rate_limiting(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 0.5, 1.0]  # First call, then 0.5s later, then 1s later
        client = BaseHttpClient()
        client.last_request_time = 0
        client._rate_limit()
        mock_sleep.assert_called_once()
    def test_base_url_builder_keyword_validation(self):
        builder = BaseUrlBuilder("https://example.com", "/search")
        with self.assertRaises(UrlBuilderError) as context:
            builder.build_search_url("")
        self.assertIn("Keyword cannot be empty", str(context.exception))
    def test_base_url_builder_page_validation(self):
        builder = BaseUrlBuilder("https://example.com", "/search")
        with self.assertRaises(UrlBuilderError) as context:
            builder.build_search_url("test", page=-1)
        self.assertIn("Page number cannot be negative", str(context.exception))
    def test_base_price_scraper_url_builder_error(self):
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        mock_url_builder.build_search_url.side_effect = UrlBuilderError("URL error")
        scraper = BasePriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        result = scraper.scrape_products("test")
        self.assertFalse(result.success)
        self.assertIn("URL error", result.error_message)
    def test_base_price_scraper_http_client_error(self):
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        mock_url_builder.build_search_url.return_value = "https://example.com/search"
        mock_http_client.get.side_effect = HttpClientError("Network error")
        scraper = BasePriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        result = scraper.scrape_products("test")
        self.assertFalse(result.success)
        self.assertIn("Network error", result.error_message)
    def test_base_price_scraper_html_parser_error(self):
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        mock_url_builder.build_search_url.return_value = "https://example.com/search"
        mock_http_client.get.return_value = "<html>test</html>"
        mock_html_parser.parse_products.side_effect = Exception("Parser error")
        scraper = BasePriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        result = scraper.scrape_products("test")
        self.assertFalse(result.success)
        self.assertIn("Unexpected error", result.error_message)
    @patch('api.core.requests.Session')
    def test_http_client_empty_response(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.content = b""  # Empty response
        mock_response.encoding = "utf-8"
        mock_session.get.return_value = mock_response
        client = BaseHttpClient()
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        self.assertIn("Empty response", str(context.exception))
    @patch('api.core.requests.Session')
    def test_http_client_http_error(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError("404 Client Error")
        http_error.response = mock_response
        mock_session.get.side_effect = http_error
        client = BaseHttpClient()
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        self.assertIn("HTTP error 404", str(context.exception))
    @patch('api.core.requests.Session')
    def test_http_client_connection_error(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        import requests
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        client = BaseHttpClient()
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        self.assertIn("Connection error", str(context.exception))
    @patch('api.core.requests.Session')
    def test_http_client_timeout_error(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        import requests
        mock_session.get.side_effect = requests.exceptions.Timeout("Request timeout")
        client = BaseHttpClient()
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        self.assertIn("Request timeout", str(context.exception))
    @patch('api.core.requests.Session')
    def test_http_client_request_exception(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        import requests
        mock_session.get.side_effect = requests.exceptions.RequestException("Generic request error")
        client = BaseHttpClient()
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        self.assertIn("Request failed", str(context.exception))
    def test_base_url_builder_build_params(self):
        builder = BaseUrlBuilder("https://example.com", "/search")
        params = builder._build_params("test keyword", True, 5)
        expected = {
            'keyword': 'test keyword',
            'page': 5,
            'sort': 'price_asc'
        }
        self.assertEqual(params, expected)
        params = builder._build_params("another keyword", False, 0)
        expected = {
            'keyword': 'another keyword',
            'page': 0
        }
        self.assertEqual(params, expected)
    def test_base_price_scraper_http_error_handling(self):
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        mock_url_builder.build_search_url.return_value = "https://example.com/search?keyword=test"
        mock_http_client.get.side_effect = HttpClientError("Network error")
        scraper = BasePriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        result = scraper.scrape_products("test keyword")
        self.assertFalse(result.success)
        self.assertIn("Network error", result.error_message)
    def test_base_price_scraper_html_parser_error_handling(self):
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        mock_url_builder.build_search_url.return_value = "https://example.com/search?keyword=test"
        mock_http_client.get.return_value = "<html><body>Valid HTML</body></html>"
        mock_html_parser.parse_products.side_effect = HtmlParserError("Parsing failed")
        scraper = BasePriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        result = scraper.scrape_products("test keyword")
        self.assertFalse(result.success)
        self.assertIn("Parsing failed", result.error_message)
    def test_base_price_scraper_unexpected_error_handling(self):
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        mock_url_builder.build_search_url.return_value = "https://example.com/search?keyword=test"
        mock_http_client.get.side_effect = ValueError("Unexpected error")
        scraper = BasePriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        result = scraper.scrape_products("test keyword")
        self.assertFalse(result.success)
        self.assertIn("Unexpected error:", result.error_message)

    def test_base_url_builder_successful_url_construction(self):
        builder = BaseUrlBuilder("https://example.com", "/search")
        
        with patch('api.core.logger') as mock_logger:
            url = builder.build_search_url("test product", True, 5)
            
            self.assertIn("example.com", url)
            self.assertIn("keyword=test+product", url)
            self.assertIn("sort=price_asc", url)
            self.assertIn("page=5", url)
            
            mock_logger.debug.assert_called_once()
            self.assertIn("Built URL:", mock_logger.debug.call_args[0][0])

    @patch('api.core.urljoin')
    def test_base_url_builder_exception_handling_in_build_url(self, mock_urljoin):
        builder = BaseUrlBuilder("https://example.com", "/search")
        
        mock_urljoin.side_effect = ValueError("URL join failed")
        
        with self.assertRaises(UrlBuilderError) as context:
            builder.build_search_url("test", True, 0)
        
        self.assertIn("Failed to build URL: URL join failed", str(context.exception))

    def test_base_url_builder_with_various_parameters(self):
        builder = BaseUrlBuilder("https://test.com", "/api/search")
        
        url1 = builder.build_search_url("keyword with spaces", True, 10)
        self.assertIn("sort=price_asc", url1)
        self.assertIn("page=10", url1)
        
        url2 = builder.build_search_url("another keyword", False, 0)
        self.assertNotIn("sort=price_asc", url2)
        self.assertIn("page=0", url2)

    def test_base_price_scraper_successful_scraping(self):
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        
        mock_url_builder.build_search_url.return_value = "https://example.com/search?keyword=test"
        mock_http_client.get.return_value = "<html>Valid HTML</html>"
        mock_html_parser.parse_products.return_value = [
            Mock(name="Test Product", price=100, url="/test")
        ]
        
        scraper = BasePriceScraper(mock_http_client, mock_url_builder, mock_html_parser)
        
        result = scraper.scrape_products("test keyword", True, 0)
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.url, "https://example.com/search?keyword=test")
        self.assertEqual(len(result.products), 1)
        
        mock_url_builder.build_search_url.assert_called_once_with("test keyword", True, 0)
        mock_http_client.get.assert_called_once_with("https://example.com/search?keyword=test")
        mock_html_parser.parse_products.assert_called_once_with("<html>Valid HTML</html>")
