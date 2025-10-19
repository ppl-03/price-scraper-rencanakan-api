from django.test import TestCase
from unittest.mock import AsyncMock, MagicMock, patch
from api.mitra10.location_scraper import Mitra10LocationScraper
import asyncio


class TestMitra10LocationScraper(TestCase):

    def setUp(self):
        self.scraper = Mitra10LocationScraper()
        self.url = "https://www.mitra10.com/"

    @patch("api.location_scraper.BatchPlaywrightClient")
    def test_scrape_locations_success(self, mock_batch):
        mock_instance = mock_batch.return_value.__enter__.return_value
        mock_instance.client = MagicMock()

        def fake_extract(client, url):
            return ["MITRA10 TEST 1", "MITRA10 TEST 2"]

        self.scraper._extract_locations = fake_extract

        result = self.scraper.scrape_locations()
        self.assertTrue(result["success"])
        self.assertEqual(len(result["locations"]), 2)
        self.assertEqual(result["error_message"], "")

    @patch("api.location_scraper.BatchPlaywrightClient")
    def test_scrape_locations_failure(self, mock_batch):
        mock_instance = mock_batch.return_value.__enter__.return_value
        mock_instance.client = MagicMock()

        def fake_extract(client, url):
            raise RuntimeError("Simulated failure")

        self.scraper._extract_locations = fake_extract

        result = self.scraper.scrape_locations()
        self.assertFalse(result["success"])
        self.assertIn("Simulated failure", result["error_message"])

    def test_extract_locations_success(self):
        mock_client = MagicMock()
        mock_page = AsyncMock()
        mock_client.page = mock_page

        # Mock all Playwright calls
        mock_page.goto.return_value = None
        mock_page.evaluate.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.locator.return_value = AsyncMock()
        mock_page.locator().first = AsyncMock()
        mock_page.locator().first.wait_for.return_value = None
        mock_page.wait_for_selector.return_value = None
        mock_page.wait_for_function.return_value = None
        mock_page.scroll_into_view_if_needed.return_value = None
        mock_page.click.return_value = None
        mock_page.eval_on_selector_all.return_value = ["MITRA10 A", "MITRA10 B"]

        result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
        self.assertEqual(result, ["MITRA10 A", "MITRA10 B"])

    def test_extract_locations_click_retry(self):
        mock_client = MagicMock()
        mock_page = AsyncMock()
        mock_client.page = mock_page

        # Simulate click failure then success
        mock_page.goto.return_value = None
        mock_page.evaluate.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.locator.return_value = AsyncMock()
        mock_page.locator().first = AsyncMock()
        mock_page.locator().first.wait_for.return_value = None
        mock_page.wait_for_selector.return_value = None
        mock_page.wait_for_function.return_value = None
        mock_page.scroll_into_view_if_needed.return_value = None

        mock_page.click.side_effect = [Exception("Click failed"), None]
        mock_page.mouse.move.return_value = None
        mock_page.mouse.down.return_value = None
        mock_page.mouse.up.return_value = None
        mock_page.eval_on_selector_all.return_value = ["MITRA10 RETRY"]

        result = asyncio.run(self.scraper._extract_locations(mock_client, self.url))
        self.assertEqual(result, ["MITRA10 RETRY"])
