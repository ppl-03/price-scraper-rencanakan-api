import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from html import unescape

from api.interfaces import ILocationParser, Location, HtmlParserError

logger = logging.getLogger(__name__)


class TextCleaner:
    
    @staticmethod
    def clean_store_name(text: Optional[str]) -> str:
        if not text:
            return ""
        return text.strip()
    
    @staticmethod
    def clean_address(text: Optional[str]) -> str:
        if not text:
            return ""
        
        lines = [line.strip() for line in text.split('\n')]
        filtered_lines = [line for line in lines if line]
        return '\n'.join(filtered_lines)
    
    @staticmethod
    def is_valid_text(text: Optional[str]) -> bool:
        return text is not None and text.strip() != ""


class HtmlElementExtractor:
    
    def __init__(self, text_cleaner: TextCleaner):
        self._text_cleaner = text_cleaner
    
    def extract_store_name(self, item) -> Optional[str]:
        try:
            link = item.find('a', class_='location_click')
            if not link:
                logger.debug("No location_click link found in item")
                return None
            
            text = link.get_text(strip=True)
            
            if not self._text_cleaner.is_valid_text(text):
                logger.debug("Store name text is empty or invalid")
                return None
            
            return self._text_cleaner.clean_store_name(text)
            
        except Exception as e:
            logger.warning(f"Failed to extract store name: {str(e)}")
            return None
    
    def extract_address(self, item) -> Optional[str]:
        try:
            address_div = item.find('div', class_='store-location')
            if not address_div:
                logger.debug("No store-location div found in item")
                return None
            
            # Replace <br> tags with newlines before extracting text
            for br in address_div.find_all('br'):
                br.replace_with('\n')
            
            # Get text and handle HTML entities
            text = address_div.get_text(strip=False)
            text = unescape(text)
            
            # Clean up excessive whitespace while preserving newlines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
            
            if not self._text_cleaner.is_valid_text(text):
                logger.debug("Address text is empty or invalid")
                return None
            
            cleaned_address = self._text_cleaner.clean_address(text)
            return cleaned_address if self._text_cleaner.is_valid_text(cleaned_address) else None
            
        except Exception as e:
            logger.warning(f"Failed to extract address: {str(e)}")
            return None
    
    def _remove_img_tags(self, element) -> None:
        img_tag = element.find('img')
        if img_tag:
            img_tag.decompose()
    
    def _convert_br_to_newlines(self, element) -> None:
        for br in element.find_all('br'):
            br.replace_with('\n')


class ParserConfiguration:
    """Configuration for parser behavior following Open/Closed Principle"""
    
    def __init__(self):
        self.location_item_class = 'info-store'
        self.location_link_class = 'location_click'
        self.address_div_class = 'store-location'
        self.preferred_parser = 'lxml'
        self.fallback_parser = 'html.parser'
    
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


class GemilangLocationParser(ILocationParser):
    
    def __init__(self, 
                 text_cleaner: TextCleaner = None,
                 element_extractor: HtmlElementExtractor = None,
                 config: ParserConfiguration = None):
        self._text_cleaner = text_cleaner or TextCleaner()
        self._element_extractor = element_extractor or HtmlElementExtractor(self._text_cleaner)
        self._config = config or ParserConfiguration()
    
    def parse_locations(self, html_content: str) -> List[Location]:
        if not self._is_valid_html_content(html_content):
            logger.debug("HTML content is empty or invalid")
            return []
        
        try:
            soup = self._create_soup(html_content)
            location_items = self._find_location_items(soup)
            
            logger.info(f"Found {len(location_items)} location items in HTML")
            
            locations = self._extract_locations_from_items(location_items)
            
            logger.info(f"Successfully parsed {len(locations)} locations")
            return locations
            
        except Exception as e:
            logger.error(f"Failed to parse HTML: {str(e)}")
            return []
    
    def _is_valid_html_content(self, html_content: str) -> bool:
        return html_content is not None and html_content.strip() != ""
    
    def _create_soup(self, html_content: str) -> BeautifulSoup:
        parser = self._config.get_parser()
        return BeautifulSoup(html_content, parser)
    
    def _find_location_items(self, soup: BeautifulSoup) -> list:
        return soup.find_all('div', class_=self._config.location_item_class)
    
    def _extract_locations_from_items(self, location_items: list) -> List[Location]:
        locations = []
        
        names = []
        addresses = []
        
        for item in location_items:
            try:
                store_name = self._element_extractor.extract_store_name(item)
                if store_name:
                    names.append(store_name)
                    
                address = self._element_extractor.extract_address(item)
                if address:
                    addresses.append(address)
                    
            except Exception as e:
                logger.warning(f"Failed to extract data from item: {str(e)}")
                continue
        
        min_count = min(len(names), len(addresses))
        for i in range(min_count):
            locations.append(self._create_location(names[i], addresses[i]))
        
        return locations
    
    def _extract_location_from_item(self, item) -> Optional[Location]:
        try:
            store_name = self._element_extractor.extract_store_name(item)
            if not store_name:
                logger.debug("Store name extraction failed")
                return None
                
            address = self._element_extractor.extract_address(item)
            if not address:
                logger.debug("Address extraction failed")
                return None
            
            return self._create_location(store_name, address)
        except Exception as e:
            logger.warning(f"Failed to extract location from item: {str(e)}")
            return None
    
    def _create_location(self, store_name: str, address: str) -> Location:
        return Location(name=store_name, code=address)