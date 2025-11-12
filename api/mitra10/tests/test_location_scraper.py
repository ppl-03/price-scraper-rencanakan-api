import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from api.mitra10.location_scraper import Mitra10LocationScraper
import asyncio


class TestMitra10LocationScraper(unittest.TestCase):
    def _setup_basic_mocks(self, mock_client, mock_page, popup_count=0):
        mock_store_button = MagicMock()
        mock_page.mouse = MagicMock()
        mock_page.mouse.move = MagicMock()
        mock_page.mouse.down = MagicMock()
        mock_page.mouse.up = MagicMock()
        mock_page.goto = AsyncMock()
        return mock_client, mock_page, mock_store_button

    def setUp(self):
        self.scraper = Mitra10LocationScraper()
        self.url = "https://www.mitra10.com/"

    @patch("api.mitra10.location_scraper.BatchPlaywrightClient")
    def test_scrape_locations_success(self, mock_batch):
        mock_instance = mock_batch.return_value.__enter__.return_value
        mock_client = AsyncMock()
        mock_instance.client = mock_client
        mock_page = MagicMock()
        mock_client.page = mock_page

        # Mock all Playwright async methods and locator logic
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="""
        <div role=\"presentation\">
            <li><span>Jakarta Pusat</span></li>
            <li><span>Bandung</span></li>
            <li><span>Surabaya Store</span></li>
        </div>
        """)
        # Mouse actions
        mock_mouse = MagicMock()
        mock_mouse.move = AsyncMock()
        mock_mouse.down = AsyncMock()
        mock_mouse.up = AsyncMock()
        mock_page.mouse = mock_mouse
        # locator() returns a Locator object with async methods
        mock_locator = MagicMock()
        mock_first = MagicMock()
        mock_first.scroll_into_view_if_needed = AsyncMock()
        mock_first.click = AsyncMock()
        mock_locator.first = mock_first
        mock_page.locator.return_value = mock_locator

        # Patch parser to return expected locations
        with patch('api.mitra10.location_scraper.Mitra10LocationParser') as mock_parser:
            mock_parser.parse.return_value = ["Jakarta Pusat", "Bandung", "Surabaya Store"]
            result = self.scraper.scrape_locations()
            self.assertTrue(result["success"])
            self.assertEqual(len(result["locations"]), 3)
            self.assertIn("Jakarta Pusat", result["locations"])
            self.assertIn("Bandung", result["locations"])
            self.assertIn("Surabaya Store", result["locations"])
            self.assertEqual(result["error_message"], "")

    @patch("api.mitra10.location_scraper.BatchPlaywrightClient")
    def test_scrape_locations_failure(self, mock_batch):
        mock_instance = mock_batch.return_value.__enter__.return_value
        mock_client = MagicMock()
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
        # Set all Playwright async methods as AsyncMock
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="""
        <div role=\"presentation\">
            <li><span>MITRA10 Test Location</span></li>
        </div>
        """)
        # Mouse actions
        mock_mouse = MagicMock()
        mock_mouse.move = AsyncMock()
        mock_mouse.down = AsyncMock()
        mock_mouse.up = AsyncMock()
        mock_page.mouse = mock_mouse
        # Store button
        mock_store_button = MagicMock()
        mock_store_button.click = AsyncMock(side_effect=[
            Exception("Click failed attempt 1"),
            Exception("Click failed attempt 2"),
            None
        ])
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        # Patch locator to return store button
        mock_locator = MagicMock()
        mock_locator.first = mock_store_button
        mock_page.locator.return_value = mock_locator

        # Patch parser
        with patch('api.mitra10.location_scraper.Mitra10LocationParser') as mock_parser:
            mock_parser.parse.return_value = ["Test Location"]
            result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
            self.assertEqual(result, ["Test Location"])
            self.assertEqual(mock_store_button.click.call_count, 3)
            self.assertEqual(mock_mouse.move.call_count, 2)
            self.assertEqual(mock_mouse.down.call_count, 2)
            self.assertEqual(mock_mouse.up.call_count, 2)

    def test_extract_locations_click_timeout_failure(self):
        """Test click timeout failure after 3 attempts"""
        mock_client = AsyncMock()
        mock_page = MagicMock()
        mock_client.page = mock_page
        # Set all Playwright async methods as AsyncMock
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")
        # Mouse actions
        mock_mouse = MagicMock()
        mock_mouse.move = AsyncMock()
        mock_mouse.down = AsyncMock()
        mock_mouse.up = AsyncMock()
        mock_page.mouse = mock_mouse
        # Store button
        mock_store_button = MagicMock()
        mock_store_button.click = AsyncMock(side_effect=Exception("Click always fails"))
        mock_store_button.scroll_into_view_if_needed = AsyncMock()
        # Patch locator to return store button
        mock_locator = MagicMock()
        mock_locator.first = mock_store_button
        mock_page.locator.return_value = mock_locator
        # Patch parser
        with patch('api.mitra10.location_scraper.Mitra10LocationParser') as mock_parser:
            mock_parser.parse.return_value = []
            with self.assertRaises(TimeoutError) as context:
                asyncio.run(self.scraper._extract_locations(mock_client, self.url))
            self.assertIn("Failed to click store selector after 3 attempts", str(context.exception))
            self.assertEqual(mock_store_button.click.call_count, 3)

    def test_extract_locations_success(self):
        mock_client = MagicMock()
        mock_client._ensure_browser = AsyncMock()  # Mock the async method
        mock_page = MagicMock()  # Use MagicMock, not AsyncMock
        mock_client.page = mock_page

        # Mock all Playwright calls - async methods need AsyncMock return values
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")
        
        # Mock mouse
        mock_mouse = MagicMock()
        mock_mouse.move = AsyncMock()
        mock_mouse.down = AsyncMock()
        mock_mouse.up = AsyncMock()
        mock_page.mouse = mock_mouse
        
        # locator() is synchronous, returns a Locator object
        mock_locator = MagicMock()
        mock_first = MagicMock()
        mock_first.scroll_into_view_if_needed = AsyncMock()
        mock_first.click = AsyncMock()  # click is also async!
        mock_locator.first = mock_first
        mock_page.locator.return_value = mock_locator
        
        # Mock the parser
        with patch('api.mitra10.location_scraper.Mitra10LocationParser') as mock_parser:
            mock_parser.parse.return_value = ["MITRA10 A", "MITRA10 B"]
            result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
            self.assertEqual(result, ["MITRA10 A", "MITRA10 B"])

    def test_extract_locations_click_retry(self):
        mock_client = MagicMock()
        mock_client._ensure_browser = AsyncMock()  # Mock the async method
        mock_page = MagicMock()  # Use MagicMock, not AsyncMock
        mock_client.page = mock_page

        # Mock all Playwright calls - async methods need AsyncMock return values
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")
        
        # Mock mouse
        mock_mouse = MagicMock()
        mock_mouse.move = AsyncMock()
        mock_mouse.down = AsyncMock()
        mock_mouse.up = AsyncMock()
        mock_page.mouse = mock_mouse
        
        # locator() is synchronous, returns a Locator object with async methods
        mock_locator = MagicMock()
        mock_first = MagicMock()
        mock_first.scroll_into_view_if_needed = AsyncMock()
        # Simulate click failure then success
        mock_first.click = AsyncMock(side_effect=[Exception("Click failed"), None])
        mock_locator.first = mock_first
        mock_page.locator.return_value = mock_locator
        
        # Mock the parser
        with patch('api.mitra10.location_scraper.Mitra10LocationParser') as mock_parser:
            mock_parser.parse.return_value = ["MITRA10 RETRY"]
            result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
            self.assertEqual(result, ["MITRA10 RETRY"])

    def test_extract_locations_popup_close_with_dialog(self):
        """Test popup close mechanism when popup is present (lines 50-51)"""
        mock_client = AsyncMock()
        mock_page = MagicMock()
        mock_client.page = mock_page
        mock_client._ensure_browser = AsyncMock()
        
        # Set all Playwright async methods
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_function = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="""
        <div role=\"presentation\">
            <li><span>Test Location</span></li>
        </div>
        """)
        
        # Mock locator for popup - make it count > 0 to trigger lines 50-51
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)  # Popup present
        mock_page.locator.return_value = mock_locator
        
        # Mock mouse click
        mock_mouse = MagicMock()
        mock_mouse.click = AsyncMock()
        mock_mouse.move = AsyncMock()
        mock_mouse.down = AsyncMock()
        mock_mouse.up = AsyncMock()
        mock_page.mouse = mock_mouse
        
        # Mock store button
        mock_first = MagicMock()
        mock_first.scroll_into_view_if_needed = AsyncMock()
        mock_first.click = AsyncMock()
        mock_locator.first = mock_first
        
        with patch('api.mitra10.location_scraper.Mitra10LocationParser') as mock_parser:
            mock_parser.parse.return_value = ["Test Location"]
            result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
            self.assertEqual(result, ["Test Location"])
            # Verify popup close was attempted
            mock_mouse.click.assert_called_once_with(100, 100)

