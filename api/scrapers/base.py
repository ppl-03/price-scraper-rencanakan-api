import requests
import logging
import time
import re
from typing import List, Optional, Union, Any
from urllib.parse import urlencode, urljoin

from ..interfaces import (
    IHttpClient, IUrlBuilder, IHtmlParser, IPriceScraper,
    Product, ScrapingResult,
    HttpClientError, UrlBuilderError, HtmlParserError, ScraperError
)
from ..config import config

logger = logging.getLogger(__name__)


class BaseHttpClient(IHttpClient):
    
    def __init__(self, user_agent: str = None, max_retries: int = None, retry_delay: float = None):
        self.session = requests.Session()
        self.max_retries = max_retries or config.max_retries
        self.retry_delay = retry_delay or config.retry_delay
        self.last_request_time = 0
        
        # Enhanced headers for better compatibility with modern websites
        self.session.headers.update({
            'User-Agent': user_agent or config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
    
    def get(self, url: str, timeout: int = None) -> str:
        timeout = timeout or config.request_timeout
        self._rate_limit()
        
        return self._execute_with_retry(lambda: self._attempt_request(url, timeout))
    
    def _execute_with_retry(self, request_func):
        """Execute a request function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return request_func()
            except HttpClientError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request failed, retrying in {self.retry_delay} seconds: {last_exception}")
                    time.sleep(self.retry_delay)
        
        raise last_exception
    
    def _attempt_request(self, url: str, timeout: int) -> str:
        try:
            self._log_request_start(url)
            response = self.session.get(url, timeout=timeout)
            self._log_response(response)
            
            response.raise_for_status()
            
            if not response.content:
                raise HttpClientError(f"Empty response from {url}")
            
            html_content = self._decode_response(response)
            self._log_request_success(url, html_content)
            
            return html_content
            
        except requests.exceptions.Timeout:
            raise self._handle_timeout_error(url, timeout)
        except requests.exceptions.ConnectionError as e:
            raise HttpClientError(f"Connection error for {url}: {str(e)}")
        except requests.exceptions.HTTPError as e:
            raise HttpClientError(f"HTTP error {e.response.status_code} for {url}")
        except requests.exceptions.RequestException as e:
            raise HttpClientError(f"Request failed for {url}: {str(e)}")
        except Exception as e:
            raise HttpClientError(f"Unexpected error fetching {url}: {str(e)}")
    
    def _log_request_start(self, url: str):
        """Log request start if logging is enabled."""
        if config.log_requests:
            logger.info(f"Fetching URL: {url}")
            try:
                logger.debug(f"Request headers: {dict(self.session.headers)}")
            except (TypeError, AttributeError):
                pass
    
    def _log_response(self, response):
        """Log response details if logging is enabled."""
        if config.log_requests:
            logger.info(f"Response status: {response.status_code}")
            try:
                logger.debug(f"Response headers: {dict(response.headers)}")
            except (TypeError, AttributeError):
                pass
    
    def _decode_response(self, response) -> str:
        """Decode response content to string."""
        encoding = response.encoding or 'utf-8'
        return response.content.decode(encoding, errors='ignore')
    
    def _log_request_success(self, url: str, html_content: str):
        """Log successful request if logging is enabled."""
        if config.log_requests:
            logger.info(f"Successfully fetched {len(html_content)} characters from {url}")
            logger.debug(f"First 500 chars of response: {html_content[:500]}")
    
    def _handle_timeout_error(self, url: str, timeout: int) -> HttpClientError:
        """Handle timeout errors with proper logging."""
        logger.error(f"Request timeout after {timeout} seconds for {url}")
        return HttpClientError(f"Request timeout after {timeout} seconds for {url}")
    
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
    
    def _handle_scraping_error(self, error: Exception, context: str, url: str = None) -> ScrapingResult:
        """Handle scraping errors with consistent logging and result creation."""
        if isinstance(error, (UrlBuilderError, HttpClientError, HtmlParserError)):
            logger.error(f"{context} failed: {str(error)}")
            return ScrapingResult(
                products=[],
                success=False,
                error_message=str(error),
                url=getattr(error, 'url', url)
            )
        else:
            logger.error(f"Unexpected error during {context.lower()}: {str(error)}")
            return ScrapingResult(
                products=[],
                success=False,
                error_message=f"Unexpected error: {str(error)}"
            )
    
    def _execute_scraping_operation(self, operation_func, context: str, url: str = None):
        """Execute a scraping operation with consistent error handling."""
        try:
            return operation_func()
        except Exception as e:
            return self._handle_scraping_error(e, context, url)
    
    def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> ScrapingResult:
        def _scrape_operation():
            url = self.url_builder.build_search_url(keyword, sort_by_price, page)
            html_content = self.http_client.get(url)
            products = self.html_parser.parse_products(html_content)
            
            return ScrapingResult(
                products=products,
                success=True,
                url=url
            )
        
        return self._execute_scraping_operation(_scrape_operation, "Scraping")
    
    def scrape_product_details(self, product_url: str) -> Optional[Product]:
        def _scrape_details_operation():
            html_content = self.http_client.get(product_url)
            
            if hasattr(self.html_parser, 'parse_product_details'):
                return self.html_parser.parse_product_details(html_content, product_url)
            else:
                logger.warning("HTML parser does not support detailed product parsing")
                return None
        
        try:
            return _scrape_details_operation()
        except (HttpClientError, HtmlParserError) as e:
            logger.error(f"Failed to scrape product details from {product_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping product details from {product_url}: {str(e)}")
            return None


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
