from api.playwright_client import BatchPlaywrightClient
from .url_builder import Mitra10UrlBuilder
from .html_parser import Mitra10HtmlParser
from .scraper import Mitra10PriceScraper
from .location_scraper import Mitra10LocationScraper
from .location_parser import Mitra10LocationParser

def create_mitra10_scraper():
    # Pass BatchPlaywrightClient as http_client for integration test compatibility
    http_client = BatchPlaywrightClient()
    url_builder = Mitra10UrlBuilder()
    html_parser = Mitra10HtmlParser()
    
    return Mitra10PriceScraper(http_client, url_builder, html_parser)

def create_mitra10_location_scraper():
    return Mitra10LocationScraper()
