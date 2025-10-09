from api.core import BaseHttpClient
from api.interfaces import IPriceScraper
from .url_builder import DepoUrlBuilder
from .html_parser import DepoHtmlParser
from .scraper import DepoPriceScraper


def create_depo_scraper() -> IPriceScraper:
    http_client = BaseHttpClient()
    url_builder = DepoUrlBuilder()
    html_parser = DepoHtmlParser()
    
    return DepoPriceScraper(http_client, url_builder, html_parser)