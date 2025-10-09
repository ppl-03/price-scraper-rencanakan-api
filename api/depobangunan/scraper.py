from api.core import BasePriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser


class DepoPriceScraper(BasePriceScraper):
    
    def __init__(self, http_client: IHttpClient, url_builder: IUrlBuilder, html_parser: IHtmlParser):
        super().__init__(http_client, url_builder, html_parser)