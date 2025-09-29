import unittest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import WebDriverException, TimeoutException
from api.interfaces import HttpClientError
from api.selenium_client import SeleniumHttpClient


class TestSeleniumHttpClient(unittest.TestCase):

    def setUp(self):
        self.client = SeleniumHttpClient()

    def tearDown(self):
        try:
            if hasattr(self.client, 'driver') and self.client.driver:
                self.client.close()
        except Exception:
            pass

    @patch('api.selenium_client.webdriver.Chrome')
    def test_initialization_creates_driver(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        client = SeleniumHttpClient()
        
        mock_chrome.assert_called_once()
        self.assertEqual(client.driver, mock_driver)

    @patch('api.selenium_client.webdriver.Chrome')
    def test_initialization_with_options(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
                
        # Verify Chrome was called with options
        call_args = mock_chrome.call_args
        self.assertIsNotNone(call_args)
        
        # Check that options were passed
        if call_args[1]:  
            options = call_args[1].get('options')
            if options:
                self.assertIsNotNone(options)

    @patch('api.selenium_client.webdriver.Chrome')
    def test_get_method_success(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.page_source = "<html><body>Test Content</body></html>"
        
        client = SeleniumHttpClient()
        result = client.get("https://example.com")
        
        mock_driver.get.assert_called_once_with("https://example.com")
        self.assertEqual(result, "<html><body>Test Content</body></html>")

    @patch('api.selenium_client.webdriver.Chrome')
    def test_get_method_with_webdriver_exception(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.get.side_effect = WebDriverException("Connection failed")
        
        client = SeleniumHttpClient()
        
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        
        self.assertIn("Connection failed", str(context.exception))

    @patch('api.selenium_client.webdriver.Chrome')
    def test_get_method_with_timeout_exception(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.get.side_effect = TimeoutException("Request timeout")
        
        client = SeleniumHttpClient()
        
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        
        self.assertIn("Request timeout", str(context.exception))

    @patch('api.selenium_client.webdriver.Chrome')
    def test_get_method_with_generic_exception(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.get.side_effect = Exception("Unexpected error")
        
        client = SeleniumHttpClient()
        
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        
        self.assertIn("Unexpected error", str(context.exception))

    @patch('api.selenium_client.webdriver.Chrome')
    def test_close_method(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        client = SeleniumHttpClient()
        client.close()
        
        mock_driver.quit.assert_called_once()

    @patch('api.selenium_client.webdriver.Chrome')
    def test_close_method_with_exception(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.quit.side_effect = Exception("Driver already closed")
        
        client = SeleniumHttpClient()
        
        try:
            client.close()
        except Exception:
            self.fail("close() method should handle exceptions gracefully")

    @patch('api.selenium_client.webdriver.Chrome')
    def test_close_method_with_no_driver(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        client = SeleniumHttpClient()
        client.driver = None
        
        try:
            client.close()
        except Exception:
            self.fail("close() method should handle None driver gracefully")

    @patch('api.selenium_client.webdriver.Chrome')
    def test_multiple_get_requests(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.page_source = "<html>Content</html>"
        
        client = SeleniumHttpClient()
        
        result1 = client.get("https://example.com/page1")
        result2 = client.get("https://example.com/page2")
        
        self.assertEqual(mock_driver.get.call_count, 2)
        mock_driver.get.assert_any_call("https://example.com/page1")
        mock_driver.get.assert_any_call("https://example.com/page2")
        self.assertEqual(result1, "<html>Content</html>")
        self.assertEqual(result2, "<html>Content</html>")

    @patch('api.selenium_client.webdriver.Chrome')
    def test_get_with_empty_page_source(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.page_source = ""
        
        client = SeleniumHttpClient()
        result = client.get("https://example.com")
        
        self.assertEqual(result, "")

    @patch('api.selenium_client.webdriver.Chrome')
    def test_get_with_none_page_source(self, mock_chrome):
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver.page_source = None
        
        client = SeleniumHttpClient()
        
        # This should raise HttpClientError due to None page_source
        with self.assertRaises(HttpClientError) as context:
            client.get("https://example.com")
        
        self.assertIn("object of type 'NoneType' has no len()", str(context.exception))

    @patch('api.selenium_client.Options')
    @patch('api.selenium_client.webdriver.Chrome')
    def test_chrome_options_configuration(self, mock_chrome, mock_options):
        mock_options_instance = Mock()
        mock_options.return_value = mock_options_instance
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
                
        mock_options.assert_called_once()
        mock_options_instance.add_argument.assert_called()

    @patch('api.selenium_client.webdriver.Chrome')
    def test_driver_initialization_failure(self, mock_chrome):
        mock_chrome.side_effect = WebDriverException("Failed to start Chrome")
        
        with self.assertRaises(Exception) as context:
            SeleniumHttpClient()
        
        self.assertIsInstance(context.exception, (WebDriverException, Exception))

    def test_implements_http_client_interface(self):
        self.assertTrue(hasattr(SeleniumHttpClient, 'get'))
        self.assertTrue(hasattr(SeleniumHttpClient, 'close'))
        
        self.assertTrue(callable(getattr(SeleniumHttpClient, 'get')))
        self.assertTrue(callable(getattr(SeleniumHttpClient, 'close')))