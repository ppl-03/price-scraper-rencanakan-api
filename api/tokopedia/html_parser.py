import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup

from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import TokopediaPriceCleaner

logger = logging.getLogger(__name__)


class TokopediaHtmlParser(IHtmlParser):
    """
    Optimized HTML parser for Tokopedia product pages.
    
    Optimizations:
    - Pre-compiled regex patterns for slug generation
    - Efficient CSS selectors with minimal traversals
    - Early validation to skip invalid products
    - lxml parser as primary (fastest BeautifulSoup backend)
    """
    
    # Pre-compile regex patterns for better performance (class-level)
    _SLUG_PATTERN = re.compile(r'[^a-z0-9\-]')
    _PRICE_PREFIX_PATTERN = re.compile(r'^(Rp|IDR|rp|idr)')
    
    def __init__(self, price_cleaner: TokopediaPriceCleaner = None):
        self.price_cleaner = price_cleaner or TokopediaPriceCleaner()
        # Cache selectors as instance variables to avoid repeated string operations
        self._product_selector = 'a[data-testid="lnkProductContainer"]'
        self._name_selector = 'span.css-20kt3o'
        self._link_selector = 'a[data-testid="lnkProductContainer"]'
        self._price_selector = 'span.css-o5uqv'
        self._image_selector = 'img'
        self._description_selector = 'div[data-testid="divProductWrapper"]'
        # Cache base URL for URL construction
        self._base_url = "https://www.tokopedia.com"
    
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
        """
        Extract product from item with optimized validation.
        Returns None early if product is invalid to avoid unnecessary processing.
        """
        # Extract name first (cheapest operation)
        name = self._extract_product_name(item)
        if not name:
            return None
        
        # Early validation: check if name looks like a price (optimization)
        if self._PRICE_PREFIX_PATTERN.match(name):
            url = f"{self._base_url}/product/unknown"
        else:
            slug = self._generate_slug(name)
            url = f"{self._base_url}/product/{slug}"
        
        # Extract and validate price (more expensive operation, do after name check)
        price = self._extract_product_price(item)
        if not self.price_cleaner.validate_price(price):
            return None
        
        return Product(name=name, price=price, url=url)
    
    def _extract_product_name(self, item) -> Optional[str]:
        name = self._try_primary_name_selector(item)
        if name:
            return name
        
        return self._try_fallback_name_selectors(item)
    
    def _try_primary_name_selector(self, item) -> Optional[str]:
        return self._extract_text_from_selector(item, self._name_selector)
    
    def _try_fallback_name_selectors(self, item) -> Optional[str]:
        name = self._extract_text_from_selector(item, 'div[data-testid="divProductWrapper"] span')
        if name:
            return name
        
        return self._try_image_alt_selector(item)
    
    def _extract_text_from_selector(self, item, selector: str) -> Optional[str]:
        """Extract and return text from an element matching the selector."""
        element = item.select_one(selector)
        if element:
            text = element.get_text(strip=True)
            if text:
                return text
        return None
    
    def _try_text_selector(self, item, selector: str) -> Optional[str]:
        """Deprecated: Use _extract_text_from_selector instead."""
        return self._extract_text_from_selector(item, selector)
    
    def _try_image_alt_selector(self, item) -> Optional[str]:
        img = item.find('img')
        if img and img.get('alt'):
            return img.get('alt').strip()
        return None
    
    def _extract_product_url(self, item) -> str:
        """
        Extract product URL with optimized string operations.
        Uses cached base_url to avoid repeated string concatenation.
        """
        link = item.select_one(self._link_selector)
        if link and link.get('href'):
            href = link.get('href', '')
            # Efficient URL construction based on href format
            if href.startswith('/'):
                return f"{self._base_url}{href}"
            elif href.startswith('http'):
                return href
            else:
                return f"{self._base_url}/{href}"
        
        # Fallback: generate URL from product name
        name_element = item.select_one(self._name_selector)
        if name_element:
            name = name_element.get_text(strip=True)
            if name:
                slug = self._generate_slug(name)
                return f"{self._base_url}/product/{slug}"
        
        return f"{self._base_url}/product/unknown"
    
    def _generate_slug(self, name: str) -> str:
        """
        Generate URL-safe slug from product name.
        Uses pre-compiled regex pattern for better performance.
        """
        # Efficient slug generation with minimal operations
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        slug = self._SLUG_PATTERN.sub('', slug)
        return slug
    
    def _extract_product_price(self, item) -> int:
        # Try primary price selector
        price_element = item.select_one(self._price_selector)
        if price_element:
            price = self._try_clean_price(price_element.get_text(strip=True))
            if price:
                return price
        
        # Fallback: search for any text containing "Rp" or "IDR"
        price_texts = item.find_all(string=lambda text: text and ('Rp' in text or 'IDR' in text))
        for price_text in price_texts:
            price = self._try_clean_price(price_text.strip())
            if price:
                return price
        
        return 0
    
    def _try_clean_price(self, price_text: str) -> Optional[int]:
        """Try to clean and validate a price text, return None if invalid."""
        try:
            price = self.price_cleaner.clean_price(price_text)
            if self.price_cleaner.validate_price(price):
                return price
        except (TypeError, ValueError):
            pass
        return None