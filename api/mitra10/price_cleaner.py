import re
from typing import Union
from functools import lru_cache


class Mitra10PriceCleaner:
    _digit_pattern = re.compile(r'\d')
    
    _price_cache = {}
    _max_cache_size = 1000
    
    @classmethod
    def clean_price(cls, price_string: Union[str, None]) -> int:
        if price_string is None:
            raise TypeError("price_string cannot be None")
        
        if not isinstance(price_string, str):
            raise TypeError("price_string must be a string")
        
        if not price_string:
            return 0
        
        if price_string in cls._price_cache:
            return cls._price_cache[price_string]
        
        digits = cls._digit_pattern.findall(price_string)
        if not digits:
            result = 0
        else:
            result = int("".join(digits))
        
        if len(cls._price_cache) < cls._max_cache_size:
            cls._price_cache[price_string] = result
        
        return result
    
    @staticmethod
    @lru_cache(maxsize=100)
    def is_valid_price(price: int) -> bool:
        return price > 0
    
    @classmethod
    def clear_cache(cls):
        cls._price_cache.clear()