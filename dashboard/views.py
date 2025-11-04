from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseNotAllowed
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.urls import reverse
from .forms import ItemPriceProvinceForm
from . import models

from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re, json, os, time
import secrets

# For diagnostics + plain HTML fetch
from api.core import BaseHttpClient

# Vendors (use each package's own factory + url builder)
from api.gemilang.factory import create_gemilang_scraper, create_gemilang_location_scraper
from api.gemilang.url_builder import GemilangUrlBuilder

from api.depobangunan.factory import create_depo_scraper, create_depo_location_scraper
from api.depobangunan.url_builder import DepoUrlBuilder

from api.juragan_material.factory import create_juraganmaterial_scraper
from api.juragan_material.url_builder import JuraganMaterialUrlBuilder

from api.mitra10.factory import create_mitra10_scraper, create_mitra10_location_scraper
from api.mitra10.url_builder import Mitra10UrlBuilder

from api.tokopedia.factory import create_tokopedia_scraper
from api.tokopedia.url_builder import TokopediaUrlBuilder
from api.tokopedia.scraper import TOKOPEDIA_LOCATION_IDS
from api.tokopedia.location_scraper import TokopediaLocationScraper
from api.tokopedia.unit_parser import TokopediaUnitParser

# Playwright fallback (optional at runtime)
HAS_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except Exception:
    HAS_PLAYWRIGHT = False

USE_BROWSER_FALLBACK = os.getenv("USE_BROWSER_FALLBACK", "auto").lower()  # auto|always|never

# Constants to avoid duplication
GEMILANG_SOURCE = "Gemilang Store"
DEPO_BANGUNAN_SOURCE = "Depo Bangunan"
JURAGAN_MATERIAL_SOURCE = "Juragan Material"
MITRA10_SOURCE = "Mitra10"
TOKOPEDIA_SOURCE = "Tokopedia"
DASHBOARD_FORM_TEMPLATE = "dashboard/form.html"
JSON_LD_TYPE_KEY = "@type"
HTML_PARSER = "html.parser"

# Error message constants
CONTEXT_MANAGER_ERROR = "context manager"
UNKNOWN_ERROR_MSG = "Unknown error"

# CSS selector constants
PRODUCT_NAME_SELECTOR = ".product-name"
HREF_SELECTOR = "a[href]"


# ---------------- small utilities ----------------
def _digits_to_int(txt: str) -> int:
    ds = re.findall(r"\d", txt or "")
    return int("".join(ds)) if ds else 0


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _build_url_defensively(url_builder, keyword: str, sort_by_price: bool, page: int) -> str:
    if hasattr(url_builder, "build_search_url"):
        return url_builder.build_search_url(keyword, sort_by_price=sort_by_price, page=page)
    if hasattr(url_builder, "build_url"):
        return url_builder.build_url(keyword)
    raise AttributeError("URL builder has no supported build methods.")


def _human_get(url: str, tries: int = 2, sleep_sec: float = 0.6) -> str:
    """
    Simple retry wrapper around BaseHttpClient().get(url).
    We keep it minimal (no custom headers) to avoid breaking your client.
    """
    html = ""
    for _ in range(max(1, tries)):
        try:
            html = BaseHttpClient().get(url) or ""
            if html.strip():
                break
        except Exception:
            pass
        time.sleep(sleep_sec + secrets.SystemRandom().uniform(0, 0.4))
    return html


def _fetch_len(url: str) -> int:
    try:
        return len(BaseHttpClient().get(url) or "")
    except Exception:
        return 0


# ---------------- Juragan fallback (HTML-only) ----------------
def _extract_juragan_product_name(card) -> str | None:
    """Extract product name from Juragan Material card."""
    for sel in ("a " + PRODUCT_NAME_SELECTOR, PRODUCT_NAME_SELECTOR, PRODUCT_NAME_SELECTOR, "[class*=name]"):
        el = card.select_one(sel)
        if el and el.get_text(strip=True):
            return _clean_text(el.get_text(" ", strip=True))

    img = card.find("img")
    if img and img.get("alt"):
        return _clean_text(img["alt"])

    return None


def _extract_juragan_product_link(card) -> str:
    """Extract product link from Juragan Material card."""
    link = card.select_one("a:has(p" + PRODUCT_NAME_SELECTOR + ")") or card.select_one(HREF_SELECTOR)
    return link.get("href") if link and link.get("href") else "/products/product"


def _extract_juragan_product_price(card) -> int:
    """Extract product price from Juragan Material card."""
    # Try primary price selector
    price = _try_primary_juragan_price(card)
    if price > 0:
        return price

    # Try secondary price selectors
    price = _try_secondary_juragan_price(card)
    if price > 0:
        return price

    # Try currency text fallback
    return _try_currency_text_juragan_price(card)


def _try_primary_juragan_price(card) -> int:
    """Try to extract price from primary Juragan Material price selector."""
    el = card.select_one("div.product-card-price div.price")
    if el:
        price = _digits_to_int(el.get_text(" ", strip=True))
        if price > 0:
            return price
    return 0


def _try_secondary_juragan_price(card) -> int:
    """Try to extract price from secondary Juragan Material price selectors."""
    wrapper = card.select_one("div.product-card-price") or card
    if wrapper:
        for tag in wrapper.find_all(["span", "div", "p", "h1", "h2", "h3", "h4", "h5", "h6"], string=True):
            v = _digits_to_int(tag.get_text(" ", strip=True))
            if v > 0:
                return v
    return 0


def _try_currency_text_juragan_price(card) -> int:
    """Try to extract price from currency text in Juragan Material card."""
    for t in card.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
        v = _digits_to_int((t or "").strip())
        if v > 0:
            return v
    return 0


def _extract_juragan_product_unit(url: str) -> str:
    """Extract product unit from Juragan Material product detail page."""
    try:
        if not url:
            return ""

        # Handle relative URLs
        if url.startswith('/'):
            url = f"https://juraganmaterial.id{url}"

        # Fetch product detail page
        html = _human_get(url)
        soup = BeautifulSoup(html, HTML_PARSER)

        # Extract unit using the same CSS selector as the main parser
        unit_element = soup.select_one('html > body > div:nth-of-type(1) > div > main > div > div:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(2) > div:nth-of-type(2) > div > div:nth-of-type(1) > p:nth-of-type(2)')
        if unit_element:
            return unit_element.get_text(strip=True)

        return ""
    except Exception:
        return ""


def _extract_depo_product_unit(url: str) -> str:
    """Extract product unit from Depo Bangunan product detail page."""
    try:
        if not url:
            return ""

        # Handle relative URLs
        if url.startswith('/'):
            url = f"https://www.depobangunan.com{url}"

        # Fetch product detail page
        html = _human_get(url)
        if not html:
            return ""

        # Use Depo Bangunan's unit parser to extract unit from detail page
        from api.depobangunan.unit_parser import DepoBangunanUnitParser
        unit_parser = DepoBangunanUnitParser()

        # Try to extract unit from the detail page HTML
        unit = unit_parser.parse_unit_from_detail_page(html)
        return unit or ""

    except Exception:
        return ""


def _extract_depo_product_unit_from_name(name: str) -> str:
    """Extract product unit from Depo Bangunan product name."""
    try:
        if not name:
            return ""

        # Use Depo Bangunan's unit parser to extract unit from product name
        from api.depobangunan.unit_parser import DepoBangunanUnitParser
        unit_parser = DepoBangunanUnitParser()

        # Try to extract unit from the product name
        unit = unit_parser.parse_unit_from_product_name(name)
        return unit or ""

    except Exception:
        return ""


def _extract_mitra10_product_unit(url: str) -> str:
    """Extract product unit from Mitra10 product detail page."""
    try:
        if not url:
            return ""
        
        # Handle relative URLs
        if url.startswith('/'):
            url = f"https://www.mitra10.com{url}"
        
        # Fetch product detail page
        html = _human_get(url)
        if not html:
            return ""
        
        # Use Mitra10's unit parser to extract unit from detail page
        from api.mitra10.unit_parser import Mitra10UnitParser
        unit_parser = Mitra10UnitParser()
        
        # Try to extract unit from the detail page HTML
        unit = unit_parser.parse_unit(html)
        return unit or ""
        
    except Exception:
        return ""


