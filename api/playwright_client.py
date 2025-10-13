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
            
        if not self.browser:
            # Use more stealth-friendly browser arguments
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-extensions',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--disable-features=VizDisplayCompositor'
            ]
            
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
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True,
                java_script_enabled=True,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'max-age=0'
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
    
    def get_with_interaction(self, url: str, button_selector: str, wait_selector: str, timeout: int = 60) -> str:
        """Get page content after performing interactions (for Mitra10 dropdown)"""
        try:
            # Check if we're in an async context
            try:
                # If we're already in a loop, we need to run in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._sync_get_with_interaction, url, button_selector, wait_selector, timeout)
                    return future.result(timeout=timeout + 10)
            except RuntimeError:
                # No running loop, we can create our own
                if self._loop is None or self._loop.is_closed():
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                
                return self._loop.run_until_complete(
                    asyncio.wait_for(self._async_get_with_interaction(url, button_selector, wait_selector), timeout=timeout)
                )
            
        except asyncio.TimeoutError:
            logger.error(f"Interaction timeout after {timeout}s for {url}")
            raise HttpClientError(f"Interaction timeout after {timeout}s for {url}")
        except Exception as e:
            logger.error(f"Playwright interaction failed for {url}: {e}")
            raise HttpClientError(f"Interaction failed for {url}: {e}")
    
    def _sync_get_with_interaction(self, url: str, button_selector: str, wait_selector: str, timeout: int = 60) -> str:
        """Synchronous wrapper for interaction method"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                asyncio.wait_for(self._async_get_with_interaction(url, button_selector, wait_selector), timeout=timeout)
            )
        finally:
            loop.close()
    
    async def _async_get(self, url: str) -> str:
        await self._ensure_browser()
        
        try:
            response = await self.page.goto(url)
            
            if not response or not response.ok:
                raise HttpClientError(f"HTTP {response.status if response else 'Unknown'} for {url}")
            
            await self.page.wait_for_load_state('networkidle')
            
            content = await self.page.content()
            return content
            
        except Exception as e:
            raise HttpClientError(f"Failed to fetch {url}: {e}")
    
    async def _async_get_with_interaction(self, url: str, button_selector: str, wait_selector: str) -> str:
        """Navigate to URL and perform interactions to get dynamic content"""
        await self._ensure_browser()
        
        try:
            # Navigate to the page
            logger.info(f"Navigating to {url}")
            response = await self.page.goto(url)
            
            if not response or not response.ok:
                raise HttpClientError(f"HTTP {response.status if response else 'Unknown'} for {url}")
            
            # Wait for page to be fully loaded
            await self.page.wait_for_load_state('networkidle', timeout=30000)
            logger.info("Page loaded, looking for location button...")
            
            # Simple inline interaction - click the button and wait for dropdown
            try:
                # Wait for the button to be available
                await self.page.wait_for_selector(button_selector, timeout=10000)
                logger.info(f"Found button with selector: {button_selector}")
                
                # Click the button to open dropdown
                await self.page.click(button_selector)
                logger.info("Clicked location button")
                
                # Wait for dropdown to appear
                await self.page.wait_for_selector(wait_selector, timeout=10000)
                logger.info(f"Dropdown appeared: {wait_selector}")
                
                # Wait a bit for the dropdown to be fully populated
                await self.page.wait_for_timeout(2000)
                
                logger.info("Interaction successful, getting page content...")
                content = await self.page.content()
                return content
                
            except Exception as interaction_error:
                logger.warning(f"Interaction failed: {interaction_error}, returning current page content")
                content = await self.page.content()
                return content
            
        except Exception as e:
            logger.error(f"Interaction failed: {e}")
            raise HttpClientError(f"Failed to interact with {url}: {e}")
    
    def close(self):
        try:
            # Check if we're in an async context
            try:
                asyncio.get_running_loop()
                # In async context, schedule the close
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._sync_close)
                    future.result(timeout=10)
            except RuntimeError:
                # Not in async context, use loop directly
                if self._loop and not self._loop.is_closed():
                    self._loop.run_until_complete(self._async_close())
        except Exception as e:
            logger.warning(f"Error during close: {e}")
        finally:
            self.browser = None
            self.context = None
            self.page = None
            self.playwright = None
    
    def _sync_close(self):
        """Synchronous wrapper for close method"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_close())
        finally:
            loop.close()
    
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
    
    def get_with_interaction(self, url: str, button_selector: str, wait_selector: str, timeout: int = 60) -> str:
        """Get page content after performing interactions (for Mitra10 dropdown)"""
        if self.client is None:
            raise RuntimeError("BatchPlaywrightClient must be used as a context manager")
        return self.client.get_with_interaction(url, button_selector, wait_selector, timeout)


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