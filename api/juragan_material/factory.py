from api.core import BaseHttpClient
from api.interfaces import IPriceScraper
from .url_builder import JuraganMaterialUrlBuilder
from .html_parser import JuraganMaterialHtmlParser
from .scraper import JuraganMaterialPriceScraper


def create_juraganmaterial_scraper() -> IPriceScraper:
    """
    Factory function to create a fully configured Juragan Material scraper.
    
    Returns:
        IPriceScraper: Configured scraper instance
    """
    http_client = BaseHttpClient()
    url_builder = JuraganMaterialUrlBuilder()
    html_parser = JuraganMaterialHtmlParser()
    
    return JuraganMaterialPriceScraper(http_client, url_builder, html_parser)