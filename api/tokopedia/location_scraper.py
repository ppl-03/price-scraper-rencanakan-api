import logging
import re
from typing import Optional
from bs4 import BeautifulSoup, Tag
from .config import TokopediaLocations

logger = logging.getLogger(__name__)


class TokopediaLocationScraper:
    """
    Scrapes location information from Tokopedia product listings.
    
    Location is displayed as merchant/shop location on product cards,
    indicating where the seller is located and useful for understanding
    product availability and shipping times.
    
    Uses dependency injection to allow custom location configuration.
    """
    
    def __init__(self, location_config: TokopediaLocations = None):
        """
        Initialize the location scraper with optional configuration.
        
        Args:
            location_config: TokopediaLocations config object (uses defaults if None)
        """
        self.location_config = location_config or TokopediaLocations()
        self.locations_found = set()
    
    def extract_location_from_product_item(self, product_item: Tag) -> Optional[str]:
        """
        Extract location information from a product item element.
        
        Args:
            product_item: BeautifulSoup Tag containing the product element
            
        Returns:
            Location string if found, None otherwise
        """
        if not product_item:
            return None
        
        # Priority 1: Look for the specific span with class "css-ywdpwd" - this is the location span
        location = self._extract_from_location_span(product_item)
        if location:
            return location
        
        # Priority 2: Look for location in span elements (in document order)
        location = self._extract_from_span_elements(product_item)
        if location:
            return location
        
        # Strategy 3: Search all text nodes for location-like content
        location = self._extract_from_text_nodes(product_item)
        if location:
            return location
        
        return None
    
    def _extract_from_location_span(self, product_item: Tag) -> Optional[str]:
        """
        Extract location directly from the specific span with class "css-ywdpwd".
        
        This is the most reliable method as Tokopedia consistently uses this class
        for displaying the location/merchant location on product cards.
        
        Example: <span class="css-ywdpwd">Kab. Tangerang</span>
        """
        # Look for the specific span with class "css-ywdpwd"
        location_span = product_item.find('span', class_='css-ywdpwd')
        
        if location_span:
            text = location_span.get_text(strip=True)
            if text and len(text) > 0:
                return text
        
        return None
    
    def _extract_from_span_elements(self, product_item: Tag) -> Optional[str]:
        """
        Extract location from span elements in the product card.
        
        Tokopedia uses spans to display location information.
        We look through all spans and find the one that contains a valid location.
        We skip common UI buttons like "Tambah ke Wishlist", "Beli", etc.
        We also prioritize spans that contain location keywords.
        """
        # Find all span elements
        spans = product_item.find_all('span')
        
        for span in spans:
            text = span.get_text(strip=True)
            
            # Skip empty or very short text
            if not text or len(text) < 3:
                continue
            
            # Skip common UI text
            if text.lower() in self.location_config.SKIP_TEXTS or any(skip in text.lower() for skip in self.location_config.SKIP_TEXTS):
                continue
            
            # Skip if text is too long (likely a product name or description)
            if len(text) > 80:
                continue
            
            # Check if this text looks like a location
            location = self._clean_and_validate_location(text)
            if location:
                # Check if it contains location keywords
                location_lower = location.lower()
                has_location_keyword = any(
                    keyword in location_lower for keyword in self.location_config.LOCATION_KEYWORDS
                )
                
                # Only return if it has location keywords or has specific pattern (Kab./Kota.)
                if has_location_keyword or any(pattern in location_lower for pattern in ['kab', 'kota']):
                    return location
        
        return None
    
    def _extract_from_text_nodes(self, product_item: Tag) -> Optional[str]:
        """
        Extract location by searching through all text nodes.
        
        This is a fallback strategy that looks through all text content
        for location-like patterns. Returns the first segment that contains
        a known location name or location keywords.
        """
        all_text = product_item.get_text()
        
        # Split by common delimiters and check each segment
        segments = re.split(self.location_config.DELIMITER_PATTERN, all_text)
        
        # First pass: look for known location names or keywords
        for segment in segments:
            text = segment.strip()
            
            # Skip empty or very short text
            if not text or len(text) < 3 or len(text) > 80:
                continue
            
            location = self._clean_and_validate_location(text)
            if location:
                # Check if it's a known location
                location_lower = location.lower()
                is_known_location = any(
                    known in location_lower for known in self.location_config.LOCATION_KEYWORDS
                )
                
                if is_known_location:
                    return location
        
        # Second pass: if no known location found, return first valid text
        for segment in segments:
            text = segment.strip()
            
            # Skip empty or very short text
            if not text or len(text) < 3 or len(text) > 80:
                continue
            
            location = self._clean_and_validate_location(text)
            if location:
                return location
        
        return None
    
    def _clean_and_validate_location(self, text: str) -> Optional[str]:
        """
        Clean, normalize location text.
        
        Performs minimal processing - just normalizes whitespace and
        removes any special characters, but keeps the location as-is without
        validating against a database.
        
        Args:
            text: Raw text to process
            
        Returns:
            Cleaned location string if valid length, None otherwise
        """
        if not text:
            return None
        
        # Normalize whitespace
        text = ' '.join(text.split()).strip()
        
        # Skip if too short or too long
        if len(text) < self.location_config.MIN_LENGTH or len(text) > self.location_config.MAX_LENGTH:
            return None
        
        # Basic cleanup - remove very special characters but keep letters, numbers, spaces, hyphens, periods
        # Keep periods for abbreviations like Kab., Kota., etc.
        cleaned = re.sub(r'[^a-zA-Z0-9\s\-\.\,]', '', text)
        
        # Normalize spaces again
        cleaned = ' '.join(cleaned.split()).strip()
        
        # Return as-is if it has content
        if cleaned and len(cleaned) > 0:
            return cleaned
        
        return None
    
    def _is_valid_location(self, location: str) -> bool:
        """
        Validate if the extracted text looks like a valid location.
        
        This is a very lenient validation - mainly checks that it's not empty
        and has reasonable length.
        
        Args:
            location: Location text to validate
            
        Returns:
            True if location appears valid, False otherwise
        """
        if not location or len(location) < 2:
            return False
        
        # If text is too long, probably not a location
        if len(location) > 100:
            return False
        
        # Must have at least some alphabetic characters
        if not any(c.isalpha() for c in location):
            return False
        
        return True
    
    def reset(self):
        """Reset the scraper state."""
        self.locations_found.clear()


# Singleton instance for convenience
_location_scraper = None


def get_location_scraper(location_config: TokopediaLocations = None) -> TokopediaLocationScraper:
    """
    Get or create the singleton location scraper instance.
    
    Args:
        location_config: Optional custom location configuration
        
    Returns:
        TokopediaLocationScraper singleton instance
    """
    global _location_scraper
    if _location_scraper is None:
        _location_scraper = TokopediaLocationScraper(location_config)
    return _location_scraper
