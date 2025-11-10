from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Location:
    """
    Unified Location class supporting multiple use cases.
    Can be used with name/code or store_name/address patterns.
    """
    name: str
    code: Optional[str] = None
    store_name: Optional[str] = None
    address: Optional[str] = None
    
    def __post_init__(self):
        # Ensure both patterns are available by syncing fields
        # If store_name/address are provided, use them as primary
        if self.store_name and not self.name:
            self.name = self.store_name
        if self.address and not self.code:
            self.code = self.address
        
        # If name/code are provided, also populate store_name/address
        if self.name and not self.store_name:
            self.store_name = self.name
        if self.code and not self.address:
            self.address = self.code


@dataclass
class LocationScrapingResult:
    """
    Result of a location scraping operation.
    Includes locations found, success status, error messages, and metadata.
    """
    locations: List[Location]
    success: bool
    error_message: Optional[str] = None
    attempts_made: int = 1
    url: Optional[str] = None


@dataclass
class Product:
    name: str
    price: int
    url: str
    unit: Optional[str] = None
    location: Optional[str] = None
    sold_count: Optional[int] = None


@dataclass
class ScrapingResult:
    products: List[Product]
    success: bool
    error_message: Optional[str] = None
    url: Optional[str] = None
    
    def __len__(self):
        """Return the number of products in the result"""
        return len(self.products)


class IHttpClient(ABC):
    @abstractmethod
    def get(self, url: str, timeout: int = 30) -> str:
        pass


class IUrlBuilder(ABC):
    @abstractmethod
    def build_search_url(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> str:
        pass


class IHtmlParser(ABC):
    @abstractmethod
    def parse_products(self, html_content: str) -> List[Product]:
        pass


class IPriceScraper(ABC):
    @abstractmethod
    def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> ScrapingResult:
        pass


class ILocationParser(ABC):
    @abstractmethod
    def parse_locations(self, html_content: str) -> List[str]:
        pass


class ILocationScraper(ABC):
    @abstractmethod
    def scrape_locations_batch(self, timeout: Optional[int] = None) -> LocationScrapingResult:
        pass


class ILocationValidator(ABC):
    @abstractmethod
    def validate_html_content(self, html_content: str) -> bool:
        pass
    
    @abstractmethod
    def validate_locations(self, locations: List[str]) -> bool:
        pass


class HttpClientError(Exception):
    pass


class UrlBuilderError(Exception):
    pass


class HtmlParserError(Exception):
    pass


class ScraperError(Exception):
    pass


class LocationParserError(Exception):
    pass


class LocationScraperError(Exception):
    pass


class LocationValidatorError(Exception):
    pass