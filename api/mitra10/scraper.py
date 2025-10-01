from typing import List
from api.core import BasePriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, Product
from api.playwright_client import BatchPlaywrightClient


class Mitra10PriceScraper(BasePriceScraper):
    
    def __init__(self, http_client: IHttpClient, url_builder: IUrlBuilder, html_parser: IHtmlParser):
        super().__init__(http_client, url_builder, html_parser)
    
    def scrape_batch(self, keywords: List[str]) -> List[Product]:
        all_products = []
        
        with BatchPlaywrightClient() as batch_client:
            for keyword in keywords:
                try:
                    url = self.url_builder.build_search_url(keyword)                    
                    html_content = batch_client.get(url)                    
                    products = self.html_parser.parse_products(html_content)
                    all_products.extend(products)
                    
                except Exception as e:
                    print(f"Error scraping {keyword}: {e}")
                    continue
        
        return all_products