def _extract_mitra10_product_unit_from_name(name: str) -> str:
    """Extract product unit from Mitra10 product name."""
    try:
        if not name:
            return ""
        
        # Use Mitra10's unit parser to extract unit from product name
        from api.mitra10.unit_parser import Mitra10UnitExtractor
        unit_extractor = Mitra10UnitExtractor()
        
        # Try to extract unit from the product name
        unit = unit_extractor.extract_unit(name)
        return unit or ""
        
    except Exception:
        return ""


def _extract_juragan_product_location(url: str) -> str:
    """Extract product location from Juragan Material product detail page using groupmate's method."""
    try:
        if not url:
            return ""

        # Handle relative URLs
        if url.startswith('/'):
            url = f"https://juraganmaterial.id{url}"

        # Fetch product detail page
        html = _human_get(url)
        soup = BeautifulSoup(html, HTML_PARSER)

        # Extract location using the same CSS selector as the groupmate's parser
        location_element = soup.select_one('#footer-address-link > span:nth-child(2)')
        if location_element:
            return location_element.get_text(strip=True)

        return ""
    except Exception:
        return ""


def _juragan_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    try:
        url = _build_url_defensively(JuraganMaterialUrlBuilder(), keyword, sort_by_price, page)
        html = _human_get(url)
        soup = BeautifulSoup(html, HTML_PARSER)

        # Find product cards
        cards = soup.select("div.product-card") or \
                soup.select("div.product-card__item, div.card-product, div.catalog-item, div.product")

        out = []
        for card in cards:
            name = _extract_juragan_product_name(card)
            if not name:
                continue

            href = _extract_juragan_product_link(card)
            price = _extract_juragan_product_price(card)

            if price <= 0:
                continue

            # Extract unit and location for Juragan Material
            unit = _extract_juragan_product_unit(href) if href else ""
            location = _extract_juragan_product_location(href) if href else ""

            out.append({"item": name, "value": price, "unit": unit, "location": location, "source": JURAGAN_MATERIAL_SOURCE, "url": href})

        return out, url, len(html)
    except Exception:
        return [], "", 0


# ---------------- Depo Bangunan fallback ----------------
def _extract_depo_product_name(card) -> str | None:
    """Extract product name from Depo Bangunan card."""
    # Try specific Depo Bangunan selectors
    for sel in ("strong.product.name.product-item-name a", "strong.product-item-name a", ".product-item-name", PRODUCT_NAME_SELECTOR):
        el = card.select_one(sel)
        if el and el.get_text(strip=True):
            return _clean_text(el.get_text(" ", strip=True))

    # Try image alt text fallback
    img = card.find("img")
    if img and img.get("alt"):
        return _clean_text(img["alt"])

    return None


def _extract_depo_product_link(card) -> str:
    """Extract product link from Depo Bangunan card."""
    # Try to find the product name link
    link = card.select_one("strong.product.name.product-item-name a") or \
           card.select_one("strong.product-item-name a") or \
           card.select_one(HREF_SELECTOR)

    if link and link.get("href"):
        href = link.get("href")
        # Handle relative URLs
        if href.startswith('/'):
            return f"https://www.depobangunan.com{href}"
        return href

    return "https://www.depobangunan.com/"


def _extract_depo_product_price(card) -> int:
    """Extract product price from Depo Bangunan card."""
    # Try data attribute first (most reliable for Depo Bangunan)
    price = _try_depo_data_attribute_price(card)
    if price > 0:
        return price

    # Try special price
    price = _try_depo_special_price(card)
    if price > 0:
        return price

    # Try regular price
    price = _try_depo_regular_price(card)
    if price > 0:
        return price

    # Try currency text fallback
    return _try_depo_currency_text_price(card)


def _try_depo_data_attribute_price(card) -> int:
    """Try to extract price from data attribute."""
    price_wrapper = card.find('span', {'data-price-type': 'finalPrice'})
    if price_wrapper and price_wrapper.get('data-price-amount'):
        try:
            return int(float(price_wrapper.get('data-price-amount')))
        except (ValueError, TypeError):
            pass
    return 0


def _try_depo_special_price(card) -> int:
    """Try to extract special price."""
    special_price = card.find('span', class_='special-price')
    if special_price:
        price_span = special_price.find('span', class_='price')
        if price_span:
            price = _digits_to_int(price_span.get_text(" ", strip=True))
            if price > 0:
                return price
    return 0


def _try_depo_regular_price(card) -> int:
    """Try to extract regular price."""
    price_box = card.find('div', class_='price-box')
    if price_box:
        price_span = price_box.find('span', class_='price')
        if price_span:
            price = _digits_to_int(price_span.get_text(" ", strip=True))
            if price > 0:
                return price
    return 0


def _try_depo_currency_text_price(card) -> int:
    """Try to extract price from currency text."""
    for t in card.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
        v = _digits_to_int((t or "").strip())
        if v > 0:
            return v
    return 0


def _depo_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    try:
        url = _build_url_defensively(DepoUrlBuilder(), keyword, sort_by_price, page)
        html = _human_get(url)
        soup = BeautifulSoup(html, HTML_PARSER)

        # Find product cards using Depo Bangunan specific selectors
        cards = soup.select("li.item.product.product-item") or \
                soup.select("li.product-item") or \
                soup.select("div.product-item")

        out = []
        for card in cards:
            name = _extract_depo_product_name(card)
            if not name:
                continue

            href = _extract_depo_product_link(card)
            price = _extract_depo_product_price(card)

            if price <= 0:
                continue

            # Extract unit from product name first (faster)
            unit = _extract_depo_product_unit_from_name(name)

            # If no unit found from name, try extracting from detail page
            if not unit and href:
                unit = _extract_depo_product_unit(href)

            out.append({"item": name, "value": price, "unit": unit, "source": DEPO_BANGUNAN_SOURCE, "url": href})

        return out, url, len(html)
    except Exception:
        return [], "", 0


# ---------------- Mitra10 helpers + fallback ----------------
def _looks_like_bot_challenge(html: str) -> bool:
    if not html:
        return False
    L = html.lower()
    return ("attention required" in L) or ("verify you are human" in L) or ("cf-challenge" in L) or ("captcha" in L)


def _fetch_with_playwright(url: str, wait_selector: str | None = None, timeout_ms: int = 12000) -> str:
    if not HAS_PLAYWRIGHT:
        return ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
                java_script_enabled=True,
                viewport={"width": 1366, "height": 900},
            )
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=timeout_ms // 2)
            except Exception:
                pass
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=timeout_ms // 2)
                except Exception:
                    pass
            html = page.content()
            ctx.close(); browser.close()
            return html or ""
    except Exception:
        return ""


def _extract_price_from_node(node) -> int:
    """Extract price from DOM node using multiple strategies."""
    # Try data attributes first
    price = _try_data_attributes_price(node)
    if price > 0:
        return price

    # Try specific price classes
    price = _try_specific_price_classes(node)
    if price > 0:
        return price

    # Try generic class-based search
    price = _try_generic_price_classes(node)
    if price > 0:
        return price

    # Try currency text search
    price = _try_currency_text_price(node)
    if price > 0:
        return price

    # Last resort: all text containing numbers
    return _try_numeric_text_price(node)


def _try_data_attributes_price(node) -> int:
    """Try extracting price from data attributes."""
    for attr in ["data-price-amount", "data-price", "data-cost"]:
        elem = node.find(attrs={attr: True})
        if elem and elem.get(attr):
            try:
                return int(float(str(elem[attr]).replace(",", "")))
            except Exception:
                pass
    return 0


def _try_specific_price_classes(node) -> int:
    """Try extracting price from specific CSS selectors."""
    price_selectors = [
        ".price-wrapper[data-price-amount]",
        "span.price__final", "p.price__final", 
        ".price-box .price", "span.price", ".price"
    ]

    for selector in price_selectors:
        try:
            el = node.select_one(selector)
            if el and el.get_text(strip=True):
                v = _digits_to_int(el.get_text(" ", strip=True))
                if v > 0:
                    return v
        except Exception:
            continue
    return 0


