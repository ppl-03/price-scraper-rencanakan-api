import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup

from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import JuraganMaterialPriceCleaner

logger = logging.getLogger(__name__)


class JuraganMaterialHtmlParser(IHtmlParser):
    """HTML parser for Juragan Material product pages."""
    
    def __init__(self, price_cleaner: JuraganMaterialPriceCleaner = None):
        self.price_cleaner = price_cleaner or JuraganMaterialPriceCleaner()
    
    def parse_products(self, html_content: str) -> List[Product]:
        """
        Parse HTML content and extract product information.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List[Product]: List of extracted products
            
        Raises:
            HtmlParserError: If HTML parsing fails
        """
        try:
            if not html_content:
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            products = []
            
            product_items = soup.find_all('div', class_='product-card')
            logger.info(f"Found {len(product_items)} product items in HTML")
            
            for item in product_items:
                try:
                    product = self._extract_product_from_item(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"Failed to extract product from item: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(products)} products")
            return products
            
        except Exception as e:
            raise HtmlParserError(f"Failed to parse HTML: {str(e)}")
    
    def _extract_product_from_item(self, item) -> Optional[Product]:
        """Extract product information from a single product item."""
        name = self._extract_product_name(item)
        if not name:
            return None
        
        url = self._extract_product_url(item)
        
        price = self._extract_product_price(item)
        if not self.price_cleaner.is_valid_price(price):
            return None
        
        return Product(name=name, price=price, url=url)
    
    def _extract_product_name(self, item) -> Optional[str]:
        """Extract product name from item."""
        # Try to get name from link first
        name_link = item.find('a')
        if name_link:
            name_element = name_link.find('p', class_='product-name')
            if name_element:
                name = name_element.get_text(strip=True)
                if name:
                    return name
        
        # Fallback to direct p.product-name
        name_element = item.find('p', class_='product-name')
        if name_element:
            name = name_element.get_text(strip=True)
            if name:
                return name
        
        return None
    
    def _extract_product_url(self, item) -> str:
        """Extract product URL from item."""
        name_link = item.find('a')
        if name_link and name_link.get('href'):
            return name_link.get('href', '')
        
        # Generate URL from product name if no link available
        name_element = item.find('p', class_='product-name')
        if name_element:
            name = name_element.get_text(strip=True)
            if name:
                slug = self._generate_slug(name)
                return f"/products/{slug}"
        
        return "/products/product"
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL slug from product name."""
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        return slug
    
    def _extract_product_price(self, item) -> int:
        """Extract product price from item."""
        # Follow the path: div.product-card-price -> div.price
        price_wrapper = item.find('div', class_='product-card-price')
        if price_wrapper:
            price_element = price_wrapper.find('div', class_='price')
            if price_element:
                price_text = price_element.get_text(strip=True)
                try:
                    return self.price_cleaner.clean_price(price_text)
                except (TypeError, ValueError):
                    pass
        
        # Fallback: look for any text containing price patterns
        price_texts = item.find_all(string=lambda text: text and 'Rp' in text)
        for price_text in price_texts:
            try:
                price = self.price_cleaner.clean_price(price_text.strip())
                if self.price_cleaner.is_valid_price(price):
                    return price
            except (TypeError, ValueError):
                continue
        
        return 0