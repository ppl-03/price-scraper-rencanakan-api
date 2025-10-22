from api.interfaces import IPriceScraper
from .http_client import TokopediaHttpClient
from .url_builder import TokopediaUrlBuilder
from .html_parser import TokopediaHtmlParser
from .scraper import TokopediaPriceScraper


def create_tokopedia_scraper() -> IPriceScraper:
    """
    Factory function to create a fully configured Tokopedia scraper.
    
    Uses TokopediaHttpClient with enhanced headers for better compatibility,
    especially important for cloud deployments (Azure, AWS, etc.).
    
    Returns:
        IPriceScraper: Configured scraper instance
    """
    http_client = TokopediaHttpClient()
    url_builder = TokopediaUrlBuilder()
    html_parser = TokopediaHtmlParser()
    
    return TokopediaPriceScraper(http_client, url_builder, html_parser)