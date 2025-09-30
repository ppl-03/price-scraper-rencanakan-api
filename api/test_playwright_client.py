import unittest
from unittest.mock import Mock, patch, AsyncMock
from api.interfaces import HttpClientError
from api.playwright_client import PlaywrightHttpClient, BatchPlaywrightClient


class TestPlaywrightHttpClient(unittest.TestCase):

    def setUp(self):
        self.client = None

    def tearDown(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

    @patch('api.playwright_client.async_playwright')
    def test_initialization_creates_client(self, mock_playwright):
        mock_context = Mock()
        mock_playwright.return_value.__aenter__.return_value = mock_context
        
        client = PlaywrightHttpClient()
        self.assertIsNotNone(client)
        self.assertEqual(client.browser_type, "chromium")
        self.assertTrue(client.headless)

    def test_initialization_with_custom_options(self):
        client = PlaywrightHttpClient(headless=False, browser_type="firefox")
        self.assertEqual(client.browser_type, "firefox")
        self.assertFalse(client.headless)

    @patch('api.playwright_client.async_playwright')
    def test_get_method_success(self, mock_playwright):
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        
        mock_context.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = AsyncMock()
        mock_browser.new_context.return_value.new_page.return_value = mock_page
        mock_page.content.return_value = "<html><body>Test Content</body></html>"
        
        mock_playwright.return_value.__aenter__.return_value = mock_context
        
        client = PlaywrightHttpClient()
        self.client = client
        
        with patch.object(client, '_ensure_browser', new_callable=AsyncMock):
            with patch.object(client.page, 'goto', new_callable=AsyncMock):
                with patch.object(client.page, 'content', new_callable=AsyncMock) as mock_content:
                    mock_content.return_value = "<html><body>Test Content</body></html>"
                    
                    result = client.get("https://example.com")
                    self.assertIn("Test Content", result)

    @patch('api.playwright_client.async_playwright')
    def test_get_method_with_timeout(self, mock_playwright):
        mock_context = AsyncMock()
        mock_playwright.return_value.__aenter__.return_value = mock_context
        
        client = PlaywrightHttpClient()
        self.client = client
        
        with patch.object(client, '_ensure_browser', new_callable=AsyncMock):
            with patch.object(client.page, 'goto', new_callable=AsyncMock):
                with patch.object(client.page, 'content', new_callable=AsyncMock) as mock_content:
                    mock_content.return_value = "<html><body>Test</body></html>"
                    
                    result = client.get("https://example.com", timeout=60)
                    self.assertIsNotNone(result)

    @patch('api.playwright_client.async_playwright')
    def test_get_method_handles_exceptions(self, mock_playwright):
        mock_context = AsyncMock()
        mock_playwright.return_value.__aenter__.return_value = mock_context
        
        client = PlaywrightHttpClient()
        self.client = client
        
        with patch.object(client, '_ensure_browser', new_callable=AsyncMock):
            with patch.object(client.page, 'goto', new_callable=AsyncMock, side_effect=Exception("Navigation error")):
                
                with self.assertRaises(HttpClientError):
                    client.get("https://invalid-url.com")

    def test_browser_type_validation(self):
        client1 = PlaywrightHttpClient(browser_type="chromium")
        self.assertEqual(client1.browser_type, "chromium")
        
        client2 = PlaywrightHttpClient(browser_type="firefox")
        self.assertEqual(client2.browser_type, "firefox")
        
        client3 = PlaywrightHttpClient(browser_type="webkit")
        self.assertEqual(client3.browser_type, "webkit")

    @patch('api.playwright_client.async_playwright')
    def test_close_method(self, mock_playwright):
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_playwright.return_value.__aenter__.return_value = mock_context
        
        client = PlaywrightHttpClient()
        client.browser = mock_browser
        
        client.close()
        self.assertIsNone(client.browser)
        self.assertIsNone(client.context)
        self.assertIsNone(client.page)

    def test_client_interface_compliance(self):
        self.assertTrue(hasattr(PlaywrightHttpClient, 'get'))
        self.assertTrue(hasattr(PlaywrightHttpClient, 'close'))
        
        self.assertTrue(callable(getattr(PlaywrightHttpClient, 'get')))
        self.assertTrue(callable(getattr(PlaywrightHttpClient, 'close')))


class TestBatchPlaywrightClient(unittest.TestCase):

    @patch('api.playwright_client.PlaywrightHttpClient')
    def test_batch_client_context_manager(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        with BatchPlaywrightClient() as client:
            self.assertEqual(client, mock_client)
        
        mock_client.close.assert_called_once()

    @patch('api.playwright_client.PlaywrightHttpClient')
    def test_batch_client_get_method(self, mock_client_class):
        mock_client = Mock()
        mock_client.get.return_value = "<html><body>Batch Test</body></html>"
        mock_client_class.return_value = mock_client
        
        with BatchPlaywrightClient() as client:
            result = client.get("https://example.com")
            self.assertEqual(result, "<html><body>Batch Test</body></html>")
            mock_client.get.assert_called_once_with("https://example.com", timeout=30)

    def test_batch_client_error_without_context(self):
        batch_client = BatchPlaywrightClient()
        
        with self.assertRaises(RuntimeError) as context:
            batch_client.get("https://example.com")
        
        self.assertIn("context manager", str(context.exception))


if __name__ == '__main__':
    unittest.main()