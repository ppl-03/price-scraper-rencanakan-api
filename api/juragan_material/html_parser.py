import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup


from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import JuraganMaterialPriceCleaner

logger = logging.getLogger(__name__)
import requests

class RegexCache:
    """Cache for compiled regex patterns to avoid recompilation."""
    SLUG_PATTERN = re.compile(r'[^a-zA-Z0-9\-]')
    WHITESPACE_PATTERN = re.compile(r'\s+')


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
            
            parser = 'lxml' if self._has_lxml() else 'html.parser'
            soup = BeautifulSoup(html_content, parser)
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
        
        if url:
            unit = self._extract_product_unit(url)
            location = self._extract_product_location_xpath(url)
        if not self.price_cleaner.is_valid_price(price):
            return None
        
        return Product(name=name, price=price, url=url, unit=unit, location=location)
    
    def _extract_product_location(self, item) -> Optional[str]:
        """Extract product location from item."""
        location_element = item.find('div', class_='location')
        if location_element:
            location = location_element.get_text(strip=True)
            if location:
                return location
        return None
    
    def _extract_product_name(self, item) -> Optional[str]:
        """Extract product name from item."""
        # Try new Juragan Material structure first (sj-text-display4)
        name_element = item.find('p', class_='sj-text-display4')
        if name_element:
            name = name_element.get_text(strip=True)
            if name:
                return name
        
        # Fallback to old structure for backward compatibility
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
        # Check if the product card is wrapped in an <a> tag (new structure)
        if item.parent and item.parent.name == 'a':
            href = item.parent.get('href')
            if href:
                return href
        
        # Fallback to old structure - look for <a> inside the item
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
        """Generate URL slug from product name using cached regex patterns."""
        slug = name.lower()
        slug = RegexCache.WHITESPACE_PATTERN.sub('-', slug)
        slug = RegexCache.SLUG_PATTERN.sub('', slug)
        return slug
    
    def _extract_product_price(self, item) -> int:
        """Extract product price from item."""
        # Try new Juragan Material structure first (sj-text-h6 text-text-main)
        price_element = item.find('p', class_='sj-text-h6 text-text-main')
        if price_element:
            price_text = price_element.get_text(strip=True)
            try:
                return self.price_cleaner.clean_price(price_text)
            except (TypeError, ValueError):
                pass
        
        # Fallback to old structure: div.product-card-price -> div.price
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
    
    def _extract_product_unit(self, url: str) -> str:
        """Fetch the product detail page and extract the unit."""
        try:
            # kalau url relatif, tambahkan domain utama
            if url.startswith('/'):
                url = f"https://juraganmaterial.id{url}"
            
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch product detail page: {url}")
                return ''
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # ambil div sesuai path yang kamu sebutkan
            # pastikan selector ini cocok dengan struktur HTML aslinya
            unit_div = soup.select_one('html > body > div:nth-of-type(1) > div > main > div > div:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(2) > div:nth-of-type(2) > div > div:nth-of-type(1) > p:nth-of-type(2)')
            if unit_div:
                return unit_div.get_text(strip=True)
            
            return ''
        
        except Exception as e:
            logger.error(f"Error fetching unit for {url}: {e}")
            return ''
    
    def _extract_product_location_xpath(self, url: str) -> str:
        """Fetch the product detail page and extract the location using full XPath."""
        try:
            if url.startswith('/'):
                url = f"https://juraganmaterial.id{url}"
            
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch product detail page: {url}")
                return ''
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            
            # pastikan selector ini cocok dengan struktur HTML aslinya
            location_div= soup.select_one('#footer-address-link > span:nth-child(2)')
            if location_div:
                return location_div.get_text(strip=True)
            
            return ''
        
        except Exception as e:
            logger.error(f"Error fetching location for {url}: {e}")
            return ''
    
    def _has_lxml(self) -> bool:
        """Check if lxml parser is available."""
        try:
            import lxml
            return True
        except ImportError:
            return False