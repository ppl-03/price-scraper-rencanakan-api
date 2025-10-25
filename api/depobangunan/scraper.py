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
    
    def scrape_products(self, keyword: str, sort_by_price: bool = False, page: int = 0) -> ScrapingResult:
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
    
    def _enhance_product_with_unit_from_detail_page(self, product: Product) -> Product:
        if not product.url:
            return product
        
        try:
            # Fetch the product detail page with increased timeout
            detail_html = self.http_client.get(product.url, timeout=60)
            
            # Extract unit from the detail page
            unit = self.unit_parser.parse_unit_from_detail_page(detail_html)
            
            if unit:
                # Return enhanced product with unit
                return Product(
                    name=product.name,
                    price=product.price,
                    url=product.url,
                    unit=unit
                )
            
            return product
            
        except Exception as e:
            logger.warning(f"Failed to enhance product with unit from detail page {product.url}: {str(e)}")
            return product