import logging
from typing import List, Optional
from abc import ABC, abstractmethod

from api.interfaces import (
    IHttpClient, ILocationParser, ILocationScraper,
    LocationScrapingResult, Location, HttpClientError, HtmlParserError
)

logger = logging.getLogger(__name__)


class LocationScraperConfiguration:
    """Configuration class for location scraper"""
    
    def __init__(self, base_url: str, default_timeout: int = 30):
        self.base_url = base_url
        self.default_timeout = default_timeout
    
    def get_base_url(self) -> str:
        return self.base_url
    
    def get_default_timeout(self) -> int:
        return self.default_timeout


class ScrapingResultBuilder:
    """Builder class for creating LocationScrapingResult objects"""
    
    def __init__(self, url: str):
        self._url = url
        self._locations = []
        self._success = False
        self._error_message = None
    
    def with_success(self, locations: List[Location]) -> 'ScrapingResultBuilder':
        self._locations = locations or []
        self._success = True
        self._error_message = None
        return self
    
    def with_error(self, error_message: str) -> 'ScrapingResultBuilder':
        self._locations = []
        self._success = False
        self._error_message = error_message
        return self
    
    def build(self) -> LocationScrapingResult:
        return LocationScrapingResult(
            locations=self._locations,
            success=self._success,
            error_message=self._error_message,
            url=self._url
        )


class ErrorHandler:
    """Handler for different types of errors during scraping"""
    
    @staticmethod
    def handle_http_error(error: HttpClientError, url: str) -> LocationScrapingResult:
        logger.error(f"HTTP client error during location scraping: {str(error)}")
        return ScrapingResultBuilder(url).with_error(str(error)).build()
    
    @staticmethod
    def handle_parser_error(error: HtmlParserError, url: str) -> LocationScrapingResult:
        logger.error(f"HTML parser error during location scraping: {str(error)}")
        return ScrapingResultBuilder(url).with_error(str(error)).build()
    
    @staticmethod
    def handle_generic_error(error: Exception, url: str) -> LocationScrapingResult:
        logger.error(f"Unexpected error during location scraping: {str(error)}")
        return ScrapingResultBuilder(url).with_error(str(error)).build()


class LocationDataValidator:
    """Validator for location scraping data"""
    
    @staticmethod
    def validate_html_content(html_content: str) -> bool:
        return html_content is not None
    
    @staticmethod
    def validate_locations(locations: List[Location]) -> bool:
        return locations is not None
    
    @staticmethod
    def validate_timeout(timeout: int) -> int:
        return max(0, timeout) if timeout is not None else 30


class DepoBangunanLocationScraper(ILocationScraper):
    """Scraper for fetching and parsing location data from Depo Bangunan website"""
    
    def __init__(self, 
                 http_client: IHttpClient, 
                 location_parser: ILocationParser,
                 config: LocationScraperConfiguration = None,
                 error_handler: ErrorHandler = None,
                 validator: LocationDataValidator = None):
        self._http_client = http_client
        self._location_parser = location_parser
        self._config = config or LocationScraperConfiguration(
            "https://www.depobangunan.co.id/gerai-depo-bangunan"
        )
        self._error_handler = error_handler or ErrorHandler()
        self._validator = validator or LocationDataValidator()
    
    def scrape_locations(self, timeout: int = 30) -> LocationScrapingResult:
        """Scrape location data from the Depo Bangunan website"""
        timeout = self._validator.validate_timeout(timeout)
        url = self._config.get_base_url()
        
        try:
            html_content = self._fetch_html_content(url, timeout)
            locations = self._parse_locations(html_content)
            
            return self._create_success_result(locations, url)
            
        except HttpClientError as e:
            return self._error_handler.handle_http_error(e, url)
        except HtmlParserError as e:
            return self._error_handler.handle_parser_error(e, url)
        except Exception as e:
            return self._error_handler.handle_generic_error(e, url)
    
    def _fetch_html_content(self, url: str, timeout: int) -> str:
        """Fetch HTML content from the URL"""
        html_content = self._http_client.get(url, timeout=timeout)
        
        if not self._validator.validate_html_content(html_content):
            raise HttpClientError("Received None or empty content from HTTP client")
        
        return html_content
    
    def _parse_locations(self, html_content: str) -> List[Location]:
        """Parse locations from HTML content"""
        locations = self._location_parser.parse_locations(html_content)
        
        if not self._validator.validate_locations(locations):
            raise HtmlParserError("Location parser returned None")
        
        return locations
    
    def _create_success_result(self, locations: List[Location], url: str) -> LocationScrapingResult:
        """Create a successful scraping result"""
        return ScrapingResultBuilder(url).with_success(locations).build()
