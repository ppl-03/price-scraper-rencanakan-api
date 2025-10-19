from api.playwright_client import PlaywrightHttpClient
from api.interfaces import IPriceScraper
from .url_builder import Mitra10UrlBuilder
from .html_parser import Mitra10HtmlParser
from .scraper import Mitra10PriceScraper

def create_mitra10_scraper():
    http_client = PlaywrightHttpClient()
    url_builder = Mitra10UrlBuilder()
    html_parser = Mitra10HtmlParser()
    
    return Mitra10PriceScraper(http_client, url_builder, html_parser)
