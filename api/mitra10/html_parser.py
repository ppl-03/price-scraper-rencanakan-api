import logging
import re
from typing import List, Optional, Callable, Any
from bs4 import BeautifulSoup

from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import Mitra10PriceCleaner
from .unit_parser import Mitra10UnitParser

logger = logging.getLogger(__name__)


class HtmlElementExtractor:
    """Helper class for extracting data from HTML elements using selectors"""
    
    @staticmethod
    def extract_text_from_selectors(soup_or_item, selectors: List[str], min_length: int = 1) -> Optional[str]:
        """Extract text from first matching selector"""
        for selector in selectors:
            element = soup_or_item.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) >= min_length:
                    return text
        return None
    
    @staticmethod
    def extract_attribute_from_selector(soup_or_item, selector: str, attribute: str) -> Optional[str]:
        """Extract attribute value from selector"""
        element = soup_or_item.select_one(selector)
        if element and element.get(attribute):
            return element.get(attribute).strip()
        return None


class PriceExtractionHelper:
    """Helper class for price extraction with different strategies"""
    
    def __init__(self, price_cleaner: Mitra10PriceCleaner):
        self.price_cleaner = price_cleaner
        self.price_selectors = [
            'span.price__final',
            '.price',
            '.product-price', 
            '.harga',
            '#price',
            '[class*="price"]',
            '[id*="price"]',
            '.MuiTypography-root[class*="price"]'
        ]
        self.price_patterns = [
            r'Rp[\s]*([0-9.,]+)',
            r'IDR[\s]*([0-9.,]+)',
            r'([0-9.,]+)[\s]*rupiah',
        ]
    
    def extract_price_from_element(self, soup_or_item) -> int:
        """Extract price using multiple strategies"""
        # Try CSS selectors first
        price = self._extract_from_selectors(soup_or_item)
        if price > 0:
            return price
        
        # Try text patterns with string search
        price = self._extract_from_text_search(soup_or_item)
        if price > 0:
            return price
        
        # Try regex patterns
        return self._extract_from_regex_patterns(soup_or_item)
    
    def _extract_from_selectors(self, soup_or_item) -> int:
        """Extract price using CSS selectors"""
        for selector in self.price_selectors:
            price = self._try_selector_extraction(soup_or_item, selector)
            if price > 0:
                return price
        return 0
    
    def _try_selector_extraction(self, soup_or_item, selector: str) -> int:
        """Try extracting and validating price from a specific selector"""
        elements = soup_or_item.select(selector)
        for element in elements:
            price = self._extract_and_validate_price_text(element.get_text(strip=True))
            if price > 0:
                return price
        return 0
    
    def _extract_from_text_search(self, soup_or_item) -> int:
        """Extract price using text search for currency indicators"""
        price_texts = soup_or_item.find_all(string=lambda text: text and ('Rp' in text or 'IDR' in text))
        for price_text in price_texts:
            price = self._extract_and_validate_price_text(price_text.strip())
            if price > 0:
                return price
        return 0
    
    def _extract_from_regex_patterns(self, soup_or_item) -> int:
        """Extract price using regex patterns"""
        page_text = soup_or_item.get_text() if hasattr(soup_or_item, 'get_text') else str(soup_or_item)
        for pattern in self.price_patterns:
            price = self._try_pattern_extraction(pattern, page_text)
            if price > 0:
                return price
        return 0
    
    def _try_pattern_extraction(self, pattern: str, page_text: str) -> int:
        """Try to extract price from regex pattern"""
        matches = re.findall(pattern, page_text, re.IGNORECASE)
        for match in matches:
            price = self._parse_and_validate_price_match(match)
            if price > 0:
                return price
        return 0
    
    def _extract_and_validate_price_text(self, price_text: str) -> int:
        """Extract and validate price from text"""
        try:
            price = self.price_cleaner.clean_price(price_text)
            if self.price_cleaner.is_valid_price(price):
                return price
        except (TypeError, ValueError):
            pass
        return 0
    
    def _parse_and_validate_price_match(self, match: str) -> int:
        """Parse and validate a price match from regex"""
        price_str = match.replace(',', '').replace('.', '')
        try:
            price = int(price_str)
            if 100 <= price <= 50000000:  # Reasonable price range
                cleaned_price = self.price_cleaner.clean_price(f"Rp {price}")
                if self.price_cleaner.is_valid_price(cleaned_price):
                    return cleaned_price
        except (ValueError, TypeError):
            pass
        return 0


