from unittest import TestCase
from unittest.mock import Mock, patch
from api.interfaces import Location, HttpClientError, HtmlParserError
from api.gemilang.location_scraper import GemilangLocationScraper


class TestGemilangLocationScraper(TestCase):
    
    def setUp(self):
        self.mock_http_client = Mock()
        self.mock_location_parser = Mock()
        self.scraper = GemilangLocationScraper(
            http_client=self.mock_http_client,
            location_parser=self.mock_location_parser
        )

    def test_scrape_locations_success(self):
        mock_html = "<html>mock location html</html>"
        self.mock_http_client.get.return_value = mock_html
        
        expected_locations = [
            Location(
                store_name="GEMILANG - BANJARMASIN KM",
                address="Jl. Kampung Melayu Darat 39A Rt.8\nBanjarmasin, Kalimantan Selatan\nIndonesia"
            ),
            Location(
                store_name="GEMILANG - JAKARTA PUSAT", 
                address="Jl. Veteran No. 123\nJakarta Pusat, DKI Jakarta\nIndonesia"
            )
        ]
        self.mock_location_parser.parse_locations.return_value = expected_locations

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 2)
        self.assertEqual(result.locations[0].store_name, "GEMILANG - BANJARMASIN KM")
        self.assertEqual(result.locations[1].store_name, "GEMILANG - JAKARTA PUSAT")
        self.assertIsNone(result.error_message)

        expected_url = "https://gemilang-store.com/pusat/store-locations"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=30)
        self.mock_location_parser.parse_locations.assert_called_once_with(mock_html)

    def test_scrape_locations_http_client_error(self):
        self.mock_http_client.get.side_effect = HttpClientError("Connection failed")

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("Connection failed", result.error_message)

    def test_scrape_locations_parser_error(self):
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.side_effect = HtmlParserError("Failed to parse HTML")

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("Failed to parse HTML", result.error_message)

    def test_scrape_locations_empty_result(self):
        mock_html = "<html>no locations</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 0)
        self.assertIsNone(result.error_message)

    def test_scrape_locations_with_custom_timeout(self):
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations(timeout=60)

        expected_url = "https://gemilang-store.com/pusat/store-locations"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=60)
        self.assertTrue(result.success)

    def test_scrape_locations_url_construction(self):
        mock_html = "<html>mock html</html>" 
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        self.scraper.scrape_locations()

        expected_url = "https://gemilang-store.com/pusat/store-locations"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=30)

    def test_scrape_locations_generic_exception(self):
        self.mock_http_client.get.side_effect = Exception("Unexpected error")

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("Unexpected error", result.error_message)

    def test_scrape_locations_with_zero_timeout(self):
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        self.scraper.scrape_locations(timeout=0)

        expected_url = "https://gemilang-store.com/pusat/store-locations"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=0)

    def test_scrape_locations_with_negative_timeout(self):
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        self.scraper.scrape_locations(timeout=-1)

        expected_url = "https://gemilang-store.com/pusat/store-locations"
        self.mock_http_client.get.assert_called_once_with(expected_url, timeout=0)

    def test_scrape_locations_parser_returns_none(self):
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = None

        result = self.scraper.scrape_locations()

        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIsNotNone(result.error_message)

    def test_scrape_locations_empty_html_content(self):
        self.mock_http_client.get.return_value = ""
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 0)

    def test_scrape_locations_whitespace_only_html(self):
        self.mock_http_client.get.return_value = "   \n\t  "
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 0)

    def test_scrape_locations_large_html_content(self):
        large_html = "<html>" + "x" * 1000000 + "</html>"
        self.mock_http_client.get.return_value = large_html
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.mock_location_parser.parse_locations.assert_called_once_with(large_html)

    def test_scrape_locations_malformed_url_in_result(self):
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        self.mock_location_parser.parse_locations.return_value = []

        result = self.scraper.scrape_locations()

        self.assertEqual(result.url, "https://gemilang-store.com/pusat/store-locations")

    def test_scrape_locations_duplicate_locations(self):
        mock_html = "<html>mock html</html>"
        self.mock_http_client.get.return_value = mock_html
        
        duplicate_locations = [
            Location("GEMILANG - STORE A", "Address A"),
            Location("GEMILANG - STORE A", "Address A"),
            Location("GEMILANG - STORE B", "Address B")
        ]
        self.mock_location_parser.parse_locations.return_value = duplicate_locations

        result = self.scraper.scrape_locations()

        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 3)

    def test_location_scraper_configuration_get_base_url(self):
        from api.gemilang.location_scraper import LocationScraperConfiguration
        config = LocationScraperConfiguration("https://test.com")
        self.assertEqual(config.get_base_url(), "https://test.com")

    def test_location_scraper_configuration_get_default_timeout(self):
        from api.gemilang.location_scraper import LocationScraperConfiguration
        config = LocationScraperConfiguration("https://test.com", 45)
        self.assertEqual(config.get_default_timeout(), 45)

    def test_scraping_result_builder_with_error_then_success(self):
        from api.gemilang.location_scraper import ScrapingResultBuilder
        from api.interfaces import Location
        
        builder = ScrapingResultBuilder("https://test.com")
        builder.with_error("Initial error")
        builder.with_success([Location("Store", "Address")])
        
        result = builder.build()
        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 1)
        self.assertIsNone(result.error_message)

    def test_error_handler_handle_http_error(self):
        from api.gemilang.location_scraper import ErrorHandler
        from api.interfaces import HttpClientError
        
        error = HttpClientError("HTTP Error")
        result = ErrorHandler.handle_http_error(error, "https://test.com")
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "HTTP Error")
        self.assertEqual(len(result.locations), 0)

    def test_error_handler_handle_parser_error(self):
        from api.gemilang.location_scraper import ErrorHandler
        from api.interfaces import HtmlParserError
        
        error = HtmlParserError("Parser Error")
        result = ErrorHandler.handle_parser_error(error, "https://test.com")
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Parser Error")
        self.assertEqual(len(result.locations), 0)

    def test_error_handler_handle_generic_error(self):
        from api.gemilang.location_scraper import ErrorHandler
        
        error = ValueError("Generic Error")
        result = ErrorHandler.handle_generic_error(error, "https://test.com")
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Generic Error")
        self.assertEqual(len(result.locations), 0)

    def test_location_data_validator_validate_html_content_none(self):
        from api.gemilang.location_scraper import LocationDataValidator
        
        result = LocationDataValidator.validate_html_content(None)
        self.assertFalse(result)

    def test_location_data_validator_validate_html_content_valid(self):
        from api.gemilang.location_scraper import LocationDataValidator
        
        result = LocationDataValidator.validate_html_content("<html></html>")
        self.assertTrue(result)

    def test_location_data_validator_validate_locations_none(self):
        from api.gemilang.location_scraper import LocationDataValidator
        
        result = LocationDataValidator.validate_locations(None)
        self.assertFalse(result)

    def test_location_data_validator_validate_locations_valid(self):
        from api.gemilang.location_scraper import LocationDataValidator
        from api.interfaces import Location
        
        locations = [Location("Store", "Address")]
        result = LocationDataValidator.validate_locations(locations)
        self.assertTrue(result)

    def test_location_data_validator_validate_timeout_none(self):
        from api.gemilang.location_scraper import LocationDataValidator
        
        result = LocationDataValidator.validate_timeout(None)
        self.assertEqual(result, 30)

    def test_location_data_validator_validate_timeout_negative(self):
        from api.gemilang.location_scraper import LocationDataValidator
        
        result = LocationDataValidator.validate_timeout(-5)
        self.assertEqual(result, 0)

    def test_gemilang_location_scraper_with_all_none_dependencies(self):
        from api.gemilang.location_scraper import GemilangLocationScraper
        from unittest.mock import Mock
        
        mock_http_client = Mock()
        mock_parser = Mock()
        
        scraper = GemilangLocationScraper(mock_http_client, mock_parser, None, None, None)
        
        self.assertIsNotNone(scraper._config)
        self.assertIsNotNone(scraper._error_handler)
        self.assertIsNotNone(scraper._validator)

    def test_create_success_result_method(self):
        from api.gemilang.location_scraper import GemilangLocationScraper
        from api.interfaces import Location
        from unittest.mock import Mock
        
        mock_http_client = Mock()
        mock_parser = Mock()
        scraper = GemilangLocationScraper(mock_http_client, mock_parser)
        
        locations = [Location("Store", "Address")]
        result = scraper._create_success_result(locations, "https://test.com")
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 1)
        self.assertIsNone(result.error_message)

    def test_scraper_result_builder_chaining(self):
        from api.gemilang.location_scraper import ScrapingResultBuilder
        from api.interfaces import Location
        
        builder = ScrapingResultBuilder("https://test.com")
        result = builder.with_success([Location("Store", "Address")]).build()
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.locations), 1)

    def test_fetch_html_content_none_response(self):
        from api.gemilang.location_scraper import GemilangLocationScraper
        from api.interfaces import HttpClientError
        from unittest.mock import Mock
        
        mock_http_client = Mock()
        mock_http_client.get.return_value = None
        mock_parser = Mock()
        
        scraper = GemilangLocationScraper(mock_http_client, mock_parser)
        
        with self.assertRaises(HttpClientError):
            scraper._fetch_html_content("https://test.com", 30)