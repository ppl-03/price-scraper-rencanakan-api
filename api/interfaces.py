from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Location:
    name: str
    code: Optional[str] = None


@dataclass
class LocationScrapingResult:
    locations: List[Location]
    success: bool
    error_message: Optional[str] = None
    attempts_made: int = 1


@dataclass
class Product:
    name: str
    price: int
    url: str
    unit: Optional[str] = None
    location: Optional[str] = None


@dataclass
class ScrapingResult:
    products: List[Product]
    success: bool
    error_message: Optional[str] = None
    url: Optional[str] = None


@dataclass
class Location:
    store_name: str
    address: str


@dataclass
class LocationScrapingResult:
    locations: List[Location]
    success: bool
    error_message: Optional[str] = None
    url: Optional[str] = None


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