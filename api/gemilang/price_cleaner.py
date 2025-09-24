import re
from typing import Union


class GemilangPriceCleaner:
    
    @staticmethod
    def clean_price(price_string: Union[str, None]) -> int:
        if price_string is None:
            raise TypeError("price_string cannot be None")
        
        if not isinstance(price_string, str):
            raise TypeError("price_string must be a string")
        
        if not price_string:
            return 0
        
        digits = re.findall(r'\d', price_string)
        if not digits:
            return 0
        
        return int("".join(digits))
    
    @staticmethod
    def is_valid_price(price: int) -> bool:
        return price > 0