import re
from bs4 import BeautifulSoup

def clean_price_depo(price_string: str) -> int:
    digits = re.findall(r'\d+', price_string)
    return int("".join(digits)) if digits else 0

def scrape_products_from_depo_html(html_content: str):
    soup = BeautifulSoup(html_content, "html.parser")
    rows = []

    for card in soup.select("li.item.product.product-item"):
        link = card.select_one("strong.product.name.product-item-name a") or card.select_one("a[href]")
        name = (link.get_text(strip=True) if link else "") or ""
        url = link.get("href", "") if link else ""

        wrap = card.select_one("span.price-wrapper[data-price-type='finalPrice']")
        price = None
        if wrap and wrap.has_attr("data-price-amount"):
            try:
                price = int(float(wrap["data-price-amount"]))
            except ValueError:
                price = None

        if price is None:
            price_el = (card.select_one("span.price-wrapper[data-price-type='finalPrice'] span.price")
                        or card.select_one("span.price"))
            price = clean_price_depo(price_el.get_text()) if price_el else 0

        if name and price:
            rows.append({
                'name': name,
                'price': price,
                'url': url
            })

    return rows

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