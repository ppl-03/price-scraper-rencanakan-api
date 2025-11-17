import re
from typing import Optional
from .config import TokopediaPriceConfig


class TokopediaPriceCleaner:
    """Clean and normalize price strings from Tokopedia"""
    
    def __init__(self, price_config: TokopediaPriceConfig = None):
        """
        Initialize price cleaner with optional configuration.
        
        Args:
            price_config: Custom price configuration (uses defaults if None)
        """
        self.price_config = price_config or TokopediaPriceConfig()
        # Regex pattern to match Tokopedia price format: Rp123.456
        self.price_pattern = re.compile(r'Rp\s*([\d,\.]+)', re.IGNORECASE)
        self.number_pattern = re.compile(r'[\d,\.]+')
    
    def clean_price_string(self, price_text: str) -> Optional[int]:
        """
        Clean price string and convert to integer
        
        Args:
            price_text: Raw price string from HTML (e.g., "Rp62.500")
            
        Returns:
            Integer price in rupiah or None if parsing fails
        """
        if not price_text or not isinstance(price_text, str):
            return None
        
        try:
            # Remove whitespace and normalize
            price_text = price_text.strip()
            
            # Extract price using regex
            match = self.price_pattern.search(price_text)
            if not match:
                # Fallback: try to extract just numbers
                number_match = self.number_pattern.search(price_text)
                if not number_match:
                    return None
                price_text = number_match.group()
            else:
                price_text = match.group(1)
            
            # Remove separators and convert to integer
            # Tokopedia uses dots as thousand separators
            clean_price = price_text.replace(',', '').replace('.', '')
            
            # Convert to integer
            return int(clean_price)
            
        except (ValueError, AttributeError):
            return None
    
    def clean_price(self, price_text: str) -> int:
        """
        Clean price string and convert to integer (interface compatibility)
        
        Args:
            price_text: Raw price string from HTML (e.g., "Rp62.500")
            
        Returns:
            Integer price in rupiah or 0 if parsing fails
        """
        result = self.clean_price_string(price_text)
        return result if result is not None else 0
    
    def is_valid_price(self, price: int) -> bool:
        """
        Alias for validate_price method for interface compatibility
        
        Args:
            price: Price in rupiah
            
        Returns:
            True if price seems valid
        """
        return self.validate_price(price)
    
    def validate_price(self, price: int) -> bool:
        """
        Validate if price is reasonable for construction materials
        
        Args:
            price: Price in rupiah
            
        Returns:
            True if price seems valid
        """
        if not isinstance(price, int):
            return False
        
        # Use configured price range
        return self.price_config.is_valid(price)