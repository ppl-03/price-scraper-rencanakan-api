import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup

from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import DepoPriceCleaner
from .unit_parser import DepoBangunanUnitParser

logger = logging.getLogger(__name__)


class DepoHtmlParser(IHtmlParser):
    
    def __init__(self, price_cleaner: DepoPriceCleaner = None, unit_parser: DepoBangunanUnitParser = None):
        self.price_cleaner = price_cleaner or DepoPriceCleaner()
        self.unit_parser = unit_parser or DepoBangunanUnitParser()
    
    def parse_products(self, html_content: str) -> List[Product]:
        try:
            if not html_content:
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            products = []
            
            # Find all product items using the correct selector
            product_items = soup.find_all('li', class_='item product product-item')
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
        name = self._extract_product_name(item)
        if not name:
            return None
        
        url = self._extract_product_url(item)
        
        price = self._extract_product_price(item)
        if not self.price_cleaner.is_valid_price(price):
            return None
        
        # Extract unit from product name
        unit = self.unit_parser.parse_unit_from_product_name(name)
        
        return Product(name=name, price=price, url=url, unit=unit)
    
    def _extract_product_name(self, item) -> Optional[str]:
        # Try to find the product name in the product-item-name element
        name_element = item.find('strong', class_='product name product-item-name')
        if name_element:
            # Look for anchor tag within the strong element
            link = name_element.find('a')
            if link:
                name = link.get_text(strip=True)
                if name:
                    return name
            
            # If no anchor, try to get text directly from strong element
            name = name_element.get_text(strip=True)
            if name:
                return name
        
        return None
    
    def _extract_product_url(self, item) -> str:
        # Find the product name link
        name_element = item.find('strong', class_='product name product-item-name')
        if name_element:
            link = name_element.find('a')
            if link and link.get('href'):
                return link.get('href')
        
        return ""
    
    def _extract_product_price(self, item) -> int:
        # Try different price extraction methods in order of preference
        price = self._extract_price_from_data_attribute(item)
        if price and price > 0:
            return price
        
        price = self._extract_price_from_special_price(item)
        if price and price > 0:
            return price
        
        price = self._extract_price_from_regular_price(item)
        if price and price > 0:
            return price
        
        return self._extract_price_from_text_search(item)
    
    def _extract_price_from_data_attribute(self, item) -> int:
        price_wrapper = item.find('span', {'data-price-type': 'finalPrice'})
        if price_wrapper and price_wrapper.get('data-price-amount'):
            try:
                return int(price_wrapper.get('data-price-amount'))
            except (ValueError, TypeError):
                pass
        return 0
    
    def _extract_price_from_special_price(self, item) -> int:
        special_price = item.find('span', class_='special-price')
        if not special_price:
            return 0
        
        price_wrapper = special_price.find('span', {'data-price-type': 'finalPrice'})
        if not price_wrapper:
            return 0
        
        # Try data attribute first
        if price_wrapper.get('data-price-amount'):
            try:
                return int(price_wrapper.get('data-price-amount'))
            except (ValueError, TypeError):
                pass
        
        # Try text content
        price_span = price_wrapper.find('span', class_='price')
        if price_span:
            return self._clean_price_text(price_span.get_text(strip=True))
        
        return 0
    
    def _extract_price_from_regular_price(self, item) -> int:
        price_box = item.find('div', class_='price-box price-final_price')
        if not price_box:
            return 0
        
        price_wrapper = price_box.find('span', {'data-price-type': 'finalPrice'})
        if not price_wrapper:
            return 0
        
        # Try data attribute first
        if price_wrapper.get('data-price-amount'):
            try:
                return int(price_wrapper.get('data-price-amount'))
            except (ValueError, TypeError):
                pass
        
        # Try text content
        price_span = price_wrapper.find('span', class_='price')
        if price_span:
            return self._clean_price_text(price_span.get_text(strip=True))
        
        return 0
    
    def _extract_price_from_text_search(self, item) -> int:
        price_texts = item.find_all(string=lambda text: text and 'Rp' in text)
        for price_text in price_texts:
            price = self._clean_price_text(price_text.strip())
            if self.price_cleaner.is_valid_price(price):
                return price
        return 0
    
    def _clean_price_text(self, price_text: str) -> int:
        try:
            return self.price_cleaner.clean_price(price_text)
        except (TypeError, ValueError):
            return 0