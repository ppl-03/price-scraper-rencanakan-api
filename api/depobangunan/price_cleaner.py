import re
from typing import Union


class DepoPriceCleaner:
    # Pre-compile regex pattern for better performance
    _DIGIT_PATTERN = re.compile(r'\d+')
    
    @classmethod
    def clean_price(cls, price_string: Union[str, None]) -> int:
        if price_string is None:
            raise TypeError("price_string cannot be None")
        
        if not isinstance(price_string, str):
            raise TypeError("price_string must be a string")
        
        if not price_string:
            return 0
        
        # Extract all digit sequences and join them (faster than findall individual digits)
        digit_groups = cls._DIGIT_PATTERN.findall(price_string)
        if not digit_groups:
            return 0
        
        return int("".join(digit_groups))
    
    @staticmethod
    def is_valid_price(price: int) -> bool:
        return price > 0