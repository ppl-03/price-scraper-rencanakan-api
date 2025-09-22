import requests
import logging
import time
from urllib.parse import urlencode, urljoin
from typing import List, Optional
from bs4 import BeautifulSoup

from .interfaces import (
    IHttpClient, IUrlBuilder, IHtmlParser, IPriceScraper,
    Product, ScrapingResult,
    HttpClientError, UrlBuilderError, HtmlParserError, ScraperError
)
from .scraper import clean_price_gemilang
from .config import config

logging.basicConfig(level=getattr(logging, config.log_level))
logger = logging.getLogger(__name__)


class RequestsHttpClient(IHttpClient):
    
    def __init__(self, user_agent: str = None, max_retries: int = None, retry_delay: float = None):
        self.session = requests.Session()
        self.max_retries = max_retries or config.max_retries
        self.retry_delay = retry_delay or config.retry_delay
        self.last_request_time = 0
        
        self.session.headers.update({
            'User-Agent': user_agent or config.user_agent
        })
    
    def get(self, url: str, timeout: int = None) -> str:
        timeout = timeout or config.request_timeout
        self._rate_limit()
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                if config.log_requests:
                    logger.info(f"Fetching URL (attempt {attempt + 1}/{self.max_retries}): {url}")
                
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                
                if not response.content:
                    raise HttpClientError(f"Empty response from {url}")
                
                encoding = response.encoding or 'utf-8'
                html_content = response.content.decode(encoding, errors='ignore')
                
                if config.log_requests:
                    logger.info(f"Successfully fetched {len(html_content)} characters from {url}")
                return html_content
                
            except requests.exceptions.Timeout as e:
                last_exception = HttpClientError(f"Request timeout after {timeout} seconds for {url}")
            except requests.exceptions.ConnectionError as e:
                last_exception = HttpClientError(f"Connection error for {url}: {str(e)}")
            except requests.exceptions.HTTPError as e:
                last_exception = HttpClientError(f"HTTP error {e.response.status_code} for {url}")
            except requests.exceptions.RequestException as e:
                last_exception = HttpClientError(f"Request failed for {url}: {str(e)}")
            except Exception as e:
                last_exception = HttpClientError(f"Unexpected error fetching {url}: {str(e)}")
            
            if attempt < self.max_retries - 1:
                logger.warning(f"Request failed, retrying in {self.retry_delay} seconds: {last_exception}")
                time.sleep(self.retry_delay)
        
        raise last_exception
    
    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < config.min_request_interval:
            sleep_time = config.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class GemilangUrlBuilder(IUrlBuilder):
    
    def __init__(self, base_url: str = None, search_path: str = None):
        self.base_url = base_url or config.gemilang_base_url
        self.search_path = search_path or config.gemilang_search_path
    
    def build_search_url(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> str:
        try:
            if not keyword or not keyword.strip():
                raise UrlBuilderError("Keyword cannot be empty")
            
            if page < 0:
                raise UrlBuilderError("Page number cannot be negative")
            
            params = {
                'keyword': keyword.strip(),
                'page': page
            }
            
            if sort_by_price:
                params['sort'] = 'price_asc'
            
            full_url = urljoin(self.base_url, self.search_path)
            url = f"{full_url}?{urlencode(params)}"
            logger.debug(f"Built URL: {url}")
            return url
            
        except Exception as e:
            raise UrlBuilderError(f"Failed to build URL: {str(e)}")


class GemilangHtmlParser(IHtmlParser):
    
    def parse_products(self, html_content: str) -> List[Product]:
        try:
            if not html_content:
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            products = []
            
            product_items = soup.find_all('div', class_='item-product')
            logger.info(f"Found {len(product_items)} product items in HTML")
            
            for item in product_items:
                try:
                    product = self._extract_product_from_item(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"Failed to extract product from item: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(products)} products")
            return products
            
        except Exception as e:
            raise HtmlParserError(f"Failed to parse HTML: {str(e)}")
    
    def _extract_product_from_item(self, item) -> Optional[Product]:
        name_link = item.find('a')
        if not name_link:
            return None
            
        name_element = name_link.find('p', class_='product-name')
        if not name_element:
            return None
            
        name = name_element.get_text(strip=True)
        if not name:
            return None
            
        url = name_link.get('href', '')
        
        price_wrapper = item.find('div', class_='price-wrapper')
        if not price_wrapper:
            return None
            
        price_element = price_wrapper.find('p', class_='price')
        if not price_element:
            return None
            
        price_text = price_element.get_text(strip=True)
        
        try:
            price = clean_price_gemilang(price_text)
        except (TypeError, ValueError):
            return None
        
        if name and price > 0 and url:
            return Product(name=name, price=price, url=url)
        
        return None


class GemilangPriceScraper(IPriceScraper):
    
    def __init__(self, http_client: IHttpClient, url_builder: IUrlBuilder, html_parser: IHtmlParser):
        self.http_client = http_client
        self.url_builder = url_builder
        self.html_parser = html_parser
    
    def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> ScrapingResult:
        try:
            url = self.url_builder.build_search_url(keyword, sort_by_price, page)
            html_content = self.http_client.get(url)
            products = self.html_parser.parse_products(html_content)
            
            return ScrapingResult(
                products=products,
                success=True,
                url=url
            )
            
        except (UrlBuilderError, HttpClientError, HtmlParserError) as e:
            logger.error(f"Scraping failed: {str(e)}")
            return ScrapingResult(
                products=[],
                success=False,
                error_message=str(e),
                url=getattr(e, 'url', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {str(e)}")
            return ScrapingResult(
                products=[],
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )


def create_gemilang_scraper() -> IPriceScraper:
    http_client = RequestsHttpClient()
    url_builder = GemilangUrlBuilder()
    html_parser = GemilangHtmlParser()
    
    return GemilangPriceScraper(http_client, url_builder, html_parser)