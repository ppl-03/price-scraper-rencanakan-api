from api.core import BaseHttpClient
from api.interfaces import IPriceScraper
from .url_builder import TokopediaUrlBuilder
from .html_parser import TokopediaHtmlParser
from .scraper import TokopediaPriceScraper


def create_tokopedia_scraper() -> IPriceScraper:
    """
    Factory function to create a fully configured Tokopedia scraper.
    
    Returns:
        IPriceScraper: Configured scraper instance
    """
    http_client = BaseHttpClient()
    url_builder = TokopediaUrlBuilder()
    html_parser = TokopediaHtmlParser()
    
    return TokopediaPriceScraper(http_client, url_builder, html_parser)