from api.selenium_client import SeleniumHttpClient
from api.interfaces import IPriceScraper
from api.mitra10.url_builder import Mitra10UrlBuilder
from api.mitra10.html_parser import Mitra10HtmlParser
from api.mitra10.scraper import Mitra10PriceScraper


def create_mitra10_scraper() -> IPriceScraper:
    http_client = SeleniumHttpClient()
    url_builder = Mitra10UrlBuilder()
    html_parser = Mitra10HtmlParser()

    return Mitra10PriceScraper(http_client, url_builder, html_parser)