class SafeExtractionMixin:
    """Mixin for safe extraction operations with consistent error handling"""
    
    def safe_extract(self, operation: Callable, operation_name: str, *args, **kwargs) -> Any:
        """Safely execute extraction operation with logging"""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to {operation_name}: {str(e)}")
            return None
    
    def safe_extract_with_default(self, operation: Callable, default_value: Any, operation_name: str, *args, **kwargs) -> Any:
        """Safely execute extraction operation with default value"""
        try:
            result = operation(*args, **kwargs)
            return result if result is not None else default_value
        except Exception as e:
            logger.warning(f"Failed to {operation_name}: {str(e)}")
            return default_value


class Mitra10HtmlParser(IHtmlParser, SafeExtractionMixin):
    
    def __init__(self, price_cleaner: Mitra10PriceCleaner = None, unit_parser: Mitra10UnitParser = None):
        self.price_cleaner = price_cleaner or Mitra10PriceCleaner()
        self.unit_parser = unit_parser or Mitra10UnitParser()
        self.price_helper = PriceExtractionHelper(self.price_cleaner)
        self._product_selector = "div.MuiGrid-item"
        self._name_selector = 'a.gtm_mitra10_cta_product p'  
        self._link_selector = "a.gtm_mitra10_cta_product"
        self._image_selector = "img"
        self._description_selector = "p.MuiTypography-root"
        
        # Name extraction selectors
        self._name_selectors = [
            self._name_selector,
            'p.product-name'
        ]
        
        # Product page name selectors
        self._page_name_selectors = [
            'h1',
            '.product-title',
            '.product-name',
            'title',
            '.MuiTypography-h1',
            '.MuiTypography-h2'
        ]
    
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
        return self.safe_extract(self._extract_product_from_item, "extract product from item", item)
    
    def _extract_product_from_item(self, item) -> Optional[Product]:
        name = self._extract_product_name(item)
        if not name:
            return None
        
        url = self._extract_product_url(item)
        price = self.price_helper.extract_price_from_element(item)
        
        if not self.price_cleaner.is_valid_price(price):
            return None
        
        # Extract unit from the item HTML
        item_html = str(item)
        unit = self.unit_parser.parse_unit(item_html)
        
        # If no unit found in item HTML, try parsing the product name directly
        if not unit and name:
            unit = self.unit_parser.parse_unit(f"<div><h2>{name}</h2></div>")
        
        return Product(name=name, price=price, url=url, unit=unit)
    
    def _extract_product_name(self, item) -> Optional[str]:
        # Try primary selectors
        name = HtmlElementExtractor.extract_text_from_selectors(item, self._name_selectors)
        if name:
            return name
        
        # Try image alt as fallback
        return self._try_image_alt_selector(item)
    
    def _try_image_alt_selector(self, item) -> Optional[str]:
        img = item.find('img')
        if img and img.get('alt'):
            return img.get('alt').strip()
        return None
    
    def _extract_product_url(self, item) -> str:
        # Try primary link selector
        url = HtmlElementExtractor.extract_attribute_from_selector(item, self._link_selector, 'href')
        if url:
            return url
        
        # Generate URL from product name
        name = HtmlElementExtractor.extract_text_from_selectors(item, self._name_selectors)
        if name:
            slug = self._generate_slug(name)
            return f"/product/{slug}"
        
        return "/product/unknown"
    
    def _generate_slug(self, name: str) -> str:
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        return slug
    
    def parse_product_details(self, html_content: str, product_url: str = None) -> Optional[Product]:
        """Parse detailed product information from a product page"""
        return self.safe_extract(self._parse_product_details_safely, "parse product details", html_content, product_url)
    
    def _parse_product_details_safely(self, html_content: str, product_url: str = None) -> Optional[Product]:
        if not html_content:
            return None
        
        parser = 'lxml' if self._has_lxml() else 'html.parser'
        soup = BeautifulSoup(html_content, parser)
        
        name = self._extract_product_name_from_page(soup)
        if not name:
            return None
        
        price = self.price_helper.extract_price_from_element(soup)
        if not self.price_cleaner.is_valid_price(price):
            return None
        
        # Extract unit from the full page HTML
        unit = self.unit_parser.parse_unit(html_content)
        
        return Product(name=name, price=price, url=product_url or "", unit=unit)
    
    def _extract_product_name_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product name from product detail page"""
        return HtmlElementExtractor.extract_text_from_selectors(soup, self._page_name_selectors, min_length=3)
    
    def _has_lxml(self) -> bool:
        """Check if lxml parser is available"""
        try:
            import lxml
            return True
        except ImportError:
            return False