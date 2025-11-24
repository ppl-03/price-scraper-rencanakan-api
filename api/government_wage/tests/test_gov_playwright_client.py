import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from api.government_wage.gov_playwright_client import GovernmentWagePlaywrightClient
from api.interfaces import HttpClientError


class TestGovernmentWagePlaywrightClient(unittest.TestCase):
    
    def setUp(self):
        self.client = GovernmentWagePlaywrightClient()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        try:
            self.client.close()
        except Exception:
            pass
        if self.loop:
            self.loop.close()
    
    def test_init_values(self):
        client = GovernmentWagePlaywrightClient(
            headless=False,
            browser_type="firefox",
            region_label="Kab. Semarang",
            auto_select_region=False,
            search_keyword="test"
        )
        self.assertFalse(client.headless)
        self.assertEqual(client.browser_type, "firefox")
        self.assertEqual(client.region_label, "Kab. Semarang")
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_ensure_browser_types(self, mock_playwright):
        for browser_type in ["chromium", "firefox", "webkit"]:
            with self.subTest(browser_type=browser_type):
                client = GovernmentWagePlaywrightClient(browser_type=browser_type)
                mock_pw, mock_browser, mock_context, mock_page = self._setup_mocks(mock_playwright)
                self.loop.run_until_complete(client._ensure_browser())
                getattr(mock_pw, browser_type).launch.assert_called_once_with(headless=True)
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_ensure_browser_errors(self, mock_playwright):
        mock_pw = AsyncMock()
        mock_playwright.return_value.start = AsyncMock(return_value=mock_pw)
        self.client.browser_type = "invalid"
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(self.client._ensure_browser())
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_ensure_browser_reuses_instances(self, mock_playwright):
        mock_pw, _, _, _ = self._setup_mocks(mock_playwright)
        self.loop.run_until_complete(self.client._ensure_browser())
        self.loop.run_until_complete(self.client._ensure_browser())
        mock_playwright.return_value.start.assert_called_once()
    
    def test_get_methods(self):
        with patch.object(self.client, '_async_get', new_callable=AsyncMock) as mock_async:
            mock_async.return_value = "<html>test</html>"
            result = self.client.get("http://test.com")
            self.assertEqual(result, "<html>test</html>")
            
            mock_async.side_effect = asyncio.TimeoutError()
            with self.assertRaises(HttpClientError):
                self.client.get("http://test.com", timeout=1)
            
            mock_async.side_effect = RuntimeError("error")
            with self.assertRaises(HttpClientError):
                self.client.get("http://test.com")
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_async_get_success(self, mock_playwright):
        mock_pw, mock_browser, mock_context, mock_page = self._setup_mocks(mock_playwright)
        mock_response = AsyncMock(ok=True, status=200)
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.wait_for_selector = AsyncMock()
        mock_page.select_option = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[5, "Test"])
        mock_page.content = AsyncMock(return_value="<html>test</html>")
        
        self.client.auto_select_region = True
        self.client.region_label = "Kab. Cilacap"
        result = self.loop.run_until_complete(self.client._async_get("http://test.com"))
        
        self.assertEqual(result, "<html>test</html>")
        mock_page.select_option.assert_called_once()
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_async_get_errors(self, mock_playwright):
        mock_pw, mock_browser, mock_context, mock_page = self._setup_mocks(mock_playwright)
        
        mock_response = AsyncMock(ok=False, status=404)
        mock_page.goto = AsyncMock(return_value=mock_response)
        with self.assertRaises(HttpClientError):
            self.loop.run_until_complete(self.client._async_get("http://test.com"))
        
        mock_page.goto = AsyncMock(return_value=None)
        with self.assertRaises(HttpClientError):
            self.loop.run_until_complete(self.client._async_get("http://test.com"))
        
        mock_page.goto = AsyncMock(side_effect=RuntimeError("fail"))
        with self.assertRaises(HttpClientError):
            self.loop.run_until_complete(self.client._async_get("http://test.com"))
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_async_get_region_fallback(self, mock_playwright):
        mock_pw, mock_browser, mock_context, mock_page = self._setup_mocks(mock_playwright)
        mock_response = AsyncMock(ok=True)
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.wait_for_selector = AsyncMock()
        mock_page.select_option = AsyncMock(side_effect=RuntimeError("fail"))
        mock_page.click = AsyncMock()
        mock_locator = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_locator.click = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[5, "Test"])
        mock_page.content = AsyncMock(return_value="<html>test</html>")
        
        self.client.auto_select_region = True
        self.client.region_label = "Kab. Cilacap"
        self.loop.run_until_complete(self.client._async_get("http://test.com"))
        
        mock_page.click.assert_called_once()
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_async_get_region_failure(self, mock_playwright):
        _, _, _, mock_page = self._setup_mocks(mock_playwright)
        mock_response = AsyncMock(ok=True)
        mock_page.goto = AsyncMock(return_value=mock_response)
        
        call_count = [0]
        def wait_selector_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("timeout")
            return AsyncMock()
        
        mock_page.wait_for_selector = AsyncMock(side_effect=wait_selector_side_effect)
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[5, "Test"])
        mock_page.content = AsyncMock(return_value="<html>test</html>")
        
        self.client.auto_select_region = True
        result = self.loop.run_until_complete(self.client._async_get("http://test.com"))
        self.assertEqual(result, "<html>test</html>")
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_async_get_with_search(self, mock_playwright):
        mock_pw, mock_browser, mock_context, mock_page = self._setup_mocks(mock_playwright)
        mock_response = AsyncMock(ok=True)
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.wait_for_selector = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[5, "Test"])
        mock_page.content = AsyncMock(return_value="<html>test</html>")
        
        self.client.search_keyword = "test"
        self.client.auto_select_region = False
        self.loop.run_until_complete(self.client._async_get("http://test.com"))
        
        mock_page.fill.assert_called_once()
    
    @patch('api.government_wage.gov_playwright_client.async_playwright')
    def test_async_get_exception_handling(self, mock_playwright):
        _, _, _, mock_page = self._setup_mocks(mock_playwright)
        mock_response = AsyncMock(ok=True)
        mock_page.goto = AsyncMock(return_value=mock_response)
        
        call_count = [0]
        def wait_selector_side_effect(selector, *args, **kwargs):
            call_count[0] += 1
            if selector == ".dataTables_filter input":
                raise RuntimeError("fail")
            return AsyncMock()
        
        mock_page.wait_for_selector = AsyncMock(side_effect=wait_selector_side_effect)
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=RuntimeError("fail"))
        mock_page.content = AsyncMock(return_value="<html>test</html>")
        
        self.client.search_keyword = "test"
        self.client.auto_select_region = False
        result = self.loop.run_until_complete(self.client._async_get("http://test.com"))
        self.assertEqual(result, "<html>test</html>")
    
    def test_close_and_context_manager(self):
        self.client.playwright = MagicMock()
        self.client.browser = MagicMock()
        
        with patch.object(self.client, '_async_close', new_callable=AsyncMock):
            self.client.close()
        
        self.assertIsNone(self.client.browser)
        
        result = self.client.__enter__()
        self.assertEqual(result, self.client)
        
        with patch.object(self.client, 'close') as mock_close:
            self.client.__exit__(None, None, None)
            mock_close.assert_called_once()
    
    def test_async_close(self):
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_pw = AsyncMock()
        
        self.client.page = mock_page
        self.client.context = mock_context
        self.client.browser = mock_browser
        self.client.playwright = mock_pw
        
        self.loop.run_until_complete(self.client._async_close())
        
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()
    
    def test_selectors(self):
        self.assertEqual(
            GovernmentWagePlaywrightClient.REGION_SELECT_SELECTOR,
            "select.form-control"
        )
        self.assertEqual(
            GovernmentWagePlaywrightClient.SEARCH_INPUT_SELECTOR,
            ".dataTables_filter input"
        )
    
    def _setup_mocks(self, mock_playwright):
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.start = AsyncMock(return_value=mock_pw)
        mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.firefox.launch = AsyncMock(return_value=mock_browser)
        mock_pw.webkit.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        return mock_pw, mock_browser, mock_context, mock_page


if __name__ == '__main__':
    unittest.main()