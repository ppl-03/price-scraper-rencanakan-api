import asyncio
from api.mitra10.url_builder import Mitra10UrlBuilder
from api.mitra10.html_parser import Mitra10HtmlParser
from api.mitra10.scraper import Mitra10PriceScraper
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from api.interfaces import IHttpClient, HttpClientError
import logging

logger = logging.getLogger(__name__)


class PlaywrightHttpClient(IHttpClient):
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._loop = None
    
    async def _ensure_browser(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
        if not self.browser:
            if self.browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(headless=self.headless)
            elif self.browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
                
        if not self.context:
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
        if not self.page:
            self.page = await self.context.new_page()
    
    def get(self, url: str, timeout: int = 30) -> str:
        try:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            
            return self._loop.run_until_complete(self._async_get(url, timeout))
            
        except Exception as e:
            logger.error(f"Playwright request failed for {url}: {e}")
            raise HttpClientError(f"Request failed for {url}: {e}")
    
    async def _async_get(self, url: str, timeout: int) -> str:
        await self._ensure_browser()
        
        try:
            response = await self.page.goto(url, timeout=timeout * 1000)
            
            if not response or not response.ok:
                raise HttpClientError(f"HTTP {response.status if response else 'Unknown'} for {url}")
            
            await self.page.wait_for_load_state('networkidle', timeout=timeout * 1000)
            
            content = await self.page.content()
            return content
            
        except Exception as e:
            raise HttpClientError(f"Failed to fetch {url}: {e}")
    
    def close(self):
        if self._loop and not self._loop.is_closed():
            self._loop.run_until_complete(self._async_close())
    
    async def _async_close(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class BatchPlaywrightClient:
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        self.headless = headless
        self.browser_type = browser_type
        self.client = None
    
    async def __aenter__(self):
        self.client = PlaywrightHttpClient(self.headless, self.browser_type)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client._async_close()
    
    def __enter__(self):
        self.client = PlaywrightHttpClient(self.headless, self.browser_type)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
    
    def get(self, url: str, timeout: int = 30) -> str:
        return self.client.get(url, timeout)


class RequestsHtmlClient(IHttpClient):

    def __init__(self):
        try:
            from requests_html import HTMLSession
            self.session = HTMLSession()
        except ImportError:
            raise ImportError("requests-html not installed. Run: pip install requests-html")
    
    def get(self, url: str, timeout: int = 30) -> str:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            response.html.render(timeout=timeout)
            
            return response.html.html
            
        except Exception as e:
            logger.error(f"Requests-HTML failed for {url}: {e}")
            raise HttpClientError(f"Request failed for {url}: {e}")
    
    def close(self):
        if hasattr(self.session, 'close'):
            self.session.close()


def create_alternative_mitra10_scraper(client_type: str = "playwright"):
    url_builder = Mitra10UrlBuilder()
    html_parser = Mitra10HtmlParser()
    
    if client_type == "playwright":
        http_client = PlaywrightHttpClient()
    elif client_type == "requests-html":
        http_client = RequestsHtmlClient()
    else:
        http_client = PlaywrightHttpClient()
    
    return Mitra10PriceScraper(http_client, url_builder, html_parser)