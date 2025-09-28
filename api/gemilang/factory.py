from api.core import BaseHttpClient
from api.interfaces import IPriceScraper
from .url_builder import GemilangUrlBuilder
from .html_parser import GemilangHtmlParser
from .scraper import GemilangPriceScraper


def create_gemilang_scraper() -> IPriceScraper:
    http_client = BaseHttpClient()
    url_builder = GemilangUrlBuilder()
    html_parser = GemilangHtmlParser()
    
    return GemilangPriceScraper(http_client, url_builder, html_parser)