import logging
from typing import Optional
from api.core import BasePriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, Product, ScrapingResult
from .unit_parser import DepoBangunanUnitParser

logger = logging.getLogger(__name__)


class DepoPriceScraper(BasePriceScraper):
    
    def __init__(self, http_client: IHttpClient, url_builder: IUrlBuilder, html_parser: IHtmlParser):
        super().__init__(http_client, url_builder, html_parser)
        self.unit_parser = DepoBangunanUnitParser()
        # Cache for detail page units to avoid re-fetching same URLs
        self._unit_cache = {}
    
    def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> ScrapingResult:
        # Get initial results from the base scraper
        result = super().scrape_products(keyword, sort_by_price, page)
        
        if not result.success or not result.products:
            return result
        
        # Enhance products without units by checking their detail pages
        enhanced_products = []
        for product in result.products:
            if product.unit:
                # Product already has unit, keep as is
                enhanced_products.append(product)
            else:
                # Try to get unit from detail page
                enhanced_product = self._enhance_product_with_unit_from_detail_page(product)
                enhanced_products.append(enhanced_product)
        
        # Return enhanced result
        return ScrapingResult(
            products=enhanced_products,
            success=result.success,
            error_message=result.error_message,
            url=result.url
        )
    
    def scrape_popularity_products(self, keyword: str, page: int = 0, top_n: int = 5) -> ScrapingResult:
        """
        Scrape products sorted by popularity (top rated) and return top N by sold count.
        
        Args:
            keyword: Search keyword
            page: Page number to scrape (default: 0)
            top_n: Number of top products to return based on sold count (default: 5)
        
        Returns:
            ScrapingResult with products sorted by sold_count in descending order
        """
        try:
            # Build URL for popularity sorting
            url = self.url_builder.build_popularity_url(keyword, page)
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
            
            # Filter products that have sold_count data (including 0) and sort by it
            products_with_sales = [p for p in products if p.sold_count is not None]
            
            if products_with_sales:
                # Sort by sold_count descending (highest first)
                products_with_sales.sort(key=lambda x: x.sold_count, reverse=True)
                # Get top N products
                top_products = products_with_sales[:top_n]
                logger.info(f"Found {len(products_with_sales)} products with sales data, returning top {len(top_products)}")
            else:
                # No products have sold_count, just return first top_n products
                top_products = products[:top_n]
                logger.warning(f"No products with sold_count found, returning first {len(top_products)} products")
            
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
    
    def _enhance_product_with_unit_from_detail_page(self, product: Product) -> Product:
        if not product.url:
            return product
        
        # Check cache first
        if product.url in self._unit_cache:
            cached_unit = self._unit_cache[product.url]
            if cached_unit:
                return Product(
                    name=product.name,
                    price=product.price,
                    url=product.url,
                    unit=cached_unit,
                    sold_count=product.sold_count
                )
            return product
        
        try:
            # Fetch the product detail page with increased timeout
            detail_html = self.http_client.get(product.url, timeout=60)
            
            # Extract unit from the detail page
            unit = self.unit_parser.parse_unit_from_detail_page(detail_html)
            
            # Cache the result (even if None)
            self._unit_cache[product.url] = unit
            
            if unit:
                # Return enhanced product with unit
                return Product(
                    name=product.name,
                    price=product.price,
                    url=product.url,
                    unit=unit,
                    sold_count=product.sold_count
                )
            
            return product
            
        except Exception as e:
            logger.warning(f"Failed to enhance product with unit from detail page {product.url}: {str(e)}")
            # Cache the failure to avoid re-fetching
            self._unit_cache[product.url] = None
            return product