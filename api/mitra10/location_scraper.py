import asyncio
import logging
from api.playwright_client import BatchPlaywrightClient
from .location_parser import Mitra10LocationParser

logger = logging.getLogger(__name__)

class Mitra10LocationScraper:
    def scrape_locations(self):
        url = "https://www.mitra10.com/"
        try:
            with BatchPlaywrightClient(headless=True) as batch:
                # Use the inner Playwright client
                client = batch.client
                store_names = asyncio.run(self._extract_locations(client, url))
            return {
                "success": True,
                "locations": store_names,
                "error_message": ""
            }
        except Exception as e:
            logging.exception(f"Error while scraping Mitra10 locations: {e}")
            return {
                "success": False,
                "locations": [],
                "error_message": str(e)
            }

    async def _extract_locations(self, client, url):
        await client._ensure_browser()
        page = client.page
        # Increase timeout to 5 minutes (300000ms) for initial page load
        await page.goto(url, timeout=300000)

        # remove leftover geolocation banners
        try:
            await page.evaluate("""
                document.querySelectorAll('[id*="geo"], [class*="geo"]').forEach(el => el.remove());
            """)
        except Exception:
            pass

        # Increase timeout to 5 minutes for networkidle state on heavy JavaScript sites
        await page.wait_for_load_state("networkidle", timeout=300000)

        # close popup by clicking outside if present
        try:
            await page.wait_for_timeout(1500)
            if await page.locator(".MuiDialog-root, #popup-promo").count() > 0:
                await page.mouse.click(100, 100)
                await page.wait_for_timeout(1000)
        except Exception as e:
            logger.warning(f"[Playwright] Popup click close failed: {e}")

        # wait until store button appears
        await page.wait_for_selector("button.MuiButtonBase-root.jss368", state="visible", timeout=60000)
        pilih_button = page.locator("button.MuiButtonBase-root.jss368").first

        # React hydration: wait until button text updates
        await page.wait_for_function(
            """() => {
                const btn = document.querySelector('button.MuiButtonBase-root.jss368');
                if (!btn || btn.offsetParent === null) return false;
                const text = btn.innerText.toUpperCase();
                return text.includes("PILIH TOKO") || text.startsWith("MITRA10 ");
            }""",
            timeout=60000
        )

        await pilih_button.scroll_into_view_if_needed()
        await page.wait_for_timeout(1000)

        clicked = False
        for attempt in range(3):
            try:
                await pilih_button.click(force=True)
                logger.info(f"[Playwright] Clicked store selector (attempt {attempt + 1})")
                clicked = True
                break
            except Exception as e:
                logger.warning(f"[Playwright] Click attempt {attempt + 1} failed: {e}")
                await page.mouse.move(200, 200)
                await page.mouse.down()
                await page.mouse.up()
                await page.wait_for_timeout(1000)

        if not clicked:
            raise TimeoutError("Failed to click store selector after 3 attempts")

        # wait for dropdown to appear with increased timeout (60 seconds)
        await page.wait_for_selector("div[role='presentation'] li span", timeout=60000)
        logger.info("[Playwright] Dropdown appeared successfully!")

        # get page content and parse locations using the parser
        page_content = await page.content()
        locations = Mitra10LocationParser.parse(page_content)

        return locations
