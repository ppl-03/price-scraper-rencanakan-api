import logging
from typing import List
from bs4 import BeautifulSoup

from api.interfaces import HtmlParserError

logger = logging.getLogger(__name__)


class SelectorConfig:
    def __init__(self):
        self.dropdown_container = 'div[role="presentation"].MuiPopover-root'
        self.location_list = 'ul.MuiList-root'
        self.location_item = 'li.MuiButtonBase-root'
        self.location_text = 'span'


class Mitra10LocationParser:
    MITRA10_PREFIX = "MITRA10 "
    
    def __init__(self, selector_config: SelectorConfig = None):
        self._selectors = selector_config or SelectorConfig()
    
    def parse_locations(self, html_content: str) -> List[str]:
        if not html_content:
            return []
        
        try:
            return self._parse_with_lxml(html_content)
        except Exception as e:
            return self._parse_with_fallback(html_content, e)
    
    def _parse_with_lxml(self, html_content: str) -> List[str]:
        soup = BeautifulSoup(html_content, 'lxml')
        return self._extract_locations(soup)
    
    def _parse_with_fallback(self, html_content: str, original_error: Exception) -> List[str]:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return self._extract_locations(soup)
        except Exception:
            raise HtmlParserError(f"Failed to parse location HTML: {str(original_error)}")
    
    def _extract_locations(self, soup: BeautifulSoup) -> List[str]:
        locations = []
        
        dropdown_container = soup.select_one(self._selectors.dropdown_container)
        if not dropdown_container:
            logger.warning(f"No dropdown container found with selector: {self._selectors.dropdown_container}")
            return []
        
        logger.info("Found dropdown container with exact selector")
        
        location_list = dropdown_container.select_one(self._selectors.location_list)
        if not location_list:
            logger.warning(f"No location list found with selector: {self._selectors.location_list}")
            return []
        
        logger.info("Found location list within container")
        
        location_items = location_list.select(self._selectors.location_item)
        if not location_items:
            logger.warning(f"No location items found with selector: {self._selectors.location_item}")
            return []
        
        logger.info(f"Found {len(location_items)} location items")
        
        for item in location_items:
            span = item.select_one(self._selectors.location_text)
            if span:
                text = span.get_text(strip=True)
                if text and self._is_valid_location_name(text):
                    if text.startswith(self.MITRA10_PREFIX):
                        text = text[len(self.MITRA10_PREFIX):].strip()
                    locations.append(text)
        
        logger.info(f"Successfully extracted {len(locations)} valid locations")
        return locations
    
    def _is_valid_location_name(self, name: str) -> bool:
        if not name or len(name.strip()) < 3:
            return False
        
        exclude_terms = [
            'select', 'choose', 'option', 'menu', 'close', 'search', 'filter',
            'dispenser', 'portable', 'category', 'product', 'brand', 'promo'
        ]
        name_lower = name.lower()
        
        for term in exclude_terms:
            if term in name_lower:
                return False
        
        return True
    
    def get_dropdown_selector(self) -> str:
        return self._selectors.dropdown_container
    
    def get_location_list_selector(self) -> str:
        return self._selectors.location_list
    
    def get_location_item_selector(self) -> str:
        return self._selectors.location_item