import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from api.interfaces import IHttpClient, HttpClientError

logger = logging.getLogger(__name__)

# this playwright client is only for MasPetruk (HSPK) pages
class GovernmentWagePlaywrightClient(IHttpClient):
    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        region_label: Optional[str] = "Kab. Cilacap",
        auto_select_region: bool = True,
    ):
        self.headless = headless
        self.browser_type = browser_type
        self.region_label = region_label
        self.auto_select_region = auto_select_region

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._loop = None

    # ---------- lifecycle ----------
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
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

        if not self.page:
            self.page = await self.context.new_page()

    def get(self, url: str, timeout: int = 90) -> str:
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
            # 1) Load MasPetruk HSPK page
            response = await self.page.goto(url, wait_until="domcontentloaded")
            if not response or not response.ok:
                raise HttpClientError(f"HTTP {response.status if response else 'Unknown'} for {url}")

            # 2) Ensure region (dropdown exists on this page)
            if self.auto_select_region and self.region_label:
                try:
                    await self.page.wait_for_selector("select.form-control", timeout=5000)
                    try:
                        await self.page.select_option("select.form-control", label=self.region_label)
                    except Exception:
                        # fallback click if select_option fails
                        await self.page.click("select.form-control")
                        await self.page.locator("select.form-control option", has_text=self.region_label).click()
                except Exception:
                    pass

            # 3) Wait for DataTables rows to render
            await self.page.wait_for_selector("table.dataTable tbody tr", timeout=60000)

            # 4) Ensure 'Uraian Pekerjaan' anchor texts are present and non-empty
            await self.page.wait_for_function(
                """
                () => {
                    const rows = document.querySelectorAll('table.dataTable tbody tr');
                    if (rows.length === 0) return false;
                    const anchors = document.querySelectorAll('table.dataTable tbody tr td:nth-child(3) a.hspk');
                    return anchors.length > 0 && Array.from(anchors).every(a => (a.textContent || '').trim().length > 0);
                }
                """,
                timeout=60000
            )

            await self.page.wait_for_load_state("networkidle", timeout=15000)

            try:
                count = await self.page.evaluate(
                    "document.querySelectorAll('table.dataTable tbody tr').length"
                )
                first = await self.page.evaluate(
                    "(() => { const a = document.querySelector('table.dataTable tbody tr td:nth-child(3) a.hspk'); return a ? a.textContent.trim() : ''; })()"
                )
                logger.info(f"MasPetruk rows: {count} | First uraian: {first[:60]}")
            except Exception:
                pass

            return await self.page.content()

        except Exception as e:
            raise HttpClientError(f"Failed to fetch {url}: {e}")

    # ---------- cleanup ----------
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