def _try_generic_price_classes(node) -> int:
    """Try extracting price from generic price-related classes."""
    try:
        price_elements = node.select("[class*=price]")
        for el in price_elements:
            v = _digits_to_int(el.get_text(" ", strip=True))
            if v > 0:
                return v
    except Exception:
        pass
    return 0


def _try_currency_text_price(node) -> int:
    """Try extracting price from currency text patterns."""
    currency_patterns = ["Rp", "IDR", "rupiah"]
    for pattern in currency_patterns:
        for t in node.find_all(string=lambda s: s and pattern in str(s)):
            v = _digits_to_int(str(t))
            if v > 0:
                return v
    return 0


def _try_numeric_text_price(node) -> int:
    """Last resort: extract price from numeric text patterns."""
    all_text = node.get_text()
    numbers = re.findall(r'\d{4,}', all_text)  # Look for 4+ digit numbers
    for num_str in numbers:
        try:
            num = int(num_str)
            if 1000 <= num <= 100000000:  # Reasonable price range
                return num
        except Exception:
            continue
    return 0


def _extract_price_from_jsonld_offers(offers) -> int:
    """Extract price from JSON-LD offers object."""
    if isinstance(offers, dict) and offers.get("price"):
        try:
            return int(float(str(offers.get("price")).replace(",", "")))
        except Exception:
            return _digits_to_int(str(offers.get("price")))
    return 0


def _process_jsonld_product(prod_data: dict) -> tuple[str | None, int, str | None]:
    """Process a single product from JSON-LD data."""
    name = prod_data.get("name")
    price_val = _extract_price_from_jsonld_offers(prod_data.get("offers"))
    url_ = prod_data.get("url") or prod_data.get("@id")
    return name, price_val, url_


def _parse_jsonld_itemlist(data: dict, emit_func):
    """Parse JSON-LD ItemList or SearchResultsPage."""
    if not isinstance(data, dict) or data.get(JSON_LD_TYPE_KEY) not in ("ItemList", "SearchResultsPage"):
        return

    elems = data.get("itemListElement") or []
    for e in elems:
        prod = e.get("item") if isinstance(e, dict) else None
        if isinstance(prod, dict) and (prod.get(JSON_LD_TYPE_KEY) == "Product" or "name" in prod):
            name, price_val, url_ = _process_jsonld_product(prod)
            emit_func(name, price_val, url_)


def _parse_jsonld_products(data: dict | list, emit_func):
    """Parse standalone JSON-LD products."""
    candidates = data if isinstance(data, list) else [data]
    for d in candidates:
        if not isinstance(d, dict):
            continue
        if d.get(JSON_LD_TYPE_KEY) == "Product" or "name" in d:
            name, price_val, url_ = _process_jsonld_product(d)
            emit_func(name, price_val, url_)


def _parse_mitra10_jsonld(soup, request_url: str, seen: set) -> list[dict]:
    """Parse Mitra10 JSON-LD structured data."""
    out = []

    def _emit(name: str | None, price_val: int, href: str | None):
        if not name or price_val <= 0:
            return
        full_url = urljoin(request_url, href or "")
        key = full_url or (name, price_val)
        if key in seen:
            return
        seen.add(key)
        
        # Extract unit from product name first (faster)
        unit = _extract_mitra10_product_unit_from_name(name)
        
        # If no unit found from name, try extracting from detail page
        if not unit and full_url:
            unit = _extract_mitra10_product_unit(full_url)
        
        out.append({"item": _clean_text(name), "value": price_val, "unit": unit, "source": MITRA10_SOURCE, "url": full_url})

    jsonld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in jsonld_scripts:
        _process_jsonld_script(script, _emit)

    return out


def _process_jsonld_script(script, emit_func):
    """Process a single JSON-LD script tag."""
    raw = (script.string or script.text or "").strip()
    if not raw:
        return

    try:
        data = json.loads(raw)
    except Exception:
        return

    # Try parsing as ItemList/SearchResultsPage
    try:
        _parse_jsonld_itemlist(data, emit_func)
    except Exception:
        pass

    # Try parsing as standalone products
    try:
        _parse_jsonld_products(data, emit_func)
    except Exception:
        pass


def _extract_mitra10_product_name(container) -> str | None:
    """Extract product name from Mitra10 DOM container with generic fallbacks."""
    # Try specific product selectors first
    name = _try_specific_mitra10_selectors(container)
    if name:
        return name

    # Try image alt text
    name = _try_mitra10_image_alt(container)
    if name:
        return name

    # Try link titles and text
    name = _try_mitra10_link_text(container)
    if name:
        return name

    # Generic fallback: longest meaningful text in container
    return _try_mitra10_generic_text(container)


def _try_specific_mitra10_selectors(container) -> str | None:
    """Try specific product selectors for Mitra10."""
    specific_selectors = [
        "a.product-item-link",
        PRODUCT_NAME_SELECTOR,
        "h3", "h2", "h1"
    ]

    for sel in specific_selectors:
        try:
            el = container.select_one(sel)
            if el and _clean_text(el.get_text()):
                return _clean_text(el.get_text())
        except Exception:
            continue
    return None


def _try_mitra10_image_alt(container) -> str | None:
    """Try extracting product name from image alt text."""
    img = container.find("img")
    if img and img.get("alt"):
        alt_text = _clean_text(img["alt"])
        if len(alt_text) > 3:  # Avoid tiny alt texts
            return alt_text
    return None


def _try_mitra10_link_text(container) -> str | None:
    """Try extracting product name from link titles and text."""
    links = container.find_all("a", href=True)
    for link in links:
        # Try title attribute
        if link.get("title"):
            title = _clean_text(link["title"])
            if len(title) > 3:
                return title

        # Try link text
        link_text = _clean_text(link.get_text())
        if 10 <= len(link_text) <= 200:  # Reasonable product name length
            return link_text
    return None


def _try_mitra10_generic_text(container) -> str | None:
    """Generic fallback: longest meaningful text in container."""
    text_elements = container.find_all(["span", "div", "p"], string=True)
    candidates = []
    skip_terms = ["rp", "price", "buy", "cart"]

    for elem in text_elements:
        text = _clean_text(elem.get_text())
        if 10 <= len(text) <= 200 and not any(skip in text.lower() for skip in skip_terms):
            candidates.append(text)

    if candidates:
        # Return the longest candidate as it's likely the product name
        return max(candidates, key=len)

    return None


def _extract_mitra10_product_url(container, request_url: str) -> str:
    """Extract product URL from Mitra10 DOM container."""
    # Try different link selectors individually
    link_selectors = [
        "a.product-item-link",
        "a.gtm_mitra10_cta_product",
        "a[href*=\"/product/\"]",
        "a[href*=\"/catalog/\"]",
        HREF_SELECTOR
    ]

    link = None
    for selector in link_selectors:
        try:
            link = container.select_one(selector)
            if link and link.get("href"):
                break
        except Exception:
            continue

    href = link.get("href") if link and link.get("href") else ""
    return urljoin(request_url, href)


def _parse_mitra10_dom(soup, request_url: str, seen: set) -> list[dict]:
    """Parse Mitra10 DOM-based product containers with generic fallback."""
    containers = _find_mitra10_containers(soup)
    return _process_mitra10_containers(containers, request_url, seen)


def _find_mitra10_containers(soup):
    """Find product containers in Mitra10 DOM."""
    # Try specific selectors first
    containers = _try_specific_mitra10_containers(soup)
    if containers:
        return containers

    # If no specific containers found, try generic approach
    return _try_generic_mitra10_containers(soup)


def _try_specific_mitra10_containers(soup):
    """Try to find containers using specific Mitra10 selectors."""
    specific_selectors = [
        "li.product-item",
        "div.product-item", 
        "div.product-item-info",
        "[data-product-id]",
        "[data-product-sku]"
    ]

    for selector in specific_selectors:
        try:
            test_containers = soup.select(selector)
            if test_containers:
                return test_containers
        except Exception:
            continue
    return []


