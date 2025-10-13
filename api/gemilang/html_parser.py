import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup

from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import GemilangPriceCleaner
from .unit_parser import GemilangUnitParser

logger = logging.getLogger(__name__)

class RegexCache:
    SLUG_PATTERN = re.compile(r'[^a-zA-Z0-9\s]')
    WHITESPACE_PATTERN = re.compile(r'\s+')


class GemilangHtmlParser(IHtmlParser):
    
    def __init__(self, price_cleaner: GemilangPriceCleaner = None, unit_parser: GemilangUnitParser = None):
        self.price_cleaner = price_cleaner or GemilangPriceCleaner()
        self.unit_parser = unit_parser or GemilangUnitParser()
    
    def parse_products(self, html_content: str) -> List[Product]:
        try:
            if not html_content:
                return []
            
            parser = 'lxml' if self._has_lxml() else 'html.parser'
            soup = BeautifulSoup(html_content, parser)
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
        
        item_html = str(item)
        unit = self.unit_parser.parse_unit(item_html)
        
        return Product(name=name, price=price, url=url, unit=unit)
    
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
        base_url = "https://gemilang-store.com"
        
        name_link = item.find('a')
        if name_link and name_link.get('href') and name_link.get('href') != '#xs-review-button':
            href = name_link.get('href', '')
            if href.startswith('/'):
                return base_url + href
            elif href.startswith('http'):
                return href
            else:
                return base_url + '/' + href
        
        name_element = item.select_one('p.product-name')
        if name_element:
            name = name_element.get_text(strip=True)
            if name:
                slug = self._generate_slug(name)
                return f"{base_url}/pusat/{slug}"
        
        return f"{base_url}/pusat/product"
    
    def _generate_slug(self, name: str) -> str:
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        return slug
    
    def _has_lxml(self) -> bool:
        try:
            import lxml
            return True
        except ImportError:
            return False
    
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
    
    def parse_product_details(self, html_content: str, product_url: str = None) -> Optional[Product]:
        try:
            if not html_content:
                return None
            
            parser = 'lxml' if self._has_lxml() else 'html.parser'
            soup = BeautifulSoup(html_content, parser)
            
            name = self._extract_product_name_from_page(soup)
            if not name:
                return None
            
            price = self._extract_product_price_from_page(soup)
            if not self.price_cleaner.is_valid_price(price):
                return None
            
            unit = self.unit_parser.parse_unit(html_content)
            
            return Product(name=name, price=price, url=product_url or "", unit=unit)
            
        except Exception as e:
            logger.warning(f"Failed to parse product details: {str(e)}")
            return None
    
    def _extract_product_name_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        name_selectors = [
            'h1',
            '.product-title',
            '.product-name',
            'title'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                if name and len(name) > 3:
                    return name
        
        return None
    
    def _extract_product_price_from_page(self, soup: BeautifulSoup) -> int:
        price_selectors = [
            '.price',
            '.product-price', 
            '.harga',
            '#price',
            '[class*="price"]',
            '[id*="price"]',
            '.price-current'
        ]
        
        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                try:
                    price = self.price_cleaner.clean_price(text)
                    if self.price_cleaner.is_valid_price(price):
                        return price
                except (TypeError, ValueError):
                    continue
        
        price_patterns = [
            r'Rp[\s]*([0-9.,]+)',
            r'IDR[\s]*([0-9.,]+)',
            r'([0-9.,]+)[\s]*rupiah',
        ]
        
        page_text = soup.get_text()
        for pattern in price_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                for match in matches:
                    price_str = match.replace(',', '').replace('.', '')
                    try:
                        price = int(price_str)
                        if 100 <= price <= 50000000:  # Reasonable price range
                            cleaned_price = self.price_cleaner.clean_price(f"Rp {price}")
                            if self.price_cleaner.is_valid_price(cleaned_price):
                                return cleaned_price
                    except (ValueError, TypeError):
                        continue
        
        return 0