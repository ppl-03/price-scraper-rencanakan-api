from django.test import TestCase
from unittest.mock import AsyncMock, MagicMock, patch
from api.mitra10.location_scraper import Mitra10LocationScraper
import asyncio


class TestMitra10LocationScraper(TestCase):

    def setUp(self):
        self.scraper = Mitra10LocationScraper()
        self.url = "https://www.mitra10.com/"

    @patch("api.mitra10.location_scraper.BatchPlaywrightClient")
    def test_scrape_locations_success(self, mock_batch):
        mock_instance = mock_batch.return_value.__enter__.return_value
        mock_instance.client = MagicMock()

        async def fake_extract(client, url):
            return ["MITRA10 TEST 1", "MITRA10 TEST 2"]

        self.scraper._extract_locations = fake_extract

        result = self.scraper.scrape_locations()
        self.assertTrue(result["success"])
        self.assertEqual(len(result["locations"]), 2)
        self.assertEqual(result["error_message"], "")

    @patch("api.mitra10.location_scraper.BatchPlaywrightClient")
    def test_scrape_locations_failure(self, mock_batch):
        mock_instance = mock_batch.return_value.__enter__.return_value
        mock_instance.client = MagicMock()

        async def fake_extract(client, url):
            raise RuntimeError("Simulated failure")

        self.scraper._extract_locations = fake_extract

        result = self.scraper.scrape_locations()
        self.assertFalse(result["success"])
        self.assertIn("Simulated failure", result["error_message"])

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

