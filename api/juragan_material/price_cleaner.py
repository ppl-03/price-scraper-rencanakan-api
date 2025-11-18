import re
from typing import Union


class PriceRegexCache:
    """Cache for compiled regex patterns used in price cleaning."""
    DIGIT_PATTERN = re.compile(r'\d')


class JuraganMaterialPriceCleaner:
    
    @staticmethod
    def clean_price(price_string: Union[str, None]) -> int:
        """
        Clean price string and return integer value.
        
        Args:
            price_string: Price string to clean (e.g., "Rp 60.500")
            
        Returns:
            int: Cleaned price as integer
            
        Raises:
            TypeError: If price_string is None or not a string
        """
        if price_string is None:
            raise TypeError("price_string cannot be None")
        
        if not isinstance(price_string, str):
            raise TypeError("price_string must be a string")
        
        if not price_string:
            return 0
        
        # Extract all digits from the string using cached regex pattern
        digits = PriceRegexCache.DIGIT_PATTERN.findall(price_string)
        if not digits:
            return 0
        
        return int("".join(digits))
    
    @staticmethod
    def is_valid_price(price: int) -> bool:
        """
        Check if price is valid (greater than 0).
        
        Args:
            price: Price value to validate
            
        Returns:
            bool: True if price is valid, False otherwise
        """
        return price > 0