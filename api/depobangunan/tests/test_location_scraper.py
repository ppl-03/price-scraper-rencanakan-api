from unittest import TestCase
from unittest.mock import Mock, patch
from api.interfaces import Location, HttpClientError, HtmlParserError
from api.depobangunan.location_scraper import DepoBangunanLocationScraper


class TestDepoBangunanLocationScraper(TestCase):
    
    def setUp(self):
        self.mock_http_client = Mock()
        self.mock_location_parser = Mock()
        self.scraper = DepoBangunanLocationScraper(
            http_client=self.mock_http_client,
            location_parser=self.mock_location_parser
        )

    def test_scrape_locations_success(self):
        """Test successful location scraping"""
        mock_html = "<html>mock location html</html>"
        self.mock_http_client.get.return_value = mock_html
        
        expected_locations = [
            Location(
                store_name="Depo Bangunan - Kalimalang",
                address="Jl. Raya Kalimalang No.46, Duren Sawit, Kec. Duren Sawit, Timur, Daerah Khusus Ibukota Jakarta 13440"
            ),
            Location(
                store_name="Depo Bangunan - Tangerang Selatan", 
                address="Jl. Raya Serpong No.KM.2, Pakulonan, Kec. Serpong Utara, Kota Tangerang Selatan, Banten 15325"
            )
        ]
        self.mock_location_parser.parse_locations.return_value = expected_locations

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 2)
        self.assertEqual(result.locations[0].store_name, "Depo Bangunan - Kalimalang")
        self.assertEqual(result.locations[1].store_name, "Depo Bangunan - Tangerang Selatan")
        self.assertIsNone(result.error_message)

        expected_url = "https://www.depobangunan.co.id/gerai-depo-bangunan"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=30)
        self.mock_location_parser.parse_locations.assert_called_once_with(mock_html)

    def test_scrape_locations_http_client_error(self):
        """Test handling of HTTP client errors"""
        self.mock_http_client.get.side_effect = HttpClientError("Connection failed")

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("Connection failed", result.error_message)

    def test_scrape_locations_parser_error(self):
        """Test handling of parser errors"""
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.side_effect = HtmlParserError("Failed to parse HTML")

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("Failed to parse HTML", result.error_message)

    def test_scrape_locations_empty_result(self):
        """Test scraping with no locations found"""
        mock_html = "<html>no locations</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 0)
        self.assertIsNone(result.error_message)

    def test_scrape_locations_with_custom_timeout(self):
        """Test scraping with custom timeout"""
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations(timeout=60)

        expected_url = "https://www.depobangunan.co.id/gerai-depo-bangunan"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=60)
        self.assertTrue(result.success)

    def test_scrape_locations_url_construction(self):
        """Test correct URL is constructed"""
        mock_html = "<html>mock html</html>" 
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        self.scraper.scrape_locations()

        expected_url = "https://www.depobangunan.co.id/gerai-depo-bangunan"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=30)

    def test_scrape_locations_generic_exception(self):
        """Test handling of generic exceptions"""
        self.mock_http_client.get.side_effect = Exception("Unexpected error")

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("Unexpected error", result.error_message)

    def test_scrape_locations_with_zero_timeout(self):
        """Test scraping with zero timeout"""
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        self.scraper.scrape_locations(timeout=0)

        expected_url = "https://www.depobangunan.co.id/gerai-depo-bangunan"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=0)

    def test_scrape_locations_with_negative_timeout(self):
        """Test scraping with negative timeout (should default to 0)"""
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        self.scraper.scrape_locations(timeout=-5)

        expected_url = "https://www.depobangunan.co.id/gerai-depo-bangunan"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=0)

    def test_scrape_locations_parser_returns_none(self):
        """Test handling when parser returns None"""
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = None

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIsNotNone(result.error_message)

    def test_scrape_locations_empty_html_content(self):
        """Test scraping with empty HTML content"""
        self.mock_http_client.get.return_value = ""
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 0)

    def test_scrape_locations_whitespace_only_html(self):
        """Test scraping with whitespace-only HTML"""
        self.mock_http_client.get.return_value = "   \n\t  "
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 0)

    def test_scrape_locations_large_html_content(self):
        """Test scraping with large HTML content"""
        large_html = "<html>" + "x" * 1000000 + "</html>"
        self.mock_http_client.get.return_value = large_html
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.mock_location_parser.parse_locations.assert_called_once_with(large_html)

    def test_scrape_locations_url_in_result(self):
        """Test that result contains the correct URL"""
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertEqual(result.url, "https://www.depobangunan.co.id/gerai-depo-bangunan")

    def test_scrape_locations_duplicate_locations(self):
        """Test scraping with duplicate locations"""
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        
        duplicate_locations = [
            Location("Depo Bangunan - Store A", "Address A"),
            Location("Depo Bangunan - Store A", "Address A"),
            Location("Depo Bangunan - Store B", "Address B")
        ]
        self.mock_location_parser.parse_locations.return_value = duplicate_locations

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 3)

    def test_scrape_locations_http_client_returns_none(self):
        """Test handling when HTTP client returns None"""
        self.mock_http_client.get.return_value = None

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIsNotNone(result.error_message)

    def test_scrape_locations_none_timeout(self):
        """Test scraping with None timeout (should use default)"""
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        self.scraper.scrape_locations(timeout=None)

        expected_url = "https://www.depobangunan.co.id/gerai-depo-bangunan"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=30)
