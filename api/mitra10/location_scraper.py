import logging
from typing import List, Optional, NamedTuple
from api.playwright_client import BatchPlaywrightClient

logger = logging.getLogger(__name__)


class Mitra10ScrapingResult(NamedTuple):
    locations: List[str]
    success: bool
    error_message: Optional[str] = None
    attempts_made: int = 1


class Mitra10ScraperConfig:
    def __init__(self):
        self.base_url = "https://www.mitra10.com/"
        self.default_timeout = 60
        self.max_retries = 3
        self.retry_delay = 5
        
        # Working selectors based on HTML analysis
        self.location_button_trigger = 'div.jss9'  # Click this area to trigger location selector
        self.dropdown_button_selector = 'button.MuiButtonBase-root'  # General button selector
        self.dynamic_container_selector = 'div[role="presentation"]'  # Appears after interaction
        self.mui_popover_selector = '.MuiPopover-root'  # Material UI popover
        
        # Working interaction selectors (confirmed by testing)
        self.interaction_selectors = [
            'div.jss9',  # Primary location area (click to activate)
            'div[class*="jss"] button',  # Any button in JSS containers (13 found)
            'button.MuiButtonBase-root',  # MUI buttons (7 found)
            'button[tabindex="0"]'  # Focusable buttons (4 found)
        ]


class Mitra10ErrorHandler:
    @staticmethod
    def handle_no_locations(attempt: int) -> str:
        return f"No locations found in dropdown on attempt {attempt} - dropdown may not have loaded properly"
    
    @staticmethod
    def handle_interaction_timeout(attempt: int, timeout: int) -> str:
        return f"Timeout after {timeout}s on attempt {attempt} - website may be slow or button not clickable"
    
    @staticmethod
    def handle_generic_error(error: Exception, attempt: int) -> str:
        return f"Attempt {attempt} failed: {str(error)}"


class Mitra10DataValidator:
    @staticmethod
    def validate_html_content(html_content: str) -> bool:
        return html_content is not None and html_content.strip()
    
    @staticmethod
    def validate_locations(locations: List[str]) -> bool:
        return locations is not None and len(locations) > 0
    
    @staticmethod
    def has_interaction_capability(http_client) -> bool:
        return http_client and hasattr(http_client, 'get_with_interaction')