def _try_generic_mitra10_containers(soup):
    """Try to find containers using generic approach."""
    containers = []
    all_elements = soup.find_all(["div", "li", "article", "section"])

    for elem in all_elements:
        if _is_valid_mitra10_container(elem):
            containers.append(elem)
            # Limit to avoid too many false positives
            if len(containers) >= 50:
                break

    return containers


def _is_valid_mitra10_container(elem) -> bool:
    """Check if element is a valid product container."""
    elem_text = elem.get_text(strip=True)

    # Skip if too small or too large
    if len(elem_text) < 10 or len(elem_text) > 1000:
        return False

    # Must have a link
    if not elem.find_all("a", href=True):
        return False

    # Must have price-like content
    price_indicators = ["rp", "idr", "price", "harga"]
    return any(indicator in elem_text.lower() for indicator in price_indicators)


def _process_mitra10_containers(containers, request_url: str, seen: set) -> list[dict]:
    """Process found containers and extract product data."""
    out = []

    for container in containers:
        product_data = _extract_mitra10_product_data(container, request_url)
        if not product_data:
            continue

        key = product_data["url"] or (product_data["item"], product_data["value"])
        if key in seen:
            continue
        seen.add(key)

        out.append(product_data)

    return out


def _extract_mitra10_product_data(container, request_url: str) -> dict | None:
    """Extract product data from a single container."""
    name = _extract_mitra10_product_name(container)
    if not name:
        return None

    full_url = _extract_mitra10_product_url(container, request_url)
    price = _extract_price_from_node(container)

    if price <= 0:
        return None

    # Extract unit from product name first (faster)
    unit = _extract_mitra10_product_unit_from_name(name)
    
    # If no unit found from name, try extracting from detail page
    if not unit and full_url:
        unit = _extract_mitra10_product_unit(full_url)

    return {"item": name, "value": price, "unit": unit, "source": MITRA10_SOURCE, "url": full_url}


def _parse_mitra10_html(html: str, request_url: str) -> list[dict]:
    """
    Robust Mitra10 parser:
      A) JSON-LD (if present)
      B) DOM cards with broader selectors (Magento/MUI/React variants)
    """
    if not html:
        return []

    soup = BeautifulSoup(html, HTML_PARSER)
    seen = set()

    # Try JSON-LD first
    out = _parse_mitra10_jsonld(soup, request_url, seen)
    if out:
        return out  # JSON-LD was enough

    # Fallback to DOM parsing
    return _parse_mitra10_dom(soup, request_url, seen)


def _mitra10_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    """
    Enhanced Mitra10 fallback with better handling for JavaScript-heavy sites:
    1) Try simple GET request first
    2) If no products found, try Playwright with JavaScript rendering
    3) Try alternative URL patterns
    """
    try:
        # First attempt: Simple URL
        prods, url, html_len = _try_simple_mitra10_url(keyword)
        if prods:
            return prods, url, html_len

        # Second attempt: Try with Playwright if available
        prods, url, html_len = _try_playwright_mitra10(keyword, url)
        if prods:
            return prods, url, html_len

        # Third attempt: Try complex URL
        prods, url, html_len = _try_complex_mitra10_url(keyword, sort_by_price, page, url)
        if prods:
            return prods, url, html_len

        # Fourth attempt: Try alternative URLs
        prods, url, html_len = _try_alternative_mitra10_urls(keyword)
        if prods:
            return prods, url, html_len

        # Return the best attempt we made
        return [], url, html_len
    except Exception:
        return [], "", 0


def _try_simple_mitra10_url(keyword: str):
    """Try simple Mitra10 URL without complex parameters."""
    simple_url = f"https://www.mitra10.com/catalogsearch/result?q={keyword}"
    html1 = _human_get(simple_url)
    prods1 = _parse_mitra10_html(html1, simple_url)
    return prods1, simple_url, len(html1)


def _try_playwright_mitra10(keyword: str, fallback_url: str):
    """Try Mitra10 with Playwright for JavaScript rendering."""
    if not HAS_PLAYWRIGHT:
        return [], fallback_url, 0

    simple_url = f"https://www.mitra10.com/catalogsearch/result?q={keyword}"
    html_js = _fetch_with_playwright(simple_url, wait_selector="div", timeout_ms=15000)

    if html_js and len(html_js) > len(_human_get(simple_url)):  # Got more content with JS
        prods_js = _parse_mitra10_html(html_js, simple_url)
        if prods_js:
            return prods_js, simple_url, len(html_js)

    return [], fallback_url, 0


def _try_complex_mitra10_url(keyword: str, sort_by_price: bool, page: int, fallback_url: str):
    """Try Mitra10 with complex URL builder."""
    urlb = Mitra10UrlBuilder()
    url1 = _build_url_defensively(urlb, keyword, sort_by_price, page)
    simple_url = f"https://www.mitra10.com/catalogsearch/result?q={keyword}"

    if url1 != simple_url:  # Only if different from simple URL
        html2 = _human_get(url1)
        prods2 = _parse_mitra10_html(html2, url1)
        if prods2:
            return prods2, url1, len(html2)

    return [], fallback_url, 0


def _try_alternative_mitra10_urls(keyword: str):
    """Try alternative Mitra10 search URL patterns."""
    alt_urls = [
        f"https://www.mitra10.com/search?q={keyword}",
        f"https://www.mitra10.com/catalog/search/?q={keyword}",
    ]

    for alt_url in alt_urls:
        try:
            html_alt = _human_get(alt_url)
            prods_alt = _parse_mitra10_html(html_alt, alt_url)
            if prods_alt:
                return prods_alt, alt_url, len(html_alt)
        except Exception:
            continue

    return [], "", 0


# ---------------- Tokopedia helpers + fallback ----------------
def _extract_tokopedia_product_unit(url: str) -> str:
    """Extract product unit from Tokopedia product detail page."""
    try:
        if not url:
            return ""

        # Handle relative URLs
        if url.startswith('/'):
            url = f"https://www.tokopedia.com{url}"

        # Fetch product detail page
        html = _human_get(url)
        if not html:
            return ""

        # Use Tokopedia's unit parser to extract unit from detail page
        unit_parser = TokopediaUnitParser()

        # Try to extract unit from the detail page HTML
        unit = unit_parser.parse_unit(html)
        return unit or ""

    except Exception:
        return ""


def _extract_tokopedia_product_unit_from_name(name: str) -> str:
    """Extract product unit from Tokopedia product name."""
    try:
        if not name:
            return ""

        # Use Tokopedia's unit parser to extract unit from product name
        unit_parser = TokopediaUnitParser()

        # Try to extract unit from the product name
        unit = unit_parser._extract_unit_from_name(name)
        return unit or ""

    except Exception:
        return ""


def _extract_tokopedia_product_location(card) -> str:
    """Extract product location from Tokopedia product card using location scraper."""
    try:
        if not card:
            return ""

        # Use Tokopedia's location scraper to extract location from product item
        location_scraper = TokopediaLocationScraper()
        location = location_scraper.extract_location_from_product_item(card)
        return location or ""

    except Exception:
        return ""


def _extract_tokopedia_product_name(card) -> str | None:
    """Extract product name from Tokopedia card."""
    # Try primary selector
    name = _try_primary_tokopedia_name(card)
    if name:
        return name

    # Try fallback selectors
    name = _try_fallback_tokopedia_name(card)
    if name:
        return name

    # Try image alt text
    return _try_tokopedia_image_alt(card)


def _try_primary_tokopedia_name(card) -> str | None:
    """Try primary Tokopedia name selector."""
    for sel in ['span.css-20kt3o', 'span[data-testid="lblProductName"]', '.css-20kt3o']:
        el = card.select_one(sel)
        if el and el.get_text(strip=True):
            return _clean_text(el.get_text(" ", strip=True))
    return None


