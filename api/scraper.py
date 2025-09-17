import re

def clean_price_gemilang(price_string):
    digits = re.findall(r'\d', price_string)
    return int("".join(digits))

def scrape_products_from_gemilang_html(html_content):
    return [{}, {}]

def clean_price_depo(price_string: str) -> int:
    digits = re.findall(r'\d+', price_string)
    return int("".join(digits)) if digits else 0

def scrape_products_from_depo_html(html_content: str):
    return []