class Mitra10LocationScraper:
    def __init__(self, 
                 http_client=None, 
                 location_parser=None,
                 config: Mitra10ScraperConfig = None,
                 error_handler: Mitra10ErrorHandler = None,
                 validator: Mitra10DataValidator = None):
        self.http_client = http_client
        self.location_parser = location_parser
        self._config = config or Mitra10ScraperConfig()
        self._error_handler = error_handler or Mitra10ErrorHandler()
        self._validator = validator or Mitra10DataValidator()
    
    def scrape_locations(self) -> Mitra10ScrapingResult:
        logger.info("Starting location scraping for Mitra10")
        
        if not self._validator.has_interaction_capability(self.http_client):
            logger.warning("HTTP client does not support interaction, using batch mode")
            return self.scrape_locations_batch()
        
        try:
            html_content = self.http_client.get_with_interaction(
                self._config.base_url,
                self._config.dropdown_button_selector,
            )
            
            if not self._validator.validate_html_content(html_content):
                return Mitra10ScrapingResult(
                    locations=[],
                    success=False,
                    error_message="Received empty HTML content from website"
                )
            
            locations = self.location_parser.parse_locations(html_content)
            
            if not self._validator.validate_locations(locations):
                return Mitra10ScrapingResult(
                    locations=[],
                    success=False,
                    error_message="No valid locations found in dropdown - dropdown may not have opened"
                )
            
            logger.info(f"Successfully scraped {len(locations)} locations")
            return Mitra10ScrapingResult(locations=locations, success=True)
            
        except Exception as e:
            error_msg = self._error_handler.handle_generic_error(e, 1)
            logger.error(error_msg)
            return Mitra10ScrapingResult(locations=[], success=False, error_message=error_msg)
    
    def scrape_locations_batch(self, timeout: Optional[int] = None) -> Mitra10ScrapingResult:
        """Main entry point for batch location scraping with retry logic"""
        timeout = timeout or self._config.default_timeout
        logger.info("Starting batch location scraping for Mitra10")
        
        for attempt in range(self._config.max_retries):
            result = self._attempt_single_scrape(attempt + 1, timeout)
            
            if result.success:
                return result
                
            if self._should_retry(attempt):
                self._wait_for_retry()
            else:
                return self._create_failure_result(result.error_message, self._config.max_retries)
        
        return self._create_final_failure_result()
    
    def _attempt_single_scrape(self, attempt_number: int, timeout: int) -> Mitra10ScrapingResult:
        """Attempt a single scraping operation"""
        logger.info(f"Attempt {attempt_number} of {self._config.max_retries} - Timeout: {timeout}s")
        
        try:
            html_content = self._fetch_page_content(timeout)
            
            if not self._validator.validate_html_content(html_content):
                error_msg = "Received empty HTML content - website may not have loaded properly"
                logger.warning(f"Attempt {attempt_number}: {error_msg}")
                return Mitra10ScrapingResult(locations=[], success=False, error_message=error_msg)
            
            locations = self._parse_locations_from_html(html_content)
            
            if self._validator.validate_locations(locations):
                return self._create_success_result(locations, attempt_number)
            else:
                error_msg = self._error_handler.handle_no_locations(attempt_number)
                logger.warning(error_msg)
                return Mitra10ScrapingResult(locations=[], success=False, error_message=error_msg)
                
        except Exception as e:
            error_msg = self._error_handler.handle_generic_error(e, attempt_number)
            logger.error(error_msg)
            return Mitra10ScrapingResult(locations=[], success=False, error_message=error_msg)
    
    def _fetch_page_content(self, timeout: int) -> str:
        """Fetch HTML content from Mitra10 website with interaction"""
        with BatchPlaywrightClient() as batch_client:
            return batch_client.get_with_interaction(
                self._config.base_url,
                self._config.dropdown_button_selector,
                self._config.dynamic_container_selector,
                timeout
            )
    
    def _parse_locations_from_html(self, html_content: str) -> List[str]:
        """Parse locations from HTML content"""
        return self.location_parser.parse_locations(html_content)
    
    def _should_retry(self, attempt: int) -> bool:
        """Determine if another retry should be attempted"""
        return attempt < self._config.max_retries - 1
    
    def _wait_for_retry(self) -> None:
        """Wait for the configured retry delay"""
        logger.info(f"Retrying in {self._config.retry_delay} seconds...")
        import time
        time.sleep(self._config.retry_delay)
    
    def _create_success_result(self, locations: List[str], attempt_number: int) -> Mitra10ScrapingResult:
        """Create a successful scraping result"""
        logger.info(f"Successfully scraped {len(locations)} locations on attempt {attempt_number}")
        return Mitra10ScrapingResult(
            locations=locations, 
            success=True, 
            attempts_made=attempt_number
        )
    
    def _create_failure_result(self, error_message: str, attempts_made: int) -> Mitra10ScrapingResult:
        """Create a failure result for exhausted retries"""
        return Mitra10ScrapingResult(
            locations=[], 
            success=False, 
            error_message=f"All {attempts_made} attempts failed. Last error: {error_message}",
            attempts_made=attempts_made
        )
    
    def _create_final_failure_result(self) -> Mitra10ScrapingResult:
        """Create the final failure result when all attempts are exhausted"""
        return Mitra10ScrapingResult(
            locations=[], 
            success=False, 
            error_message=f"Failed to scrape locations after {self._config.max_retries} attempts",
            attempts_made=self._config.max_retries
        )
    
    def get_config(self) -> Mitra10ScraperConfig:
        return self._config
    
    def update_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.info(f"Updated config {key} to: {value}")
            else:
                logger.warning(f"Unknown config key: {key}")
    
    def get_scraping_status(self) -> dict:
        return {
            'base_url': self._config.base_url,
            'timeout': self._config.default_timeout,
            'max_retries': self._config.max_retries,
            'has_http_client': self.http_client is not None,
            'has_location_parser': self.location_parser is not None,
            'selectors': {
                'dropdown_button': self._config.dropdown_button_selector,
                'dynamic_container': self._config.dynamic_container_selector,
                'mui_popover': self._config.mui_popover_selector,
            }
        }