def _try_fallback_tokopedia_name(card) -> str | None:
    """Try fallback Tokopedia name selectors."""
    for sel in ['div[data-testid="divProductWrapper"] span', 'span', 'h3', 'h2', 'h1']:
        el = card.select_one(sel)
        if el and el.get_text(strip=True):
            text = _clean_text(el.get_text(" ", strip=True))
            # Skip if it looks like a price
            if not text.startswith(('Rp', 'IDR', 'rp', 'idr')) and len(text) > 3:
                return text
    return None


def _try_tokopedia_image_alt(card) -> str | None:
    """Try extracting name from image alt text."""
    img = card.find("img")
    if img and img.get("alt"):
        alt_text = _clean_text(img["alt"])
        if len(alt_text) > 3 and not alt_text.startswith(('Rp', 'IDR')):
            return alt_text
    return None


def _extract_tokopedia_product_price(card) -> int:
    """Extract product price from Tokopedia card."""
    # Try primary price selector
    price = _try_primary_tokopedia_price(card)
    if price > 0:
        return price

    # Try secondary price selectors
    price = _try_secondary_tokopedia_price(card)
    if price > 0:
        return price

    # Try currency text fallback
    return _try_currency_text_tokopedia_price(card)


def _try_primary_tokopedia_price(card) -> int:
    """Try primary Tokopedia price selector."""
    for sel in ['span.css-o5uqv', 'span[data-testid="lblProductPrice"]', '.css-o5uqv']:
        el = card.select_one(sel)
        if el:
            price_text = el.get_text(" ", strip=True)
            # Use Tokopedia price cleaning logic
            clean_price = _clean_tokopedia_price(price_text)
            if clean_price > 0:
                return clean_price
    return 0


def _try_secondary_tokopedia_price(card) -> int:
    """Try secondary Tokopedia price selectors."""
    for sel in ['span', 'div', 'p']:
        elements = card.select(sel)
        for el in elements:
            text = el.get_text(" ", strip=True)
            if 'Rp' in text or 'IDR' in text:
                clean_price = _clean_tokopedia_price(text)
                if clean_price > 0:
                    return clean_price
    return 0


def _try_currency_text_tokopedia_price(card) -> int:
    """Try extracting price from currency text in Tokopedia card."""
    for t in card.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
        clean_price = _clean_tokopedia_price(str(t).strip())
        if clean_price > 0:
            return clean_price
    return 0


def _clean_tokopedia_price(price_text: str) -> int:
    """Clean Tokopedia price string and convert to integer."""
    if not price_text:
        return 0

    try:
        # Remove whitespace and normalize
        price_text = price_text.strip()

        # Extract price using regex (Tokopedia format: Rp62.500)
        import re
        price_pattern = re.compile(r'Rp\s*([\d,\.]+)', re.IGNORECASE)
        match = price_pattern.search(price_text)

        if not match:
            # Fallback: try to extract just numbers
            number_pattern = re.compile(r'[\d,\.]+')
            number_match = number_pattern.search(price_text)
            if not number_match:
                return 0
            price_text = number_match.group()
        else:
            price_text = match.group(1)

        # Remove separators and convert to integer
        # Tokopedia uses dots as thousand separators
        clean_price = price_text.replace(',', '').replace('.', '')

        # Convert to integer
        return int(clean_price)

    except (ValueError, AttributeError):
        return 0


def _extract_tokopedia_product_link(card) -> str:
    """Extract product link from Tokopedia card."""
    # Try primary link selector
    link = card.select_one('a[data-testid="lnkProductContainer"]')
    if link and link.get("href"):
        return link.get("href")

    # Try fallback link selectors
    for sel in ['a[href*="/p/"]', 'a[href*="/product/"]', HREF_SELECTOR]:
        link = card.select_one(sel)
        if link and link.get("href"):
            return link.get("href")

    return "https://www.tokopedia.com/p/pertukangan/material-bangunan"


def _tokopedia_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    """
    Tokopedia fallback: Only use HTTP-based scraping, do not use Playwright.
    1) Try simple GET request first
    2) Try alternative URL patterns if no products found
    """
    try:
        # First attempt: Simple URL
        prods, url, html_len = _try_simple_tokopedia_url(keyword, sort_by_price, page)
        if prods:
            return prods, url, html_len

        # Second attempt: Try alternative URLs
        prods, url, html_len = _try_alternative_tokopedia_urls(keyword)
        if prods:
            return prods, url, html_len

        # Return empty if nothing found
        return [], url, html_len
    except Exception:
        return [], "", 0


def _try_simple_tokopedia_url(keyword: str, sort_by_price: bool = True, page: int = 0):
    """Try simple Tokopedia URL without complex parameters."""
    url = _build_url_defensively(TokopediaUrlBuilder(), keyword, sort_by_price, page)
    html = _human_get(url)
    prods = _parse_tokopedia_html(html)
    return prods, url, len(html)




def _try_alternative_tokopedia_urls(keyword: str):
    """Try alternative Tokopedia search URL patterns."""
    alt_urls = [
        f"https://www.tokopedia.com/search?st=product&q={keyword}",
        f"https://www.tokopedia.com/p/pertukangan/material-bangunan?q={keyword}",
    ]

    for alt_url in alt_urls:
        try:
            html_alt = _human_get(alt_url)
            prods_alt = _parse_tokopedia_html(html_alt)
            if prods_alt:
                return prods_alt, alt_url, len(html_alt)
        except Exception:
            continue

    return [], "", 0


