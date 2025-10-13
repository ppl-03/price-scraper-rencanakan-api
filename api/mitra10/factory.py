from api.playwright_client import PlaywrightHttpClient
from .url_builder import Mitra10UrlBuilder
from .html_parser import Mitra10HtmlParser
from .scraper import Mitra10PriceScraper
from .location_scraper import Mitra10LocationScraper
from .location_parser import Mitra10LocationParser

def create_mitra10_scraper():
    http_client = PlaywrightHttpClient()
    url_builder = Mitra10UrlBuilder()
    html_parser = Mitra10HtmlParser()
    
    return Mitra10PriceScraper(http_client, url_builder, html_parser)

def create_mitra10_location_scraper():
    http_client = PlaywrightHttpClient()
    location_parser = Mitra10LocationParser()

    return Mitra10LocationScraper(http_client, location_parser)
