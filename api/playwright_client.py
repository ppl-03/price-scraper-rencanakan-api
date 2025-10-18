import asyncio
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
        
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-extensions',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--disable-features=VizDisplayCompositor'
            ]
                    
        if not self.browser:
            if self.browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=launch_args
                )
            elif self.browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
                
        if not self.context:
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="id-ID",
                timezone_id="Asia/Jakarta",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
            
        if not self.page:
            self.page = await self.context.new_page()
    
    def get(self, url: str, timeout: int = 30) -> str:
        try:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            
            return self._loop.run_until_complete(
                asyncio.wait_for(self._async_get(url), timeout=timeout)
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Request timeout after {timeout}s for {url}")
            raise HttpClientError(f"Request timeout after {timeout}s for {url}")
        except Exception as e:
            logger.error(f"Playwright request failed for {url}: {e}")
            raise HttpClientError(f"Request failed for {url}: {e}")
    
    async def _async_get(self, url: str) -> str:
        await self._ensure_browser()
        
        try:
            # Add random delay to avoid detection
            import random
            await asyncio.sleep(random.uniform(1, 3))
            
            response = await self.page.goto(url, wait_until="domcontentloaded")
            
            if not response or not response.ok:
                raise HttpClientError(f"HTTP {response.status if response else 'Unknown'} for {url}")
            
            # Check if we got redirected to a challenge page
            current_url = self.page.url
            if "/challenge/" in current_url or "verify" in current_url.lower():
                raise HttpClientError(f"Bot detection triggered - redirected to: {current_url}")
            
            # Wait for page to fully load
            await self.page.wait_for_load_state('networkidle')
            
            # For Blibli, wait for JavaScript content to load
            try:
                await self.page.wait_for_selector('#blibliApp', timeout=10000)
                
                # Wait for the catalog app to load
                await self.page.wait_for_selector('#app-collab-catalog-vue3', timeout=15000)
                
                # Wait for the skeleton loaders to disappear and actual content to appear
                await self.page.wait_for_function(
                    """() => {
                        // Check if skeleton loaders are gone (they disappear when content loads)
                        const skeletons = document.querySelectorAll('.product-list-skeleton, .blu-loader-skeleton');
                        
                        // Check if we have actual products
                        const products = document.querySelectorAll('a[href*="/p/"], [class*="product-card"], [class*="product-item"]');
                        
                        // Check for "no results" indicators
                        const noResults = document.body.innerText.toLowerCase().includes('tidak ditemukan') ||
                                        document.body.innerText.toLowerCase().includes('tidak ada hasil') ||
                                        document.body.innerText.toLowerCase().includes('maaf') ||
                                        document.querySelector('[class*="no-result"], [class*="empty"]');
                        
                        // Return true if we have products OR confirmed no results, AND skeletons are minimal
                        return (products.length > 0 || noResults) && skeletons.length < 5;
                    }""",
                    timeout=25000
                )
                
                # Give a final moment for any late-loading elements
                await asyncio.sleep(2)
                
            except Exception as wait_error:
                logger.warning(f"Timeout waiting for products to load: {wait_error}")
                # Continue anyway, maybe content loaded differently
            
            content = await self.page.content()
            return content
            
        except Exception as e:
            if "Bot detection" in str(e):
                raise  # Re-raise bot detection errors
            raise HttpClientError(f"Failed to fetch {url}: {e}")
    
    def close(self):
        if self._loop and not self._loop.is_closed():
            self._loop.run_until_complete(self._async_close())
        
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
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
    
    def __enter__(self):
        self.client = PlaywrightHttpClient(self.headless, self.browser_type)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
    
    def get(self, url: str, timeout: int = 30) -> str:
        if self.client is None:
            raise RuntimeError("BatchPlaywrightClient must be used as a context manager")
        return self.client.get(url, timeout=timeout)


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