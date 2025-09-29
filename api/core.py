import requests
import logging
import time
import re
from typing import List, Optional, Union, Any
from urllib.parse import urlencode, urljoin

from .interfaces import (
    IHttpClient, IUrlBuilder, IHtmlParser, IPriceScraper,
    Product, ScrapingResult,
    HttpClientError, UrlBuilderError, HtmlParserError, ScraperError
)
from .config import config

logger = logging.getLogger(__name__)


class BaseHttpClient(IHttpClient):
    
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
                return self._attempt_request(url, timeout, attempt)
            except HttpClientError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request failed, retrying in {self.retry_delay} seconds: {last_exception}")
                    time.sleep(self.retry_delay)
        
        raise last_exception
    
    def _attempt_request(self, url: str, timeout: int, attempt: int) -> str:
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
            
        except requests.exceptions.Timeout:
            raise HttpClientError(f"Request timeout after {timeout} seconds for {url}")
        except requests.exceptions.ConnectionError as e:
            raise HttpClientError(f"Connection error for {url}: {str(e)}")
        except requests.exceptions.HTTPError as e:
            raise HttpClientError(f"HTTP error {e.response.status_code} for {url}")
        except requests.exceptions.RequestException as e:
            raise HttpClientError(f"Request failed for {url}: {str(e)}")
        except Exception as e:
            raise HttpClientError(f"Unexpected error fetching {url}: {str(e)}")
    
    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < config.min_request_interval:
            sleep_time = config.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class BaseUrlBuilder(IUrlBuilder):
    
    def __init__(self, base_url: str, search_path: str):
        self.base_url = base_url
        self.search_path = search_path
    
    def build_search_url(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> str:
        try:
            if not keyword or not keyword.strip():
                raise UrlBuilderError("Keyword cannot be empty")
            
            if page < 0:
                raise UrlBuilderError("Page number cannot be negative")
            
            params = self._build_params(keyword.strip(), sort_by_price, page)
            
            full_url = urljoin(self.base_url, self.search_path)
            url = f"{full_url}?{urlencode(params)}"
            logger.debug(f"Built URL: {url}")
            return url
            
        except Exception as e:
            raise UrlBuilderError(f"Failed to build URL: {str(e)}")
    
    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        params = {
            'keyword': keyword,
            'page': page
        }
        
        if sort_by_price:
            params['sort'] = 'price_asc'
        
        return params


class BasePriceScraper(IPriceScraper):
    
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


def clean_price_digits(price_string: Union[str, Any]) -> int:
    if price_string is None:
        raise TypeError("price_string cannot be None")
    
    if not isinstance(price_string, str):
        raise TypeError("price_string must be a string")
    
    if not price_string:
        return 0
    
    digits = re.findall(r'\d', price_string)
    if not digits:
        return 0
    
    return int("".join(digits))