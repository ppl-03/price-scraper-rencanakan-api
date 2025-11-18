from api.core import BaseHttpClient
from api.interfaces import IPriceScraper, ILocationScraper
from .url_builder import DepoUrlBuilder
from .html_parser import DepoHtmlParser
from .scraper import DepoPriceScraper
from .location_parser import DepoBangunanLocationParser
from .location_scraper import DepoBangunanLocationScraper


def create_depo_scraper() -> IPriceScraper:
    http_client = BaseHttpClient()
    url_builder = DepoUrlBuilder()
    html_parser = DepoHtmlParser()
    
    return DepoPriceScraper(http_client, url_builder, html_parser)


def create_depo_location_scraper() -> ILocationScraper:
    """Factory function to create a Depo Bangunan location scraper"""
    http_client = BaseHttpClient()
    location_parser = DepoBangunanLocationParser()
    
    return DepoBangunanLocationScraper(http_client, location_parser)
