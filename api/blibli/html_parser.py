import logging
from typing import List, Optional
from bs4 import BeautifulSoup

from api.interfaces import IHtmlParser, Product, HtmlParserError
from .price_cleaner import BlibliPriceCleaner

logger = logging.getLogger(__name__)

class BlibliHtmlParser(IHtmlParser):
    """
    HTML parser for Blibli product search results.
    Extracts product name, price, and URL from the search results page.
    """

    def __init__(self, price_cleaner: BlibliPriceCleaner = None):
        self.price_cleaner = price_cleaner or BlibliPriceCleaner()
        self._product_selector = "div.product-list__card"
        self._container_selector = "div.elf-product-card__container"
        self._link_selector = "a.elf-product-card"
        self._title_selector = "span.els-product__title"
        self._price_selector = "div.els-product__fixed-price"

    def parse_products(self, html_content: str) -> List[Product]:
        if not html_content:
            return []

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            product_items = soup.select(self._product_selector)
            logger.info(f"Found {len(product_items)} product items in HTML")

            products = []
            for item in product_items:
                product = self._safely_extract_product(item)
                if product:
                    products.append(product)

            logger.info(f"Successfully parsed {len(products)} products")
            return products

        except Exception as e:
            raise HtmlParserError(f"Failed to parse HTML: {str(e)}")

    def _safely_extract_product(self, item) -> Optional[Product]:
        try:
            return self._extract_product_from_item(item)
        except Exception as e:
            logger.warning(f"Failed to extract product from item: {str(e)}")
            return None

    def _extract_product_from_item(self, item) -> Optional[Product]:
        # Find the inner container
        container = item.select_one(self._container_selector)
        if not container:
            return None

        # Extract product URL
        url = self._extract_product_url(container)

        # Extract product name
        name = self._extract_product_name(container)
        if not name:
            return None

        # Extract product price
        price = self._extract_product_price(container)
        if not self.price_cleaner.is_valid_price(price):
            return None

        return Product(name=name, price=price, url=url)

    def _extract_product_url(self, container) -> str:
        link = container.select_one(self._link_selector)
        if link and link.get("href"):
            return link.get("href")
        return ""

    def _extract_product_name(self, container) -> Optional[str]:
        # Try to get name from the title span's 'title' attribute first
        title_span = container.select_one(self._title_selector)
        if title_span:
            if title_span.get("title"):
                return title_span.get("title").strip()
            # Fallback: get text content
            name_text = title_span.get_text(strip=True)
            if name_text:
                return name_text
        # Fallback: try image alt
        img = container.find("img")
        if img and img.get("alt"):
            return img.get("alt").strip()
        return None

    def _extract_product_price(self, container) -> int:
        price_div = container.select_one(self._price_selector)
        if price_div and price_div.get("title"):
            price_text = price_div.get("title").strip()
            try:
                return self.price_cleaner.clean_price(price_text)
            except (TypeError, ValueError):
                pass
        # Fallback: try to get price from visible text
        if price_div:
            price_text = price_div.get_text(strip=True)
            try:
                return self.price_cleaner.clean_price(price_text)
            except (TypeError, ValueError):
                pass
        return 0