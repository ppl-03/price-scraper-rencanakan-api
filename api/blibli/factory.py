from api.playwright_client import PlaywrightHttpClient
from .url_builder import BlibliUrlBuilder
from .html_parser import BlibliHtmlParser
from .scraper import BlibliPriceScraper

def create_blibli_scraper():
    http_client = PlaywrightHttpClient()
    url_builder = BlibliUrlBuilder()
    html_parser = BlibliHtmlParser()
    return BlibliPriceScraper(http_client, url_builder, html_parser)
