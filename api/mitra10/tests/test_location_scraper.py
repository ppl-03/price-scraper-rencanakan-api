import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from api.mitra10.location_scraper import Mitra10LocationScraper
import asyncio


class TestMitra10LocationScraper(unittest.TestCase):

    def setUp(self):
        self.scraper = Mitra10LocationScraper()
        self.url = "https://www.mitra10.com/"

    @patch("api.mitra10.location_scraper.BatchPlaywrightClient")
    def test_comprehensive_location_scraper_coverage(self, mock_batch):
        """Comprehensive test to achieve 100% code coverage for Mitra10LocationScraper"""
        
        # Test 1: scrape_locations success path
        mock_instance = mock_batch.return_value.__enter__.return_value
        mock_client = AsyncMock()
        mock_instance.client = mock_client
        mock_page = MagicMock()
        mock_client.page = mock_page

        # Mock successful HTML content with locations
        mock_html_content = """
        <html>
            <div role="presentation">
                <li><span>MITRA10 Jakarta Pusat</span></li>
                <li><span>MITRA10 Bandung</span></li>
                <li><span>Surabaya Store</span></li>
            </div>
        </html>
        """

        # Set up all required async mocks for successful flow
        mock_client._ensure_browser = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        # Mock popup handling - first call returns 1 (popup exists), second returns 0
        mock_popup_locator = MagicMock()
        mock_popup_locator.count = AsyncMock(return_value=1)
        
        # Mock store button locator
        mock_store_locator = MagicMock()
        mock_store_button = MagicMock()
        mock_store_locator.first = mock_store_button
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        mock_store_button.click = AsyncMock()
        
        # Configure page.locator to return appropriate mocks based on selector
        def locator_side_effect(selector):
            if "MuiDialog-root" in selector or "popup-promo" in selector:
                return mock_popup_locator
            elif "button.MuiButtonBase-root.jss368" in selector:
                return mock_store_locator
            return MagicMock()
            
        mock_page.locator.side_effect = locator_side_effect
        mock_page.mouse = MagicMock()
        mock_page.mouse.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html_content)

        # Test successful scraping
        result = self.scraper.scrape_locations()
        self.assertTrue(result["success"])
        self.assertEqual(len(result["locations"]), 3)
        self.assertIn("Jakarta Pusat", result["locations"])
        self.assertIn("Bandung", result["locations"])
        self.assertIn("Surabaya Store", result["locations"])
        self.assertEqual(result["error_message"], "")

        # Verify all methods were called
        mock_client._ensure_browser.assert_called_once()
        mock_page.goto.assert_called_with("https://www.mitra10.com/", timeout=60000)
        mock_page.evaluate.assert_called()
        mock_page.wait_for_load_state.assert_called_with("networkidle")

    @patch("api.mitra10.location_scraper.BatchPlaywrightClient")
    def test_scrape_locations_failure_handling(self, mock_batch):
        """Test error handling in scrape_locations"""
        mock_instance = mock_batch.return_value.__enter__.return_value
        mock_client = AsyncMock()
        mock_instance.client = mock_client

        # Simulate error in _extract_locations
        mock_client._ensure_browser = AsyncMock(side_effect=RuntimeError("Browser failed"))

        result = self.scraper.scrape_locations()
        self.assertFalse(result["success"])
        self.assertEqual(result["locations"], [])
        self.assertIn("Browser failed", result["error_message"])

    def test_extract_locations_click_retry_mechanism(self):
        """Test click retry mechanism in _extract_locations"""
        mock_client = AsyncMock()
        mock_page = MagicMock()
        mock_client.page = mock_page

        # Mock HTML content with locations
        mock_html_content = """
        <div role="presentation">
            <li><span>MITRA10 Test Location</span></li>
        </div>
        """

        # Set up basic mocks
        mock_client._ensure_browser = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        # Mock no popup scenario
        mock_popup_locator = MagicMock()
        mock_popup_locator.count = AsyncMock(return_value=0)
        
        # Mock store button with click retry scenario
        mock_store_locator = MagicMock()
        mock_store_button = MagicMock()
        mock_store_locator.first = mock_store_button
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        
        # First two clicks fail, third succeeds
        mock_store_button.click = AsyncMock(side_effect=[
            Exception("Click failed attempt 1"),
            Exception("Click failed attempt 2"), 
            None  # Success on third attempt
        ])
        
        def locator_side_effect(selector):
            if "MuiDialog-root" in selector or "popup-promo" in selector:
                return mock_popup_locator
            elif "button.MuiButtonBase-root.jss368" in selector:
                return mock_store_locator
            return MagicMock()
            
        mock_page.locator.side_effect = locator_side_effect
        mock_page.mouse = MagicMock()
        mock_page.mouse.click = AsyncMock()
        mock_page.mouse.move = AsyncMock()
        mock_page.mouse.down = AsyncMock()
        mock_page.mouse.up = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html_content)

        result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
        self.assertEqual(result, ["Test Location"])
        
        # Verify click retry mechanism was used
        self.assertEqual(mock_store_button.click.call_count, 3)
        self.assertEqual(mock_page.mouse.move.call_count, 2)  # Called for failed attempts
        self.assertEqual(mock_page.mouse.down.call_count, 2)
        self.assertEqual(mock_page.mouse.up.call_count, 2)

    def test_extract_locations_click_timeout_failure(self):
        """Test click timeout failure after 3 attempts"""
        mock_client = AsyncMock()
        mock_page = MagicMock()
        mock_client.page = mock_page

        # Set up basic mocks
        mock_client._ensure_browser = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        # Mock no popup scenario
        mock_popup_locator = MagicMock()
        mock_popup_locator.count = AsyncMock(return_value=0)
        
        # Mock store button that always fails to click
        mock_store_locator = MagicMock()
        mock_store_button = MagicMock()
        mock_store_locator.first = mock_store_button
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        mock_store_button.click = AsyncMock(side_effect=Exception("Click always fails"))
        
        def locator_side_effect(selector):
            if "MuiDialog-root" in selector or "popup-promo" in selector:
                return mock_popup_locator
            elif "button.MuiButtonBase-root.jss368" in selector:
                return mock_store_locator
            return MagicMock()
            
        mock_page.locator.side_effect = locator_side_effect
        mock_page.mouse = MagicMock()
        mock_page.mouse.click = AsyncMock()
        mock_page.mouse.move = AsyncMock()
        mock_page.mouse.down = AsyncMock()
        mock_page.mouse.up = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()

        # This should raise TimeoutError
        with self.assertRaises(TimeoutError) as context:
            asyncio.run(self.scraper._extract_locations(mock_client, self.url))
        
        self.assertIn("Failed to click store selector after 3 attempts", str(context.exception))
        self.assertEqual(mock_store_button.click.call_count, 3)

    def test_extract_locations_popup_handling(self):
        """Test popup detection and handling"""
        mock_client = AsyncMock()
        mock_page = MagicMock()
        mock_client.page = mock_page

        mock_html_content = """
        <div role="presentation">
            <li><span>MITRA10 Popup Test</span></li>
        </div>
        """

        # Set up basic mocks
        mock_client._ensure_browser = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        # Mock popup exists scenario
        mock_popup_locator = MagicMock()
        mock_popup_locator.count = AsyncMock(return_value=1)  # Popup exists
        
        # Mock store button
        mock_store_locator = MagicMock()
        mock_store_button = MagicMock()
        mock_store_locator.first = mock_store_button
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        mock_store_button.click = AsyncMock()
        
        def locator_side_effect(selector):
            if "MuiDialog-root" in selector or "popup-promo" in selector:
                return mock_popup_locator
            elif "button.MuiButtonBase-root.jss368" in selector:
                return mock_store_locator
            return MagicMock()
            
        mock_page.locator.side_effect = locator_side_effect
        mock_page.mouse = MagicMock()
        mock_page.mouse.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html_content)

        result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
        self.assertEqual(result, ["Popup Test"])
        
        # Verify popup handling was triggered
        mock_popup_locator.count.assert_called_once()
        mock_page.mouse.click.assert_called_with(100, 100)  # Popup close click

    def test_extract_locations_empty_result(self):
        """Test handling of empty location results"""
        mock_client = AsyncMock()
        mock_page = MagicMock()
        mock_client.page = mock_page

        # HTML with no valid locations
        mock_html_content = "<html><body>No locations found</body></html>"

        # Set up basic mocks
        mock_client._ensure_browser = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        # Mock no popup scenario
        mock_popup_locator = MagicMock()
        mock_popup_locator.count = AsyncMock(return_value=0)
        
        # Mock store button
        mock_store_locator = MagicMock()
        mock_store_button = MagicMock()
        mock_store_locator.first = mock_store_button
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        mock_store_button.click = AsyncMock()
        
        def locator_side_effect(selector):
            if "MuiDialog-root" in selector or "popup-promo" in selector:
                return mock_popup_locator
            elif "button.MuiButtonBase-root.jss368" in selector:
                return mock_store_locator
            return MagicMock()
            
        mock_page.locator.side_effect = locator_side_effect
        mock_page.mouse = MagicMock()
        mock_page.mouse.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html_content)

        result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
        self.assertEqual(result, [])

    def test_extract_locations_evaluate_exception_handling(self):
        """Test exception handling in evaluate JavaScript call"""
        mock_client = AsyncMock()
        mock_page = MagicMock()
        mock_client.page = mock_page

        mock_html_content = """
        <div role="presentation">
            <li><span>MITRA10 Exception Test</span></li>
        </div>
        """

        # Set up basic mocks
        mock_client._ensure_browser = AsyncMock()
        mock_page.goto = AsyncMock()
        # Mock evaluate to raise exception (should be caught and ignored)
        mock_page.evaluate = AsyncMock(side_effect=Exception("JS evaluation failed"))
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        # Mock no popup scenario
        mock_popup_locator = MagicMock()
        mock_popup_locator.count = AsyncMock(return_value=0)
        
        # Mock store button
        mock_store_locator = MagicMock()
        mock_store_button = MagicMock()
        mock_store_locator.first = mock_store_button
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        mock_store_button.click = AsyncMock()
        
        def locator_side_effect(selector):
            if "MuiDialog-root" in selector or "popup-promo" in selector:
                return mock_popup_locator
            elif "button.MuiButtonBase-root.jss368" in selector:
                return mock_store_locator
            return MagicMock()
            
        mock_page.locator.side_effect = locator_side_effect
        mock_page.mouse = MagicMock()
        mock_page.mouse.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html_content)

        # Should complete successfully despite evaluate exception
        result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
        self.assertEqual(result, ["Exception Test"])
        
        # Verify evaluate was called and failed
        mock_page.evaluate.assert_called_once()

    def test_extract_locations_popup_exception_handling(self):
        """Test exception handling in popup close logic"""
        mock_client = AsyncMock()
        mock_page = MagicMock()
        mock_client.page = mock_page

        mock_html_content = """
        <div role="presentation">
            <li><span>MITRA10 Popup Exception</span></li>
        </div>
        """

        # Set up basic mocks
        mock_client._ensure_browser = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        # Mock popup locator that throws exception when counting
        mock_popup_locator = MagicMock()
        mock_popup_locator.count = AsyncMock(side_effect=Exception("Popup count failed"))
        
        # Mock store button
        mock_store_locator = MagicMock()
        mock_store_button = MagicMock()
        mock_store_locator.first = mock_store_button
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        mock_store_button.click = AsyncMock()
        
        def locator_side_effect(selector):
            if "MuiDialog-root" in selector or "popup-promo" in selector:
                return mock_popup_locator
            elif "button.MuiButtonBase-root.jss368" in selector:
                return mock_store_locator
            return MagicMock()
            
        mock_page.locator.side_effect = locator_side_effect
        mock_page.mouse = MagicMock()
        mock_page.mouse.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html_content)

        # Should complete successfully despite popup exception
        result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
        self.assertEqual(result, ["Popup Exception"])