def _parse_tokopedia_html(html: str) -> list[dict]:
    """
    Parse Tokopedia HTML and extract product data.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, HTML_PARSER)

    # Find product cards with multiple selectors
    cards = soup.select('a[data-testid="lnkProductContainer"]') or \
            soup.select('div[data-testid="divProductWrapper"]') or \
            soup.select('div.css-bk6tzz') or \
            soup.select('div[data-unify="Card"]')

    out = []
    for card in cards:
        name = _extract_tokopedia_product_name(card)
        if not name:
            continue

        price = _extract_tokopedia_product_price(card)
        if price <= 0:
            continue

        href = _extract_tokopedia_product_link(card)

        # Extract location from product card
        location = _extract_tokopedia_product_location(card)

        # Extract unit from product name first (faster)
        unit = _extract_tokopedia_product_unit_from_name(name)

        # If no unit found from name, try extracting from detail page
        if not unit and href:
            unit = _extract_tokopedia_product_unit(href)

        out.append({
            "item": name, 
            "value": price, 
            "unit": unit,
            "location": location,
            "source": TOKOPEDIA_SOURCE, 
            "url": href
        })

    return out


# ---------------- generic runners ----------------
def _handle_successful_scrape(request, res, label: str, url: str, html_len: int) -> list[dict]:
    """Handle successful scrape results."""
    rows = []
    for p in res.products:
        # Include unit and location when available
        unit = getattr(p, "unit", None)
        location = getattr(p, "location", None)

        product_data = {
            "item": p.name,
            "value": p.price,
            "unit": unit,
            "source": label,
            "url": getattr(p, "url", "")
        }

        # Add location if available
        if location:
            product_data["location"] = location

        rows.append(product_data)
    messages.info(request, f"[{label}] URL: {url} | HTML: {html_len} bytes | parsed={len(rows)}")
    return rows


def _handle_fallback_scrape(request, keyword: str, label: str, fallback, url: str, html_len: int) -> list[dict]:
    """Handle fallback scrape when primary scrape fails."""
    fb_rows, fb_url, fb_len = fallback(keyword, sort_by_price=True, page=0)
    if fb_rows:
        messages.info(request, f"[{label}] Fallback URL: {fb_url} | HTML: {fb_len} bytes | parsed={len(fb_rows)}")
        return fb_rows
    else:
        hint = _get_bot_challenge_hint(url)
        messages.warning(
            request,
            f"[{label}] Package returned no products; fallback also found none{hint}. "
            f"URL: {url} | HTML: {html_len} bytes"
        )
        return []


def _get_bot_challenge_hint(url: str) -> str:
    """Check if URL shows bot challenge and return hint."""
    try:
        html_preview = _human_get(url, tries=1)
        if _looks_like_bot_challenge(html_preview):
            return " (bot-challenge detected)"
    except Exception:
        pass
    return ""


def _run_vendor_to_prices(request, keyword: str, maker, label: str, fallback=None, limit: int | None = None) -> list[dict]:
    try:
        return _execute_vendor_scraping(request, keyword, maker, label, fallback, limit=limit)
    except Exception as e:
        return _handle_vendor_scraping_exception(request, keyword, label, fallback, e)


def _execute_vendor_scraping(request, keyword: str, maker, label: str, fallback, limit: int | None = None) -> list[dict]:
    """Execute the main vendor scraping logic."""
    scraper, urlb = maker()
    url = _build_url_defensively(urlb, keyword, sort_by_price=True, page=0)
    html_len = _fetch_len(url)

    # Handle BatchPlaywrightClient context manager issue
    # Pass vendor-specific limit (e.g., Tokopedia) when provided
    res = _safe_scrape_products(scraper, keyword, sort_by_price=True, page=0, limit=limit)

    if getattr(res, "success", False) and getattr(res, "products", None):
        return _handle_successful_scrape(request, res, label, url, html_len)

    if fallback:
        return _handle_fallback_scrape(request, keyword, label, fallback, url, html_len)
    else:
        messages.warning(request, f"[{label}] {getattr(res, 'error_message', 'No products parsed')}")
        return []


def _handle_vendor_scraping_exception(request, keyword: str, label: str, fallback, error: Exception) -> list[dict]:
    """Handle exceptions during vendor scraping."""
    error_msg = str(error)
    if CONTEXT_MANAGER_ERROR in error_msg.lower() or "batchplaywrightclient" in error_msg:
        messages.info(request, f"[{label}] Switching to alternative data source")
        if fallback:
            return _handle_fallback_scrape(request, keyword, label, fallback, "", 0)
        return []
    else:
        messages.error(request, f"[{label}] Scraper error: {error}")
        return []


def _safe_scrape_products(scraper, keyword: str, sort_by_price: bool = True, page: int = 0, limit: int | None = None):
    """
    Safely handle scraping with proper context manager usage for BatchPlaywrightClient-based scrapers.
    """
    from api.playwright_client import BatchPlaywrightClient

    # Check if this scraper uses BatchPlaywrightClient
    if hasattr(scraper, 'http_client') and isinstance(scraper.http_client, BatchPlaywrightClient):
        return _handle_playwright_scraper(scraper, keyword, sort_by_price, page, limit=limit)
    else:
        # For regular HTTP client scrapers, use normal method
        # If the scraper supports a 'limit' parameter, pass it through
        try:
            return scraper.scrape_products(keyword=keyword, sort_by_price=sort_by_price, page=page, limit=limit)
        except TypeError:
            return scraper.scrape_products(keyword=keyword, sort_by_price=sort_by_price, page=page)


def _handle_playwright_scraper(scraper, keyword: str, sort_by_price: bool, page: int, limit: int | None = None):
    """Handle scraping for BatchPlaywrightClient-based scrapers."""
    from api.playwright_client import BatchPlaywrightClient
    from api.interfaces import ScrapingResult

    try:
        # Try to use scrape_batch method if available (like Mitra10)
        if hasattr(scraper, 'scrape_batch'):
            # If limit is provided and scrape_batch supports batching, attempt to collect up to limit
            if limit and hasattr(scraper, 'scrape_batch'):
                # scrape_batch takes a list of keywords; for a single keyword we may need paging inside the scraper
                products = scraper.scrape_batch([keyword])
                # If scrape_batch returned fewer than limit, and the scraper supports paginate via scrape_products, attempt to fetch more
                if len(products) < limit and hasattr(scraper, 'scrape_products'):
                    try:
                        extra_res = scraper.scrape_products(keyword=keyword, sort_by_price=sort_by_price, page=1, limit=limit - len(products))
                        if getattr(extra_res, 'success', False) and getattr(extra_res, 'products', None):
                            products.extend(extra_res.products)
                    except TypeError:
                        pass
            else:
                products = scraper.scrape_batch([keyword])
            return ScrapingResult(products=products, success=True, url="")
        else:
            return _handle_playwright_scraper_fallback(scraper, keyword, sort_by_price, page)
    except Exception as e:
        return ScrapingResult(products=[], success=False, error_message=str(e))


def _handle_playwright_scraper_fallback(scraper, keyword: str, sort_by_price: bool, page: int):
    """Fallback handling for Playwright scrapers without scrape_batch."""
    from api.playwright_client import BatchPlaywrightClient

    # Fallback: recreate scraper with context manager
    with BatchPlaywrightClient() as batch_client:
        # Temporarily replace the http_client
        original_client = scraper.http_client
        scraper.http_client = batch_client
        result = scraper.scrape_products(keyword=keyword, sort_by_price=sort_by_price, page=page)
        scraper.http_client = original_client  # Restore original
        return result


def _run_vendor_to_count(request, keyword: str, maker, label: str, fallback=None) -> int:
    try:
        scraper, urlb = maker()
        url = _build_url_defensively(urlb, keyword, sort_by_price=True, page=0)
        res = scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)

        if getattr(res, "success", False) and getattr(res, "products", None):
            count = len(res.products)
            messages.info(request, f"[{label}] URL: {url} | parsed={count}")
            return count

        if fallback:
            fb_rows, fb_url, _ = fallback(keyword, sort_by_price=True, page=0)
            if fb_rows:
                messages.info(request, f"[{label}] Fallback URL: {fb_url} | parsed={len(fb_rows)}")
                return len(fb_rows)
        messages.warning(request, f"[{label}] {getattr(res, 'error_message', 'parse failed')}")
    except Exception as e:
        messages.error(request, f"[{label}] error: {e}")
    return 0


def _run_location_scraper(request, scraper_func, label: str) -> list[dict]:
    """Helper function to run location scraping and return formatted locations."""
    try:
        return _execute_location_scraping(request, scraper_func, label)
    except Exception as e:
        return _handle_location_scraping_exception(request, label, e)


def _execute_location_scraping(request, scraper_func, label: str) -> list[dict]:
    """Execute the main location scraping logic."""
    scraper = scraper_func()

    # Try the expected interface method first
    if hasattr(scraper, 'scrape_locations_batch'):
        result = scraper.scrape_locations_batch()
    # Fallback to the actual implemented method
    elif hasattr(scraper, 'scrape_locations'):
        result = scraper.scrape_locations()
    else:
        messages.error(request, f"[{label}] No valid scrape method found")
        return []

    if getattr(result, "success", False) and getattr(result, "locations", None):
        return _format_location_results(result.locations, label)
    else:
        error_msg = getattr(result, "error_message", UNKNOWN_ERROR_MSG)
        messages.warning(request, f"[{label}] Location scraping failed: {error_msg}")
        return []


def _format_location_results(locations, label: str) -> list[dict]:
    """Format location results into standardized format."""
    formatted_locations = []
    for i, loc in enumerate(locations):
        # Support both name/code and store_name/address patterns
        store_name = getattr(loc, 'store_name', None) or getattr(loc, 'name', '')
        address = getattr(loc, 'address', None) or getattr(loc, 'code', '')
        
        formatted_locations.append({
            "store_name": store_name,
            "address": address,
            "source": label
        })
    return formatted_locations


def _handle_location_scraping_exception(request, label: str, error: Exception) -> list[dict]:
    """Handle exceptions during location scraping."""
    error_msg = str(error)
    # Handle abstract class instantiation errors by using fallback locations
    if "abstract class" in error_msg and "abstract method" in error_msg:
        messages.info(request, f"[{label}] Using stored location data (live location service unavailable)")
        return _get_fallback_locations_by_source(label)
    else:
        messages.warning(request, f"[{label}] Cannot load live locations, using stored locations")
        return _get_fallback_locations_by_source(label)


def _get_fallback_locations_by_source(label: str) -> list[dict]:
    """Get fallback locations based on the source label."""
    if label == GEMILANG_SOURCE:
        return _get_gemilang_fallback_locations()
    elif label == DEPO_BANGUNAN_SOURCE:
        return _get_depo_fallback_locations()
    else:
        return []


def _get_gemilang_fallback_locations() -> list[dict]:
    """Get fallback Gemilang location data when live scraping fails."""
    fallback_locations = [
        {"name": "Gemilang Store Jakarta Pusat", "address": "Jakarta Pusat, DKI Jakarta"},
        {"name": "Gemilang Store Jakarta Selatan", "address": "Jakarta Selatan, DKI Jakarta"},
        {"name": "Gemilang Store Jakarta Timur", "address": "Jakarta Timur, DKI Jakarta"},
        {"name": "Gemilang Store Jakarta Barat", "address": "Jakarta Barat, DKI Jakarta"},
        {"name": "Gemilang Store Jakarta Utara", "address": "Jakarta Utara, DKI Jakarta"},
        {"name": "Gemilang Store Bekasi", "address": "Bekasi, Jawa Barat"},
        {"name": "Gemilang Store Depok", "address": "Depok, Jawa Barat"},
        {"name": "Gemilang Store Tangerang", "address": "Tangerang, Banten"},
    ]

    locations = []
    for loc_data in fallback_locations:
        locations.append({
            "store_name": loc_data["name"],
            "address": loc_data["address"],
            "source": GEMILANG_SOURCE
        })
    return locations


def _get_depo_fallback_locations() -> list[dict]:
    """Get fallback Depo Bangunan location data when live scraping fails."""
    fallback_locations = [
        {"name": "Depo Bangunan Jakarta", "address": "Jakarta, DKI Jakarta"},
        {"name": "Depo Bangunan Bandung", "address": "Bandung, Jawa Barat"},
        {"name": "Depo Bangunan Surabaya", "address": "Surabaya, Jawa Timur"},
        {"name": "Depo Bangunan Semarang", "address": "Semarang, Jawa Tengah"},
        {"name": "Depo Bangunan Medan", "address": "Medan, Sumatera Utara"},
        {"name": "Depo Bangunan Makassar", "address": "Makassar, Sulawesi Selatan"},
        {"name": "Depo Bangunan Denpasar", "address": "Denpasar, Bali"},
    ]

    locations = []
    for loc_data in fallback_locations:
        locations.append({
            "store_name": loc_data["name"],
            "address": loc_data["address"],
            "source": DEPO_BANGUNAN_SOURCE
        })
    return locations


def _run_mitra10_location_scraper(request) -> list[dict]:
    """Helper function to run Mitra10 location scraping and return formatted locations."""
    try:
        return _execute_mitra10_location_scraping(request)
    except Exception as e:
        return _handle_mitra10_scraping_exception(request, e)


def _execute_mitra10_location_scraping(request) -> list[dict]:
    """Execute Mitra10 location scraping logic."""
    scraper = create_mitra10_location_scraper()
    result = scraper.scrape_locations()

    # Handle dictionary response (Mitra10 returns a dict, not an object)
    if isinstance(result, dict) and result.get("success", False) and result.get("locations"):
        return _format_mitra10_locations(result["locations"])
    else:
        return _handle_mitra10_scraping_failure(request, result)


def _format_mitra10_locations(location_names: list) -> list[dict]:
    """Format Mitra10 location names into standardized format."""
    locations = []
    for location_name in location_names:
        # Mitra10 location scraper returns location names as strings
        # Convert them to the expected format
        locations.append({
            "store_name": f"Mitra10 {location_name}",
            "address": location_name,
            "source": MITRA10_SOURCE
        })
    return locations


def _handle_mitra10_scraping_failure(request, result) -> list[dict]:
    """Handle failed Mitra10 scraping with appropriate error messages."""
    error_msg = result.get("error_message", UNKNOWN_ERROR_MSG) if isinstance(result, dict) else UNKNOWN_ERROR_MSG

    # Handle specific error types with appropriate fallbacks
    if "timeout" in error_msg.lower() or "exceeded" in error_msg.lower():
        messages.warning(request, f"[{MITRA10_SOURCE}] Website loading slowly, using cached locations")
    elif CONTEXT_MANAGER_ERROR in error_msg.lower() or "batchplaywrightclient" in error_msg.lower():
        messages.warning(request, f"[{MITRA10_SOURCE}] Browser connection issue, using cached locations")
    else:
        messages.warning(request, f"[{MITRA10_SOURCE}] Cannot load live locations, using cached locations")

    return _get_mitra10_fallback_locations()


def _handle_mitra10_scraping_exception(request, error: Exception) -> list[dict]:
    """Handle exceptions during Mitra10 location scraping."""
    error_str = str(error)
    error_keywords = ["timeout", "exceeded", CONTEXT_MANAGER_ERROR, "batchplaywrightclient"]

    # Handle specific error types with appropriate fallbacks
    if any(keyword in error_str.lower() for keyword in error_keywords):
        messages.warning(request, f"[{MITRA10_SOURCE}] Connection issue, using cached locations")
    else:
        messages.warning(request, f"[{MITRA10_SOURCE}] Cannot load live locations, using cached locations")

    return _get_mitra10_fallback_locations()


def _get_mitra10_fallback_locations() -> list[dict]:
    """Get fallback Mitra10 location data when live scraping fails."""
    fallback_locations = [
        "Kemayoran",
        "Kelapa Gading",
        "Ciputat", 
        "Serpong",
        "Cibinong",
        "Depok",
        "Bekasi",
        "Karawang",
        "Bandung",
        "Semarang",
        "Surabaya",
        "Makassar"
    ]

    locations = []
    for location_name in fallback_locations:
        locations.append({
            "store_name": f"Mitra10 {location_name}",
            "address": location_name,
            "source": MITRA10_SOURCE
        })
    return locations


# ---------------- helper functions for home view ----------------
def _scrape_all_vendors(request, keyword: str) -> list[dict]:
    """Scrape prices from all vendors."""
    prices = []
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_gemilang_scraper(), GemilangUrlBuilder())), GEMILANG_SOURCE)
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_depo_scraper(), DepoUrlBuilder())), DEPO_BANGUNAN_SOURCE, _depo_fallback)
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_juraganmaterial_scraper(), JuraganMaterialUrlBuilder())), JURAGAN_MATERIAL_SOURCE, _juragan_fallback)
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_mitra10_scraper(), Mitra10UrlBuilder())), MITRA10_SOURCE, _mitra10_fallback)
    # Request 20 items from Tokopedia (default was showing 5)
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_tokopedia_scraper(), TokopediaUrlBuilder())), TOKOPEDIA_SOURCE, _tokopedia_fallback, limit=20)
    return prices


def _collect_vendor_locations(request, prices: list[dict]) -> dict:
    """Collect location data for vendors that have prices."""
    locations_data = {}

    # Gemilang locations
    gemilang_has_prices = any(p.get("source") == GEMILANG_SOURCE for p in prices)
    if gemilang_has_prices:
        gemilang_locations = _run_location_scraper(request, create_gemilang_location_scraper, GEMILANG_SOURCE)
        if gemilang_locations:
            locations_data[GEMILANG_SOURCE] = gemilang_locations

    # Depo Bangunan locations
    depo_has_prices = any(p.get("source") == DEPO_BANGUNAN_SOURCE for p in prices)
    if depo_has_prices:
        depo_locations = _run_location_scraper(request, create_depo_location_scraper, DEPO_BANGUNAN_SOURCE)
        if depo_locations:
            locations_data[DEPO_BANGUNAN_SOURCE] = depo_locations

    # Juragan Material locations
    juragan_has_prices = any(p.get("source") == JURAGAN_MATERIAL_SOURCE for p in prices)
    if juragan_has_prices:
        juragan_locations = _get_juragan_material_locations(prices)
        if juragan_locations:
            locations_data[JURAGAN_MATERIAL_SOURCE] = juragan_locations

    # Mitra10 locations
    mitra10_has_prices = any(p.get("source") == MITRA10_SOURCE for p in prices)
    if mitra10_has_prices:
        mitra10_locations = _run_mitra10_location_scraper(request)
        if mitra10_locations:
            locations_data[MITRA10_SOURCE] = mitra10_locations

    # Tokopedia locations
    tokopedia_has_prices = any(p.get("source") == TOKOPEDIA_SOURCE for p in prices)
    if tokopedia_has_prices:
        tokopedia_locations = _get_tokopedia_locations()
        if tokopedia_locations:
            locations_data[TOKOPEDIA_SOURCE] = tokopedia_locations

    return locations_data


def _get_tokopedia_locations() -> list[dict]:
    """Get predefined Tokopedia location data."""
    tokopedia_locations = []
    for location_name, location_ids in TOKOPEDIA_LOCATION_IDS.items():
        # Format location name for display
        display_name = location_name.replace('_', ' ').title()
        tokopedia_locations.append({
            "store_name": f"Tokopedia {display_name}",
            "address": f"Area ID: {', '.join(map(str, location_ids))}",
            "source": TOKOPEDIA_SOURCE
        })
    return tokopedia_locations


def _get_juragan_material_locations(prices: list[dict]) -> list[dict]:
    """Get Juragan Material location data from product prices."""
    juragan_locations = []
    unique_locations = set()

    # Extract unique locations from Juragan Material products
    for price in prices:
        if price.get("source") == JURAGAN_MATERIAL_SOURCE:
            location = price.get("location")
            if location and location not in unique_locations:
                unique_locations.add(location)
                juragan_locations.append({
                    "store_name": f"Juragan Material - {location}",
                    "address": location,
                    "source": JURAGAN_MATERIAL_SOURCE
                })

    # If no locations found in products, provide fallback locations
    if not juragan_locations:
        juragan_locations = [
            {
                "store_name": "Juragan Material Jakarta Selatan",
                "address": "Jakarta Selatan, DKI Jakarta",
                "source": JURAGAN_MATERIAL_SOURCE
            },
            {
                "store_name": "Juragan Material Bandung",
                "address": "Bandung, Jawa Barat",
                "source": JURAGAN_MATERIAL_SOURCE
            },
            {
                "store_name": "Juragan Material Surabaya",
                "address": "Surabaya, Jawa Timur",
                "source": JURAGAN_MATERIAL_SOURCE
            }
        ]

    return juragan_locations


def _add_location_info_to_prices(prices: list[dict], locations_data: dict) -> list[dict]:
    """Add location information to price data."""
    for price in prices:
        vendor_locations = locations_data.get(price.get("source"), [])
        if vendor_locations:
            # Take the first location for display
            price["location"] = vendor_locations[0].get("store_name", "")
            price["location_count"] = len(vendor_locations)
            # Store all locations for modal display
            price["all_locations"] = [loc.get("store_name", "") for loc in vendor_locations]
        else:
            price["location"] = ""
            price["location_count"] = 0
            price["all_locations"] = []
    return prices


def _clean_and_dedupe_prices(prices: list[dict]) -> list[dict]:
    """Clean unrealistic prices and remove duplicates."""
    # Filter out unrealistic prices
    prices = [p for p in prices if p.get("value") and p["value"] >= 100]

    # Deduplicate
    uniq = {}
    for p in prices:
        k = (p.get("source"), p.get("url") or "", p.get("item"), p.get("value"))
        if k not in uniq:
            uniq[k] = p

    prices = list(uniq.values())

    # Sort by price
    try:
        prices.sort(key=lambda x: (x["value"] is None, x["value"]))
    except Exception:
        pass

    return prices


# ---------------- views ----------------
@require_GET
def home(request):
    keyword = request.GET.get("q", "semen")

    # Scrape prices from all vendors
    prices = _scrape_all_vendors(request, keyword)

    # Collect location data for vendors with prices
    locations_data = _collect_vendor_locations(request, prices)

    # Add location info to prices
    prices = _add_location_info_to_prices(prices, locations_data)

    # Clean and deduplicate prices
    prices = _clean_and_dedupe_prices(prices)

    return render(request, "dashboard/home.html", {"prices": prices})


@require_POST
def trigger_scrape(request):
    keyword = request.POST.get("q", "semen")
    counts = {
        "gemilang": _run_vendor_to_count(request, keyword, (lambda: (create_gemilang_scraper(), GemilangUrlBuilder())), GEMILANG_SOURCE),
        "depo": _run_vendor_to_count(request, keyword, (lambda: (create_depo_scraper(), DepoUrlBuilder())), DEPO_BANGUNAN_SOURCE, _depo_fallback),
        "juragan": _run_vendor_to_count(request, keyword, (lambda: (create_juraganmaterial_scraper(), JuraganMaterialUrlBuilder())), JURAGAN_MATERIAL_SOURCE, _juragan_fallback),
        "mitra10": _run_vendor_to_count(request, keyword, (lambda: (create_mitra10_scraper(), Mitra10UrlBuilder())), MITRA10_SOURCE, _mitra10_fallback),
        "tokopedia": _run_vendor_to_count(request, keyword, (lambda: (create_tokopedia_scraper(), TokopediaUrlBuilder())), TOKOPEDIA_SOURCE, _tokopedia_fallback),
    }
    messages.success(
        request,
        "Scrape completed. Gemilang={gemilang}, Depo={depo}, JuraganMaterial={juragan}, Mitra10={mitra}, Tokopedia={tokopedia}".format(
            gemilang=counts["gemilang"], depo=counts["depo"], juragan=counts["juragan"], mitra=counts["mitra10"], tokopedia=counts["tokopedia"]
        )
    )
    return redirect("home")


@require_GET
def curated_price_list(request):
    qs = models.ItemPriceProvince.objects.select_related("item_price", "province")
    return render(request, "dashboard/curated_price_list.html", {"rows": qs})


@require_GET
def curated_price_create(request):
    form = ItemPriceProvinceForm()
    return render(request, DASHBOARD_FORM_TEMPLATE, {
        "title": "New Curated Price", 
        "form": form,
        "form_action": reverse("curated_price_create_post")
    })


@csrf_protect
@require_POST
def curated_price_create_post(request):
    form = ItemPriceProvinceForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Curated price saved")
        return redirect("curated_price_list")
    return render(request, DASHBOARD_FORM_TEMPLATE, {"title": "New Curated Price", "form": form})


@require_GET
def curated_price_update(request, pk):
    obj = get_object_or_404(models.ItemPriceProvince, pk=pk)
    form = ItemPriceProvinceForm(instance=obj)
    return render(request, DASHBOARD_FORM_TEMPLATE, {
        "title": "Edit Curated Price", 
        "form": form,
        "form_action": reverse("curated_price_update_post", args=[pk])
    })


@csrf_protect
@require_POST
def curated_price_update_post(request, pk):
    obj = get_object_or_404(models.ItemPriceProvince, pk=pk)
    form = ItemPriceProvinceForm(request.POST, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Curated price updated")
        return redirect("curated_price_list")
    return render(request, DASHBOARD_FORM_TEMPLATE, {"title": "Edit Curated Price", "form": form})


@require_GET
def curated_price_delete(request, pk):
    obj = get_object_or_404(models.ItemPriceProvince, pk=pk)
    return render(request, "dashboard/confirm_delete.html", {
        "title": "Delete Curated Price", 
        "obj": obj,
        "form_action": reverse("curated_price_delete_post", args=[pk])
    })


@csrf_protect
@require_POST
def curated_price_delete_post(request, pk):
    obj = get_object_or_404(models.ItemPriceProvince, pk=pk)
    obj.delete()
    messages.success(request, "Curated price deleted")
    return redirect("curated_price_list")


@require_POST
def curated_price_from_scrape(request):
    initial = {
        "price": request.POST.get("value") or None,
        "source": request.POST.get("source") or "",
        "url": request.POST.get("url") or "",
    }
    form = ItemPriceProvinceForm(initial=initial)
    return render(request, DASHBOARD_FORM_TEMPLATE, {
        "title": "Save Price from Scrape", 
        "form": form,
        "form_action": reverse("curated_price_create_post")
    })