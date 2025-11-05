from api.government_wage.gov_playwright_client import GovernmentWagePlaywrightClient
from .url_builder import GovernmentWageUrlBuilder
from .html_parser import GovernmentWageHtmlParser
from .scraper import GovernmentWageScraper

def create_government_wage_scraper(headless: bool = True, browser_type: str = "chromium") -> GovernmentWageScraper:
    http_client = GovernmentWagePlaywrightClient(
        headless=headless,
        browser_type=browser_type,
        region_label="Kab. Cilacap",        
        auto_select_region=True,
    )
    url_builder = GovernmentWageUrlBuilder()
    html_parser = GovernmentWageHtmlParser()
    return GovernmentWageScraper(http_client, url_builder, html_parser)