from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


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


class HttpClientError(Exception):
    pass


class UrlBuilderError(Exception):
    pass


class HtmlParserError(Exception):
    pass


class ScraperError(Exception):
    pass