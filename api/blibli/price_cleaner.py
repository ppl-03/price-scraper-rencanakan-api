import re
from typing import Union

class BlibliPriceCleaner:
    _digit_pattern = re.compile(r'\d')

    @staticmethod
    def clean_price(price_string: Union[str, None]) -> int:
        """
        Extracts digits from a price string and returns the integer value.
        Examples:
            "Rp 12.000" -> 12000
            "IDR 15,000" -> 15000
            "12.000" -> 12000
        """
        if price_string is None:
            raise TypeError("price_string cannot be None")
        if not isinstance(price_string, str):
            raise TypeError("price_string must be a string")
        if not price_string:
            return 0
        digits = BlibliPriceCleaner._digit_pattern.findall(price_string)
        if not digits:
            return 0
        return int("".join(digits))

    @staticmethod
    def is_valid_price(price: int) -> bool:
        return price > 0