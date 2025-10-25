import logging
from typing import List, Optional
from abc import ABC, abstractmethod

from api.interfaces import (
    IHttpClient, ILocationParser, ILocationScraper,
    LocationScrapingResult, Location, HttpClientError, HtmlParserError
)

logger = logging.getLogger(__name__)


class LocationScraperConfiguration:
    
    def __init__(self, base_url: str, default_timeout: int = 60):
        self.base_url = base_url
        self.default_timeout = default_timeout
    
    def get_base_url(self) -> str:
        return self.base_url
    
    def get_default_timeout(self) -> int:
        return self.default_timeout


class ScrapingResultBuilder:
    
    def __init__(self):
        self._locations = []
        self._success = False
        self._error_message = None
        self._attempts_made = 1
    
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
            attempts_made=self._attempts_made
        )


class ErrorHandler:
    
    @staticmethod
    def handle_http_error(error: HttpClientError) -> LocationScrapingResult:
        logger.error(f"HTTP client error during location scraping: {str(error)}")
        return ScrapingResultBuilder().with_error(str(error)).build()
    
    @staticmethod
    def handle_parser_error(error: HtmlParserError) -> LocationScrapingResult:
        logger.error(f"HTML parser error during location scraping: {str(error)}")
        return ScrapingResultBuilder().with_error(str(error)).build()
    
    @staticmethod
    def handle_generic_error(error: Exception) -> LocationScrapingResult:
        logger.error(f"Unexpected error during location scraping: {str(error)}")
        return ScrapingResultBuilder().with_error(str(error)).build()


class LocationDataValidator:
    
    @staticmethod
    def validate_html_content(html_content: Optional[str]) -> bool:
        return html_content is not None
    
    @staticmethod
    def validate_locations(locations: List[Location]) -> bool:
        return locations is not None
    
    @staticmethod
    def validate_timeout(timeout: Optional[int]) -> int:
        return max(0, timeout) if timeout is not None else 60


class GemilangLocationScraper(ILocationScraper):
    
    def __init__(self, 
                 http_client: IHttpClient, 
                 location_parser: ILocationParser,
                 config: LocationScraperConfiguration = None,
                 error_handler: ErrorHandler = None,
                 validator: LocationDataValidator = None):
        self._http_client = http_client
        self._location_parser = location_parser
        self._config = config or LocationScraperConfiguration(
            "https://gemilang-store.com/pusat/store-locations"
        )
        self._error_handler = error_handler or ErrorHandler()
        self._validator = validator or LocationDataValidator()
    
    def scrape_locations_batch(self, timeout: Optional[int] = None) -> LocationScrapingResult:
        """Scrape location data from the Gemilang website (implements ILocationScraper interface)"""
        return self.scrape_locations(timeout if timeout is not None else 60)
    
    def scrape_locations(self, timeout: int = 60) -> LocationScrapingResult:
        timeout = self._validator.validate_timeout(timeout)
        url = self._config.get_base_url()
        
        try:
            html_content = self._fetch_html_content(url, timeout)
            locations = self._parse_locations(html_content)
            
            return self._create_success_result(locations)
            
        except HttpClientError as e:
            return self._error_handler.handle_http_error(e)
        except HtmlParserError as e:
            return self._error_handler.handle_parser_error(e)
        except Exception as e:
            return self._error_handler.handle_generic_error(e)
    
    def _fetch_html_content(self, url: str, timeout: int) -> str:
        html_content = self._http_client.get(url, timeout=timeout)
        
        if not self._validator.validate_html_content(html_content):
            raise HttpClientError("Received None or empty content from HTTP client")
        
        return html_content
    
    def _parse_locations(self, html_content: str) -> List[Location]:
        locations = self._location_parser.parse_locations(html_content)
        
        if not self._validator.validate_locations(locations):
            raise HtmlParserError("Location parser returned None")
        
        return locations
    
    def _create_success_result(self, locations: List[Location]) -> LocationScrapingResult:
        return ScrapingResultBuilder().with_success(locations).build()