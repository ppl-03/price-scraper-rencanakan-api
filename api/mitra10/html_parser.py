import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup

from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import Mitra10PriceCleaner

logger = logging.getLogger(__name__)


class Mitra10HtmlParser(IHtmlParser):
    
    def __init__(self, price_cleaner: Mitra10PriceCleaner = None):
        self.price_cleaner = price_cleaner or Mitra10PriceCleaner()
        self._product_selector = "div.MuiGrid-item"
        self._name_selector = 'a.gtm_mitra10_cta_product p'  
        self._link_selector = "a.gtm_mitra10_cta_product"
        self._price_selector = "span.price__final"
        self._image_selector = "img"
        self._description_selector = "p.MuiTypography-root"
    
    def parse_products(self, html_content: str) -> List[Product]:
        if not html_content:
            return []
        
        try:
            return self._parse_with_lxml(html_content)
        except Exception as e:
            return self._parse_with_fallback(html_content, e)
    
    def _parse_with_lxml(self, html_content: str) -> List[Product]:
        soup = BeautifulSoup(html_content, 'lxml')
        return self._extract_all_products(soup)
    
    def _parse_with_fallback(self, html_content: str, original_error: Exception) -> List[Product]:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return self._extract_all_products(soup)
        except Exception:
            raise HtmlParserError(f"Failed to parse HTML: {str(original_error)}")
    
    def _extract_all_products(self, soup: BeautifulSoup) -> List[Product]:
        product_items = soup.select(self._product_selector)
        logger.info(f"Found {len(product_items)} product items in HTML")
        
        products = []
        for item in product_items:
            product = self._safely_extract_product(item)
            if product:
                products.append(product)
        
        logger.info(f"Successfully parsed {len(products)} products")
        return products
    
    def _safely_extract_product(self, item) -> Optional[Product]:
        try:
            return self._extract_product_from_item(item)
        except Exception as e:
            logger.warning(f"Failed to extract product from item: {str(e)}")
            return None
    
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
        name = self._try_primary_name_selector(item)
        if name:
            return name
        
        return self._try_fallback_name_selectors(item)
    
    def _try_primary_name_selector(self, item) -> Optional[str]:
        element = item.select_one(self._name_selector)
        if element:
            name = element.get_text(strip=True)
            if name:
                return name
        return None
    
    def _try_fallback_name_selectors(self, item) -> Optional[str]:
        name = self._try_text_selector(item, 'p.product-name')
        if name:
            return name
        
        return self._try_image_alt_selector(item)
    
    def _try_text_selector(self, item, selector: str) -> Optional[str]:
        element = item.select_one(selector)
        if element:
            name = element.get_text(strip=True)
            if name:
                return name
        return None
    
    def _try_image_alt_selector(self, item) -> Optional[str]:
        img = item.find('img')
        if img and img.get('alt'):
            return img.get('alt').strip()
        return None
    
    def _extract_product_url(self, item) -> str:
        link = item.select_one(self._link_selector)
        if link and link.get('href'):
            return link.get('href', '')
        
        name_element = item.select_one(self._name_selector)
        if name_element:
            name = name_element.get_text(strip=True)
            if name:
                slug = self._generate_slug(name)
                return f"/product/{slug}"
        
        return "/product/unknown"
    
    def _generate_slug(self, name: str) -> str:
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        return slug
    
    def _extract_product_price(self, item) -> int:
        price_element = item.select_one(self._price_selector)
        if price_element:
            price_text = price_element.get_text(strip=True)
            try:
                return self.price_cleaner.clean_price(price_text)
            except (TypeError, ValueError):
                pass
        
        price_texts = item.find_all(string=lambda text: text and ('Rp' in text or 'IDR' in text))
        for price_text in price_texts:
            try:
                price = self.price_cleaner.clean_price(price_text.strip())
                if self.price_cleaner.is_valid_price(price):
                    return price
            except (TypeError, ValueError):
                continue
        
        return 0