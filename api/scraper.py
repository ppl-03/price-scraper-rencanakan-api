import re
from bs4 import BeautifulSoup

def clean_price_gemilang(price_string):
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

def scrape_products_from_gemilang_html(html_content):
    if html_content is None:
        raise AttributeError("html_content cannot be None")
    
    if not isinstance(html_content, str):
        return []
    
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    
    product_items = soup.find_all('div', class_='item-product')
    
    for item in product_items:
        name_link = item.find('a')
        if not name_link:
            continue
            
        name_element = name_link.find('p', class_='product-name')
        if not name_element:
            continue
            
        name = name_element.get_text(strip=True)
        if not name:
            continue
            
        url = name_link.get('href', '')
        
        price_wrapper = item.find('div', class_='price-wrapper')
        if not price_wrapper:
            continue
            
        price_element = price_wrapper.find('p', class_='price')
        if not price_element:
            continue
            
        price_text = price_element.get_text(strip=True)
        price = clean_price_gemilang(price_text)
        
        if name and price > 0 and url:
            products.append({
                'name': name,
                'price': price,
                'url': url
            })
    
    return products

def clean_price_depo(price_string: str) -> int:
    digits = re.findall(r'\d+', price_string)
    return int("".join(digits)) if digits else 0

def scrape_products_from_depo_html(html_content: str):
    return []

def clean_price_mitra10(price_string: str) -> int:
    digits = re.findall(r'\d+', price_string)
    return int("".join(digits)) if digits else 0

def scrape_products_from_mitra10_html(html_content: str):
    return []

def clean_price_juraganmaterial(price_string: str) -> int:
    digits = re.findall(r'\d+', price_string)
    return int("".join(digits)) if digits else 0

def scrape_products_from_juraganmaterial_html(html_content: str):
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    
    # Find all product cards based on the documentation path: div.product-card
    product_cards = soup.find_all('div', class_='product-card')
    
    for card in product_cards:
        # Extract product name from the link
        name_link = card.find('a')
        if name_link:
            name_element = name_link.find('p', class_='product-name')
            name = name_element.get_text(strip=True) if name_element else ''
            url = name_link.get('href', '')
        else:
            name = ''
            url = ''
        
        # Extract price following the path: div.product-card-price -> div.price
        price_wrapper = card.find('div', class_='product-card-price')
        price = 0
        if price_wrapper:
            price_element = price_wrapper.find('div', class_='price')
            if price_element:
                price_text = price_element.get_text(strip=True)
                price = clean_price_juraganmaterial(price_text)
        
        if name and price:  # Only add if we have both name and price
            products.append({
                'name': name,
                'price': price,
                'url': url
            })
    
    return products