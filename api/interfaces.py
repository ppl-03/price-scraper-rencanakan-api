from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Product:
    name: str
    price: int
    url: str
    unit: Optional[str] = None


@dataclass
class Location:
    store_name: str
    address: str


@dataclass
class ScrapingResult:
    products: List[Product]
    success: bool
    error_message: Optional[str] = None
    url: Optional[str] = None


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


class ILocationParser(ABC):
    @abstractmethod
    def parse_locations(self, html_content: str) -> List[Location]:
        pass


class IPriceScraper(ABC):
    @abstractmethod
    def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> ScrapingResult:
        pass
    
    def scrape_product_details(self, product_url: str) -> Optional[Product]:
        pass


class ILocationScraper(ABC):
    @abstractmethod
    def scrape_locations(self, timeout: int = 30) -> LocationScrapingResult:
        pass


class HttpClientError(Exception):
    pass


class UrlBuilderError(Exception):
    pass


class HtmlParserError(Exception):
    pass


class ScraperError(Exception):
    pass