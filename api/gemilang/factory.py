from api.core import BaseHttpClient
from api.interfaces import IPriceScraper, ILocationScraper
from .url_builder import GemilangUrlBuilder
from .html_parser import GemilangHtmlParser
from .scraper import GemilangPriceScraper
from .location_parser import (
    GemilangLocationParser, TextCleaner, HtmlElementExtractor, 
    ParserConfiguration
)
from .location_scraper import (
    GemilangLocationScraper, LocationScraperConfiguration,
    ErrorHandler, LocationDataValidator
)


def create_gemilang_scraper() -> IPriceScraper:
    http_client = BaseHttpClient()
    url_builder = GemilangUrlBuilder()
    html_parser = GemilangHtmlParser()
    
    return GemilangPriceScraper(http_client, url_builder, html_parser)


def create_gemilang_location_scraper() -> ILocationScraper:
    http_client = BaseHttpClient()
    
    text_cleaner = TextCleaner()
    element_extractor = HtmlElementExtractor(text_cleaner)
    parser_config = ParserConfiguration()
    location_parser = GemilangLocationParser(text_cleaner, element_extractor, parser_config)
    
    scraper_config = LocationScraperConfiguration(
        "https://gemilang-store.com/pusat/store-locations"
    )
    error_handler = ErrorHandler()
    validator = LocationDataValidator()
    
    return GemilangLocationScraper(
        http_client, 
        location_parser, 
        scraper_config, 
        error_handler, 
        validator
    )


def create_gemilang_location_scraper_simple() -> ILocationScraper:
    http_client = BaseHttpClient()
    location_parser = GemilangLocationParser()
    
    return GemilangLocationScraper(http_client, location_parser)