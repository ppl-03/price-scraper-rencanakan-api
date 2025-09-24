import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup

from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import GemilangPriceCleaner

logger = logging.getLogger(__name__)


class GemilangHtmlParser(IHtmlParser):
    
    def __init__(self, price_cleaner: GemilangPriceCleaner = None):
        self.price_cleaner = price_cleaner or GemilangPriceCleaner()
    
    def parse_products(self, html_content: str) -> List[Product]:
        try:
            if not html_content:
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            products = []
            
            product_items = soup.find_all('div', class_='item-product')
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
        
        return Product(name=name, price=price, url=url)
    
    def _extract_product_name(self, item) -> Optional[str]:
        selectors = [
            'p.product-name',
            'a p.product-name',
            'img[alt]'
        ]
        
        for selector in selectors:
            if selector == 'img[alt]':
                img = item.find('img')
                if img and img.get('alt'):
                    return img.get('alt').strip()
            else:
                element = item.select_one(selector)
                if element:
                    name = element.get_text(strip=True)
                    if name:
                        return name
        
        return None
    
    def _extract_product_url(self, item) -> str:
        name_link = item.find('a')
        if name_link and name_link.get('href') and name_link.get('href') != '#xs-review-button':
            return name_link.get('href', '')
        
        name_element = item.select_one('p.product-name')
        if name_element:
            name = name_element.get_text(strip=True)
            if name:
                slug = self._generate_slug(name)
                return f"/pusat/{slug}"
        
        return "/pusat/product"
    
    def _generate_slug(self, name: str) -> str:
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        return slug
    
    def _extract_product_price(self, item) -> int:
        price_wrapper = item.find('div', class_=lambda x: x and 'price-wrapper' in x)
        if price_wrapper:
            price_element = price_wrapper.find('p', class_=lambda x: x and 'price' in x)
            if price_element:
                price_text = price_element.get_text(strip=True)
                try:
                    return self.price_cleaner.clean_price(price_text)
                except (TypeError, ValueError):
                    pass
        
        price_texts = item.find_all(string=lambda text: text and 'Rp' in text)
        for price_text in price_texts:
            try:
                price = self.price_cleaner.clean_price(price_text.strip())
                if self.price_cleaner.is_valid_price(price):
                    return price
            except (TypeError, ValueError):
                continue
        
        return 0