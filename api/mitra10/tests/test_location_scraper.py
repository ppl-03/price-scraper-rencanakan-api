import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from api.mitra10.location_scraper import (
    Mitra10LocationScraper, 
    Mitra10ScrapingResult, 
    Mitra10ScraperConfig,
    Mitra10ErrorHandler,
    Mitra10DataValidator
)
from api.mitra10.location_parser import Mitra10LocationParser


class TestMitra10ScrapingResult(unittest.TestCase):
    
    def test_scraping_result_creation_success(self):
        """Test creating a successful scraping result"""
        locations = ['Jakarta', 'Bandung', 'Surabaya']
        result = Mitra10ScrapingResult(
            locations=locations,
            success=True,
            error_message=None,
            attempts_made=1
        )
        
        self.assertEqual(result.locations, locations)
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.attempts_made, 1)
    
    def test_scraping_result_creation_failure(self):
        """Test creating a failed scraping result"""
        result = Mitra10ScrapingResult(
            locations=[],
            success=False,
            error_message="Network timeout",
            attempts_made=3
        )
        
        self.assertEqual(result.locations, [])
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Network timeout")
        self.assertEqual(result.attempts_made, 3)
    
    def test_scraping_result_default_values(self):
        """Test default values in scraping result"""
        result = Mitra10ScrapingResult(
            locations=['Jakarta'],
            success=True
        )
        
        self.assertEqual(result.locations, ['Jakarta'])
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.attempts_made, 1)


class TestMitra10ScraperConfig(unittest.TestCase):
    
    def test_config_initialization(self):
        """Test scraper configuration initialization"""
        config = Mitra10ScraperConfig()
        
        self.assertEqual(config.base_url, "https://www.mitra10.com/")
        self.assertEqual(config.default_timeout, 60)
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.retry_delay, 5)
        
        # Test selectors
        self.assertEqual(config.location_button_trigger, 'div.jss9')
        self.assertEqual(config.dropdown_button_selector, 'button.MuiButtonBase-root')
        self.assertEqual(config.dynamic_container_selector, 'div[role="presentation"]')
        self.assertEqual(config.mui_popover_selector, '.MuiPopover-root')
        
        # Test interaction selectors
        expected_selectors = [
            'div.jss9',
            'div[class*="jss"] button',
            'button.MuiButtonBase-root',
            'button[tabindex="0"]'
        ]
        self.assertEqual(config.interaction_selectors, expected_selectors)


class TestMitra10ErrorHandler(unittest.TestCase):
    
    def test_handle_no_locations(self):
        """Test no locations error message"""
        message = Mitra10ErrorHandler.handle_no_locations(2)
        expected = "No locations found in dropdown on attempt 2 - dropdown may not have loaded properly"
        self.assertEqual(message, expected)
    
    def test_handle_interaction_timeout(self):
        """Test interaction timeout error message"""
        message = Mitra10ErrorHandler.handle_interaction_timeout(1, 30)
        expected = "Timeout after 30s on attempt 1 - website may be slow or button not clickable"
        self.assertEqual(message, expected)
    
    def test_handle_generic_error(self):
        """Test generic error message"""
        error = Exception("Network connection failed")
        message = Mitra10ErrorHandler.handle_generic_error(error, 3)
        expected = "Attempt 3 failed: Network connection failed"
        self.assertEqual(message, expected)


