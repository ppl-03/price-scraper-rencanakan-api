from api.core import BasePriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, ScrapingResult
import logging

logger = logging.getLogger(__name__)


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
    
    def scrape_popularity_products(self, keyword: str, page: int = 0, top_n: int = 5) -> ScrapingResult:
        """
        Scrape products sorted by popularity (relevance) and return top N products.
        
        Args:
            keyword: Search keyword
            page: Page number to scrape (default: 0)
            top_n: Number of top products to return (default: 5)
        
        Returns:
            ScrapingResult with top N products sorted by relevance
        """
        try:
            # Build URL for popularity sorting (sort_by_price=False means relevance)
            url = self.url_builder.build_search_url(keyword, sort_by_price=False, page=page)
            logger.info(f"Scraping popularity products from: {url}")
            
            # Fetch HTML content
            html_content = self.http_client.get(url, timeout=30)
            
            # Parse products
            products = self.html_parser.parse_products(html_content)
            
            if not products:
                return ScrapingResult(
                    products=[],
                    success=True,
                    error_message="No products found",
                    url=url
                )
            
            # Get top N products (they are already sorted by relevance from the website)
            top_products = products[:top_n]
            logger.info(f"Found {len(products)} products, returning top {len(top_products)}")
            
            return ScrapingResult(
                products=top_products,
                success=True,
                error_message=None,
                url=url
            )
            
        except Exception as e:
            error_msg = f"Failed to scrape popularity products: {str(e)}"
            logger.error(error_msg)
            return ScrapingResult(
                products=[],
                success=False,
                error_message=error_msg,
                url=None
            )