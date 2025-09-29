from api.core import BasePriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser


class JuraganMaterialPriceScraper(BasePriceScraper):
    """Price scraper implementation for Juragan Material website."""
    
    def __init__(self, http_client: IHttpClient, url_builder: IUrlBuilder, html_parser: IHtmlParser):
        """
        Initialize Juragan Material price scraper.
        
        Args:
            http_client: HTTP client for making requests
            url_builder: URL builder for constructing search URLs
            html_parser: HTML parser for extracting products from HTML
        """
        super().__init__(http_client, url_builder, html_parser)