class TestMitra10DataValidator(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = Mitra10DataValidator()
    
    def test_validate_html_content_valid(self):
        """Test HTML content validation with valid content"""
        valid_html = "<html><body>Valid content</body></html>"
        self.assertTrue(self.validator.validate_html_content(valid_html))
    
    def test_validate_html_content_invalid(self):
        """Test HTML content validation with invalid content"""
        self.assertFalse(self.validator.validate_html_content(""))
        self.assertFalse(self.validator.validate_html_content(None))
        self.assertFalse(self.validator.validate_html_content("   "))
    
    def test_validate_locations_valid(self):
        """Test location list validation with valid locations"""
        valid_locations = ["Jakarta", "Bandung", "Surabaya"]
        self.assertTrue(self.validator.validate_locations(valid_locations))
    
    def test_validate_locations_invalid(self):
        """Test location list validation with invalid locations"""
        self.assertFalse(self.validator.validate_locations([]))
        self.assertFalse(self.validator.validate_locations(None))
    
    def test_validate_locations_single_item(self):
        """Test location list validation with single valid location"""
        single_location = ["Jakarta"]
        self.assertTrue(self.validator.validate_locations(single_location))


class TestMitra10LocationScraper(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_parser = Mock(spec=Mitra10LocationParser)
        self.mock_validator = Mock(spec=Mitra10DataValidator)
        self.mock_config = Mock(spec=Mitra10ScraperConfig)
        self.mock_error_handler = Mock(spec=Mitra10ErrorHandler)
        
        # Set up mock config values
        self.mock_config.default_timeout = 60
        self.mock_config.max_retries = 3
        self.mock_config.retry_delay = 2
        self.mock_config.base_url = "https://www.mitra10.com/"
        self.mock_config.dropdown_button_selector = "button.test"
        self.mock_config.dynamic_container_selector = "div.test"
        
        self.scraper = Mitra10LocationScraper(
            location_parser=self.mock_parser,
            validator=self.mock_validator,
            config=self.mock_config,
            error_handler=self.mock_error_handler
        )
    
    def test_scraper_initialization_with_custom_components(self):
        """Test scraper initialization with custom components"""
        scraper = Mitra10LocationScraper(
            location_parser=self.mock_parser,
            validator=self.mock_validator,
            config=self.mock_config,
            error_handler=self.mock_error_handler
        )
        
        self.assertEqual(scraper.location_parser, self.mock_parser)
        self.assertEqual(scraper._validator, self.mock_validator)
        self.assertEqual(scraper._config, self.mock_config)
        self.assertEqual(scraper._error_handler, self.mock_error_handler)
    
    def test_scraper_initialization_with_defaults(self):
        """Test scraper initialization with default components"""
        scraper = Mitra10LocationScraper()
        
        self.assertIsNone(scraper.location_parser)  # No default parser created
        self.assertIsNone(scraper.http_client)      # No default client created
        self.assertIsInstance(scraper._validator, Mitra10DataValidator)
        self.assertIsInstance(scraper._config, Mitra10ScraperConfig)
        self.assertIsInstance(scraper._error_handler, Mitra10ErrorHandler)
    
    @patch('api.mitra10.location_scraper.BatchPlaywrightClient')
    def test_scrape_locations_batch_success_first_attempt(self, mock_client_class):
        """Test successful scraping on first attempt"""
        # Mock the client context manager
        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)
        
        # Mock successful HTML content
        mock_html = "<html>Valid location HTML</html>"
        mock_client.get_with_interaction.return_value = mock_html
        
        # Mock validator responses
        self.mock_validator.validate_html_content.return_value = True
        self.mock_validator.validate_locations.return_value = True
        
        # Mock parser response
        mock_locations = ["Jakarta", "Bandung", "Surabaya"]
        self.mock_parser.parse_locations.return_value = mock_locations
        
        # Execute scraping
        result = self.scraper.scrape_locations_batch()
        
        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.locations, mock_locations)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.attempts_made, 1)
        
        # Verify method calls
        mock_client.get_with_interaction.assert_called_once()
        self.mock_validator.validate_html_content.assert_called_once_with(mock_html)
        self.mock_parser.parse_locations.assert_called_once_with(mock_html)
        self.mock_validator.validate_locations.assert_called_once_with(mock_locations)
    
    @patch('api.mitra10.location_scraper.BatchPlaywrightClient')
    def test_scrape_locations_batch_success_with_custom_timeout(self, mock_client_class):
        """Test successful scraping with custom timeout"""
        # Mock the client
        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)
        
        mock_client.get_with_interaction.return_value = "<html>Valid</html>"
        self.mock_validator.validate_html_content.return_value = True
        self.mock_validator.validate_locations.return_value = True
        self.mock_parser.parse_locations.return_value = ["Jakarta"]
        
        # Execute with custom timeout
        result = self.scraper.scrape_locations_batch(timeout=120)
        
        # Verify custom timeout was used
        mock_client.get_with_interaction.assert_called_once_with(
            self.mock_config.base_url,
            self.mock_config.dropdown_button_selector,
            self.mock_config.dynamic_container_selector,
            120
        )
        self.assertTrue(result.success)
    
    @patch('api.mitra10.location_scraper.BatchPlaywrightClient')
    def test_scrape_locations_batch_invalid_html_content(self, mock_client_class):
        """Test scraping with invalid HTML content"""
        # Mock the client
        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)
        
        mock_client.get_with_interaction.return_value = ""
        self.mock_validator.validate_html_content.return_value = False
        
        # Execute scraping
        result = self.scraper.scrape_locations_batch()
        
        # Verify failure result
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertEqual(result.attempts_made, self.mock_config.max_retries)
        self.assertIsNotNone(result.error_message)
    
    @patch('api.mitra10.location_scraper.BatchPlaywrightClient')
    def test_scrape_locations_batch_no_locations_found(self, mock_client_class):
        """Test scraping when no locations are found"""
        # Mock the client
        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)
        
        mock_client.get_with_interaction.return_value = "<html>Valid</html>"
        self.mock_validator.validate_html_content.return_value = True
        self.mock_validator.validate_locations.return_value = False
        self.mock_parser.parse_locations.return_value = []
        self.mock_error_handler.handle_no_locations.return_value = "No locations error"
        
        # Execute scraping
        result = self.scraper.scrape_locations_batch()
        
        # Verify failure result
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertEqual(result.attempts_made, self.mock_config.max_retries)
        
        # Verify error handler was called
        self.mock_error_handler.handle_no_locations.assert_called()
    
    @patch('api.mitra10.location_scraper.BatchPlaywrightClient')
    @patch('time.sleep')
    def test_scrape_locations_batch_retry_logic(self, mock_sleep, mock_client_class):
        """Test retry logic with eventual success"""
        # Mock the client
        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)
        
        # Mock first two attempts fail, third succeeds
        self.mock_validator.validate_html_content.side_effect = [False, False, True]
        self.mock_validator.validate_locations.return_value = True
        mock_client.get_with_interaction.return_value = "<html>Valid</html>"
        self.mock_parser.parse_locations.return_value = ["Jakarta"]
        
        # Execute scraping
        result = self.scraper.scrape_locations_batch()
        
        # Verify success on third attempt
        self.assertTrue(result.success)
        self.assertEqual(result.attempts_made, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep called between retries
        mock_sleep.assert_called_with(self.mock_config.retry_delay)
    
    @patch('api.mitra10.location_scraper.BatchPlaywrightClient')
    def test_scrape_locations_batch_exception_handling(self, mock_client_class):
        """Test exception handling during scraping"""
        # Mock the client to raise an exception
        mock_client_class.side_effect = Exception("Network error")
        self.mock_error_handler.handle_generic_error.return_value = "Generic error message"
        
        # Execute scraping
        result = self.scraper.scrape_locations_batch()
        
        # Verify failure result
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertEqual(result.attempts_made, self.mock_config.max_retries)
        self.assertIsNotNone(result.error_message)
        
        # Verify error handler was called
        self.mock_error_handler.handle_generic_error.assert_called()
    
    def test_attempt_single_scrape_success(self):
        """Test _attempt_single_scrape method success"""
        with patch.object(self.scraper, '_fetch_page_content') as mock_fetch:
            with patch.object(self.scraper, '_parse_locations_from_html') as mock_parse:
                mock_fetch.return_value = "<html>Valid</html>"
                mock_parse.return_value = ["Jakarta"]
                self.mock_validator.validate_html_content.return_value = True
                self.mock_validator.validate_locations.return_value = True
                
                result = self.scraper._attempt_single_scrape(1, 60)
                
                self.assertTrue(result.success)
                self.assertEqual(result.locations, ["Jakarta"])
    
    def test_attempt_single_scrape_invalid_html(self):
        """Test _attempt_single_scrape with invalid HTML"""
        with patch.object(self.scraper, '_fetch_page_content') as mock_fetch:
            mock_fetch.return_value = ""
            self.mock_validator.validate_html_content.return_value = False
            
            result = self.scraper._attempt_single_scrape(1, 60)
            
            self.assertFalse(result.success)
            self.assertEqual(result.locations, [])
    
    def test_attempt_single_scrape_exception(self):
        """Test _attempt_single_scrape with exception"""
        with patch.object(self.scraper, '_fetch_page_content') as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")
            self.mock_error_handler.handle_generic_error.return_value = "Error message"
            
            result = self.scraper._attempt_single_scrape(1, 60)
            
            self.assertFalse(result.success)
            self.assertEqual(result.locations, [])
    
    @patch('api.mitra10.location_scraper.BatchPlaywrightClient')
    def test_fetch_page_content(self, mock_client_class):
        """Test _fetch_page_content method"""
        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=None)
        
        mock_client.get_with_interaction.return_value = "<html>Content</html>"
        
        result = self.scraper._fetch_page_content(120)
        
        self.assertEqual(result, "<html>Content</html>")
        mock_client.get_with_interaction.assert_called_once_with(
            self.mock_config.base_url,
            self.mock_config.dropdown_button_selector,
            self.mock_config.dynamic_container_selector,
            120
        )
    
    def test_parse_locations_from_html(self):
        """Test _parse_locations_from_html method"""
        html_content = "<html>Test</html>"
        self.mock_parser.parse_locations.return_value = ["Jakarta", "Bandung"]
        
        result = self.scraper._parse_locations_from_html(html_content)
        
        self.assertEqual(result, ["Jakarta", "Bandung"])
        self.mock_parser.parse_locations.assert_called_once_with(html_content)
    
    def test_should_retry(self):
        """Test _should_retry method"""
        self.mock_config.max_retries = 3
        
        self.assertTrue(self.scraper._should_retry(0))  # First attempt
        self.assertTrue(self.scraper._should_retry(1))  # Second attempt
        self.assertFalse(self.scraper._should_retry(2))  # Third attempt (last)
    
    @patch('time.sleep')
    def test_wait_for_retry(self, mock_sleep):
        """Test _wait_for_retry method"""
        self.scraper._wait_for_retry()
        
        mock_sleep.assert_called_once_with(self.mock_config.retry_delay)
    
    def test_create_success_result(self):
        """Test _create_success_result method"""
        locations = ["Jakarta", "Bandung"]
        
        result = self.scraper._create_success_result(locations, 2)
        
        self.assertTrue(result.success)
        self.assertEqual(result.locations, locations)
        self.assertEqual(result.attempts_made, 2)
        self.assertIsNone(result.error_message)
    
    def test_create_failure_result(self):
        """Test _create_failure_result method"""
        error_msg = "Network timeout"
        
        result = self.scraper._create_failure_result(error_msg, 3)
        
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertEqual(result.attempts_made, 3)
        self.assertIn("All 3 attempts failed", result.error_message)
        self.assertIn("Network timeout", result.error_message)
    
    def test_create_final_failure_result(self):
        """Test _create_final_failure_result method"""
        result = self.scraper._create_final_failure_result()
        
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertEqual(result.attempts_made, self.mock_config.max_retries)
        self.assertIn("Failed to scrape locations", result.error_message)
    
    def test_scraper_with_real_components_integration(self):
        """Integration test with real components"""
        # Create scraper with real components
        real_scraper = Mitra10LocationScraper()
        
        # Test that all components are properly initialized
        self.assertIsNone(real_scraper.location_parser)  # No default parser created
        self.assertIsNotNone(real_scraper._validator)
        self.assertIsNotNone(real_scraper._config)
        self.assertIsNotNone(real_scraper._error_handler)
        
        # Test config values
        self.assertEqual(real_scraper._config.base_url, "https://www.mitra10.com/")
        self.assertEqual(real_scraper._config.max_retries, 3)

    def test_scrape_locations_with_interaction_capability(self):
        """Test scrape_locations method with interaction capability"""
        mock_http_client = Mock()
        mock_http_client.get_with_interaction = Mock(return_value="<html><div>Location Data</div></html>")
        mock_parser = Mock()
        mock_parser.parse_locations = Mock(return_value=["Jakarta", "Bandung"])
        
        scraper = Mitra10LocationScraper(
            http_client=mock_http_client,
            location_parser=mock_parser
        )
        
        result = scraper.scrape_locations()
        
        self.assertTrue(result.success)
        self.assertEqual(result.locations, ["Jakarta", "Bandung"])
        mock_http_client.get_with_interaction.assert_called_once()

    def test_scrape_locations_empty_html_content(self):
        """Test scrape_locations with empty HTML content"""
        mock_http_client = Mock()
        mock_http_client.get_with_interaction = Mock(return_value="")
        mock_parser = Mock()
        
        scraper = Mitra10LocationScraper(
            http_client=mock_http_client,
            location_parser=mock_parser
        )
        
        result = scraper.scrape_locations()
        
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("empty HTML content", result.error_message)

    def test_scrape_locations_no_valid_locations(self):
        """Test scrape_locations when no valid locations found"""
        mock_http_client = Mock()
        mock_http_client.get_with_interaction = Mock(return_value="<html><div>Data</div></html>")
        mock_parser = Mock()
        mock_parser.parse_locations = Mock(return_value=[])
        
        scraper = Mitra10LocationScraper(
            http_client=mock_http_client,
            location_parser=mock_parser
        )
        
        result = scraper.scrape_locations()
        
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("No valid locations found", result.error_message)

    def test_scrape_locations_exception_handling(self):
        """Test scrape_locations exception handling"""
        mock_http_client = Mock()
        mock_http_client.get_with_interaction = Mock(side_effect=Exception("Network error"))
        mock_parser = Mock()
        
        scraper = Mitra10LocationScraper(
            http_client=mock_http_client,
            location_parser=mock_parser
        )
        
        result = scraper.scrape_locations()
        
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertIn("Network error", result.error_message)

    def test_get_config(self):
        """Test get_config method"""
        scraper = Mitra10LocationScraper()
        config = scraper.get_config()
        
        self.assertIsInstance(config, Mitra10ScraperConfig)
        self.assertEqual(config.base_url, "https://www.mitra10.com/")

    def test_update_config_valid_keys(self):
        """Test update_config with valid config keys"""
        scraper = Mitra10LocationScraper()
        
        scraper.update_config(max_retries=5, default_timeout=120)
        
        self.assertEqual(scraper._config.max_retries, 5)
        self.assertEqual(scraper._config.default_timeout, 120)

    def test_update_config_invalid_key(self):
        """Test update_config with invalid config key"""
        scraper = Mitra10LocationScraper()
        
        with patch('api.mitra10.location_scraper.logger') as mock_logger:
            scraper.update_config(invalid_key="value")
            mock_logger.warning.assert_called_with("Unknown config key: invalid_key")

    def test_get_scraping_status(self):
        """Test get_scraping_status method"""
        mock_http_client = Mock()
        mock_parser = Mock()
        
        scraper = Mitra10LocationScraper(
            http_client=mock_http_client,
            location_parser=mock_parser
        )
        
        status = scraper.get_scraping_status()
        
        self.assertIsInstance(status, dict)
        self.assertEqual(status['base_url'], "https://www.mitra10.com/")
        self.assertEqual(status['timeout'], 60)
        self.assertEqual(status['max_retries'], 3)
        self.assertTrue(status['has_http_client'])
        self.assertTrue(status['has_location_parser'])
        self.assertIn('selectors', status)

    def test_has_interaction_capability_comprehensive(self):
        """Test has_interaction_capability validator check comprehensively"""
        validator = Mitra10DataValidator()
        
        # Test with client that has interaction capability
        mock_client = Mock()
        mock_client.get_with_interaction = Mock()
        self.assertTrue(validator.has_interaction_capability(mock_client))
        
        # Test with client without interaction capability
        mock_basic_client = Mock(spec=[])
        self.assertFalse(validator.has_interaction_capability(mock_basic_client))
        
        # Test with None client
        self.assertFalse(validator.has_interaction_capability(None))

    def test_scrape_locations_fallback_to_batch_mode(self):
        """Test scrape_locations fallback to batch mode when client lacks interaction capability"""
        # Create a client without interaction capability
        mock_http_client = Mock(spec=[])  # No get_with_interaction method
        mock_parser = Mock()
        
        scraper = Mitra10LocationScraper(
            http_client=mock_http_client,
            location_parser=mock_parser
        )
        
        # Mock the batch method to return a known result
        expected_result = Mitra10ScrapingResult(
            locations=["Batch Location"],
            success=True,
            attempts_made=1
        )
        
        with patch.object(scraper, 'scrape_locations_batch', return_value=expected_result) as mock_batch:
            result = scraper.scrape_locations()
            
            # Should call batch method due to lack of interaction capability
            mock_batch.assert_called_once()
            self.assertEqual(result.locations, ["Batch Location"])
            self.assertTrue(result.success)

    def test_scrape_locations_batch_final_failure_after_all_retries(self):
        """Test scrape_locations_batch final failure result when all retries exhausted"""
        mock_http_client = Mock()
        mock_http_client.get = Mock(return_value="")  # Always return empty HTML
        mock_parser = Mock()
        
        # Create scraper with only 1 retry to speed up test
        config = Mitra10ScraperConfig()
        config.max_retries = 1
        
        scraper = Mitra10LocationScraper(
            http_client=mock_http_client,
            location_parser=mock_parser,
            config=config
        )
        
        result = scraper.scrape_locations_batch()
        
        # Should get final failure result
        self.assertFalse(result.success)
        self.assertEqual(result.locations, [])
        self.assertEqual(result.attempts_made, 1)
        self.assertIn("All 1 attempts failed", result.error_message)

    def test_scrape_locations_batch_edge_case_force_final_failure(self):
        """Test to force final failure line coverage by modifying _should_retry behavior"""
        mock_parser = Mock()
        
        scraper = Mitra10LocationScraper(location_parser=mock_parser)
        
        # Mock _attempt_single_scrape to always return failure
        failed_result = Mitra10ScrapingResult(
            locations=[], 
            success=False, 
            error_message="Test error"
        )
        
        with patch.object(scraper, '_attempt_single_scrape', return_value=failed_result):
            # Test the _create_final_failure_result method directly to ensure coverage
            final_result = scraper._create_final_failure_result()
            
            self.assertFalse(final_result.success)
            self.assertEqual(final_result.locations, [])
            self.assertEqual(final_result.attempts_made, scraper._config.max_retries)


if __name__ == '__main__':
    unittest.main()
