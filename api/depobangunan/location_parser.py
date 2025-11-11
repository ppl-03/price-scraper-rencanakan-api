import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from html import unescape

from api.interfaces import ILocationParser, Location, HtmlParserError

logger = logging.getLogger(__name__)


class TextCleaner:
    """Utility class for cleaning extracted text data"""
    
    @staticmethod
    def clean_store_name(text: str) -> str:
        """Clean and normalize store name text"""
        if not text:
            return ""
        cleaned = text.strip()
        # Ensure vendor prefix is present
        if not re.search(r'depo\s*bangunan', cleaned, re.IGNORECASE):
            cleaned = f"DEPO BANGUNAN - {cleaned}"
        return cleaned
    
    @staticmethod
    def clean_address(text: str) -> str:
        """Clean and normalize address text by removing extra whitespace and empty lines"""
        if not text:
            return ""
        
        # Split by newlines and clean each line
        lines = [line.strip() for line in text.split('\n')]
        # Filter out empty lines
        filtered_lines = [line for line in lines if line]
        return '\n'.join(filtered_lines)
    
    @staticmethod
    def is_valid_text(text: str) -> bool:
        """Check if text is valid (not None or empty)"""
        return text is not None and text.strip() != ""


class HtmlElementExtractor:
    """Class responsible for extracting specific elements from HTML"""
    
    def __init__(self, text_cleaner: TextCleaner, config: 'ParserConfiguration'):
        self._text_cleaner = text_cleaner
        # Read non-address patterns from parser configuration (OCP)
        self._non_address_patterns = getattr(config, 'non_address_patterns', None) or []
    
    def extract_store_name(self, header) -> Optional[str]:
        """Extract store name from an h2 header element"""
        try:
            text = header.get_text(strip=True)
            
            if not self._text_cleaner.is_valid_text(text):
                logger.debug("Store name text is empty or invalid")
                return None
            
            return self._text_cleaner.clean_store_name(text)
            
        except Exception as e:
            logger.warning(f"Failed to extract store name: {str(e)}")
            return None
    
    def extract_address(self, element) -> Optional[str]:
        """Extract address from the next element after the header"""
        try:
            # Look for the element containing the address
            # The address is typically in a <p> tag or div after the header
            address_text = ""
            
            # Try to find the address in the next sibling or nearby elements
            current = element.find_next_sibling()
            
            # Look for the first paragraph that looks like an address
            while current and not address_text:
                if current.name in ['p', 'div']:
                    # Join text across multiple lines and handle <br> tags
                    text = ' '.join(current.stripped_strings)
                    text = unescape(text)
                    
                    # Skip non-address content like "Jadwal Buka", "Telepon", etc.
                    if text and not self._is_non_address_content(text):
                        address_text = text
                        break
                current = current.find_next_sibling()
            
            # Clean up "Alamat:" prefix if present
            if address_text and address_text.startswith('Alamat:'):
                address_text = address_text.split(':', 1)[1].strip()
            
            if not self._text_cleaner.is_valid_text(address_text):
                logger.debug("Address text is empty or invalid")
                return None
            
            cleaned_address = self._text_cleaner.clean_address(address_text)
            return cleaned_address if self._text_cleaner.is_valid_text(cleaned_address) else None
            
        except Exception as e:
            logger.warning(f"Failed to extract address: {str(e)}")
            return None
    
    def _is_non_address_content(self, text: str) -> bool:
        """Check if text is non-address content like hours, phone, etc."""
        # Use configured non-address patterns; default list is provided by ParserConfiguration
        return any(pattern in text for pattern in self._non_address_patterns)


class ParserConfiguration:
    """Configuration for parser behavior following Open/Closed Principle"""
    
    def __init__(self):
        self.preferred_parser = 'lxml'
        self.fallback_parser = 'html.parser'
        # Patterns that clearly indicate a block is NOT an address
        # Can be extended/configured without modifying HtmlElementExtractor
        self.non_address_patterns = ['Jadwal Buka', 'Telepon', 'WhatsApp', 'Untuk petunjuk']
    
    def get_parser(self) -> str:
        """Get appropriate HTML parser"""
        return self.preferred_parser if self._has_lxml() else self.fallback_parser
    
    def _has_lxml(self) -> bool:
        """Check if lxml is available"""
        try:
            import lxml
            return True
        except ImportError:
            return False


class DepoBangunanLocationParser(ILocationParser):
    """Parser for extracting location data from Depo Bangunan website"""
    
    def __init__(self, 
                 text_cleaner: TextCleaner = None,
                 element_extractor: HtmlElementExtractor = None,
                 config: ParserConfiguration = None):
        self._text_cleaner = text_cleaner or TextCleaner()
        self._config = config or ParserConfiguration()
        self._element_extractor = element_extractor or HtmlElementExtractor(self._text_cleaner, self._config)
        self._config = config or ParserConfiguration()
    
    def parse_locations(self, html_content: Optional[str]) -> List[Location]:
        """Parse location data from HTML content"""
        if not self._is_valid_html_content(html_content):
            logger.debug("HTML content is empty or invalid")
            return []
        
        try:
            soup = self._create_soup(html_content)
            locations = self._extract_locations_from_soup(soup)
            
            logger.info(f"Successfully parsed {len(locations)} locations")
            return locations
            
        except Exception as e:
            logger.error(f"Failed to parse HTML: {str(e)}")
            return []
    
    def _is_valid_html_content(self, html_content: Optional[str]) -> bool:
        """Validate HTML content is not empty"""
        return html_content is not None and html_content.strip() != ""
    
    def _create_soup(self, html_content: str) -> BeautifulSoup:
        """Create BeautifulSoup object from HTML content"""
        parser = self._config.get_parser()
        return BeautifulSoup(html_content, parser)
    
    def _extract_locations_from_soup(self, soup: BeautifulSoup) -> List[Location]:
        """Extract all locations from the parsed HTML"""
        locations = []
        
        # Find all h2 headers that contain store names
        headers = soup.find_all('h2')
        
        # Use case-sensitive matching to detect store headers (must match "Depo Bangunan")
        store_header_re = re.compile(r'Depo\s+Bangunan')
        
        for header in headers:
            try:
                header_text = header.get_text(strip=True)
                
                # Skip "Gerai Depo Bangunan" as it's not a real location
                if header_text.startswith('Gerai'):
                    continue
                
                # Check if this is a store location header (case-sensitive)
                if store_header_re.search(header_text):
                    location = self._extract_location_from_header(header)
                    if location:
                        locations.append(location)
                        
            except Exception as e:
                logger.warning(f"Failed to extract location from header: {str(e)}")
                continue
        
        return locations
    
    def _extract_location_from_header(self, header) -> Optional[Location]:
        """Extract a single location from a header element and its following content"""
        store_name = self._element_extractor.extract_store_name(header)
        if not store_name:
            logger.debug("Store name extraction failed")
            return None
            
        address = self._element_extractor.extract_address(header)
        if not address:
            logger.debug("Address extraction failed")
            return None
        
        return self._create_location(store_name, address)
    
    def _create_location(self, store_name: str, address: str) -> Location:
        """Create a Location object"""
        return Location(name=store_name, code=address)
