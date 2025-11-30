from typing import List
from api.core import BasePriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, Product, ScrapingResult
from api.playwright_client import BatchPlaywrightClient
from .logging_utils import get_mitra10_logger

logger = get_mitra10_logger("scraper")


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
            
            logger.info(
                "Successfully scraped %s products for keyword '%s'",
                len(products), keyword,
                extra={"operation": "scrape_products"}
            )
            return ScrapingResult(
                products=products,
                success=True,
                url=url
            )
            
        except Exception as e:
            error_msg = f"Scraping failed for keyword '{keyword}': {str(e)}"
            logger.error(
                "Scraping failed for keyword '%s': %s",
                keyword, str(e),
                extra={"operation": "scrape_products"}
            )
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
    
    def scrape_by_popularity(self, keyword: str, top_n: int = 5, page: int = 0) -> ScrapingResult:
        """Scrape products sorted by popularity and return top N best sellers (default: 5)."""
        try:
            # Build URL with popularity sorting (sort_by_price=False)
            url = self.url_builder.build_search_url(keyword, sort_by_price=False, page=page)
            
            with BatchPlaywrightClient(headless=True) as batch_client:
                html_content = batch_client.get(url, timeout=60)
                products = self.html_parser.parse_products(html_content)
            
            # Filter products that have sold_count and sort by sold_count descending
            products_with_sales = [p for p in products if p.sold_count is not None and p.sold_count > 0]
            products_with_sales.sort(key=lambda x: x.sold_count, reverse=True)
            
            # Get top N best sellers
            top_products = products_with_sales[:top_n]
            
            logger.info(
                "Successfully scraped %s products, returning top %s best sellers for keyword '%s'",
                len(products), len(top_products), keyword,
                extra={"operation": "scrape_by_popularity"}
            )
            return ScrapingResult(
                products=top_products,
                success=True,
                url=url
            )
            
        except Exception as e:
            error_msg = f"Scraping by popularity failed for keyword '{keyword}': {str(e)}"
            logger.error(
                "Scraping by popularity failed for keyword '%s': %s",
                keyword, str(e),
                extra={"operation": "scrape_by_popularity"}
            )
            return ScrapingResult(
                products=[],
                success=False,
                error_message=error_msg,
                url=url if 'url' in locals() else None
            )