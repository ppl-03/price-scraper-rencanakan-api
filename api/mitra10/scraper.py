from typing import List
import logging
from api.core import BasePriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, Product, ScrapingResult
from api.playwright_client import BatchPlaywrightClient

logger = logging.getLogger(__name__)


class Mitra10PriceScraper(BasePriceScraper):
    
    def __init__(self, http_client: IHttpClient, url_builder: IUrlBuilder, html_parser: IHtmlParser):
        super().__init__(http_client, url_builder, html_parser)
    
    def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> ScrapingResult:
        """Override to properly use BatchPlaywrightClient as context manager"""
        try:
            url = self.url_builder.build_search_url(keyword, sort_by_price, page)
            
            # Use BatchPlaywrightClient as a context manager with increased timeout
            with BatchPlaywrightClient(headless=True) as batch_client:
                # Increase timeout to 60 seconds for heavy JavaScript sites
                html_content = batch_client.get(url, timeout=60)
                products = self.html_parser.parse_products(html_content)
            
            logger.info(f"Successfully scraped {len(products)} products for keyword '{keyword}'")
            return ScrapingResult(
                products=products,
                success=True,
                url=url
            )
            
        except Exception as e:
            error_msg = f"Scraping failed for keyword '{keyword}': {str(e)}"
            logger.error(error_msg)
            return ScrapingResult(
                products=[],
                success=False,
                error_message=error_msg,
                url=url if 'url' in locals() else None
            )
    
    def scrape_batch(self, keywords: List[str]) -> List[Product]:
        all_products = []
        
        with BatchPlaywrightClient() as batch_client:
            for keyword in keywords:
                try:
                    url = self.url_builder.build_search_url(keyword)
                    # Increase timeout to 60 seconds for heavy JavaScript sites
                    html_content = batch_client.get(url, timeout=60)
                    products = self.html_parser.parse_products(html_content)
                    all_products.extend(products)
                    
                except Exception as e:
                    print(f"Error scraping {keyword}: {e}")
                    continue
        
        return all_products