import re

def clean_price_gemilang(price_string):
    digits = re.findall(r'\d', price_string)
    return int("".join(digits))

def scrape_products_from_gemilang_html(html_content):
    return [{}, {}]