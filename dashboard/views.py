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

from api.depobangunan.factory import create_depo_scraper
from api.depobangunan.url_builder import DepoUrlBuilder

from api.juragan_material.factory import create_juraganmaterial_scraper
from api.juragan_material.url_builder import JuraganMaterialUrlBuilder

from api.mitra10.factory import create_mitra10_scraper
from api.mitra10.url_builder import Mitra10UrlBuilder

from api.tokopedia.factory import create_tokopedia_scraper
from api.tokopedia.url_builder import TokopediaUrlBuilder

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
JURAGAN_MATERIAL_SOURCE = "Juragan Material"
MITRA10_SOURCE = "Mitra10"
TOKOPEDIA_SOURCE = "Tokopedia"
DASHBOARD_FORM_TEMPLATE = "dashboard/form.html"
JSON_LD_TYPE_KEY = "@type"
HTML_PARSER = "html.parser"


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
    for sel in ("a p.product-name", "p.product-name", ".product-name", "[class*=name]"):
        el = card.select_one(sel)
        if el and el.get_text(strip=True):
            return _clean_text(el.get_text(" ", strip=True))
    
    img = card.find("img")
    if img and img.get("alt"):
        return _clean_text(img["alt"])
    
    return None


def _extract_juragan_product_link(card) -> str:
    """Extract product link from Juragan Material card."""
    link = card.select_one("a:has(p.product-name)") or card.select_one("a[href]")
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

            out.append({"item": name, "value": price, "source": JURAGAN_MATERIAL_SOURCE, "url": href})
        
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
        out.append({"item": _clean_text(name), "value": price_val, "source": MITRA10_SOURCE, "url": full_url})

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
        ".product-name",
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
        "a[href]"
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

    return {"item": name, "value": price, "source": MITRA10_SOURCE, "url": full_url}


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
    for sel in ['a[href*="/p/"]', 'a[href*="/product/"]', 'a[href]']:
        link = card.select_one(sel)
        if link and link.get("href"):
            return link.get("href")
    
    return "https://www.tokopedia.com/p/pertukangan/material-bangunan"


def _tokopedia_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    """
    Tokopedia fallback using simple HTML parsing when the main scraper fails.
    """
    try:
        url = _build_url_defensively(TokopediaUrlBuilder(), keyword, sort_by_price, page)
        html = _human_get(url)
        soup = BeautifulSoup(html, HTML_PARSER)

        # Find product cards
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
            
            out.append({"item": name, "value": price, "source": TOKOPEDIA_SOURCE, "url": href})
        
        return out, url, len(html)
    except Exception:
        return [], "", 0


# ---------------- generic runners ----------------
def _handle_successful_scrape(request, res, label: str, url: str, html_len: int) -> list[dict]:
    """Handle successful scrape results."""
    rows = []
    for p in res.products:
        # Include unit when available (Gemilang parser provides Product.unit)
        unit = getattr(p, "unit", None)
        rows.append({
            "item": p.name,
            "value": p.price,
            "unit": unit,
            "source": label,
            "url": getattr(p, "url", "")
        })
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


def _run_vendor_to_prices(request, keyword: str, maker, label: str, fallback=None) -> list[dict]:
    try:
        scraper, urlb = maker()
        url = _build_url_defensively(urlb, keyword, sort_by_price=True, page=0)
        html_len = _fetch_len(url)
        res = scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)

        if getattr(res, "success", False) and getattr(res, "products", None):
            return _handle_successful_scrape(request, res, label, url, html_len)
        
        if fallback:
            return _handle_fallback_scrape(request, keyword, label, fallback, url, html_len)
        else:
            messages.warning(request, f"[{label}] {getattr(res, 'error_message', 'No products parsed')}")
            return []
            
    except Exception as e:
        messages.error(request, f"[{label}] Scraper error: {e}")
        return []


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
        scraper = scraper_func()
        result = scraper.scrape_locations()
        

        if getattr(result, "success", False) and getattr(result, "locations", None):
            locations = []
            for i, loc in enumerate(result.locations):
                locations.append({
                    "store_name": loc.store_name,
                    "address": loc.address,
                    "source": label
                })
            return locations
        else:
            error_msg = getattr(result, "error_message", "Unknown error")
            messages.warning(request, f"[{label}] Location scraping failed: {error_msg}")
            return []
    except Exception as e:
        messages.error(request, f"[{label}] Location scraping error: {e}")
        return []


# ---------------- views ----------------
def home(request):
    keyword = request.GET.get("q", "semen")
    prices = []
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_gemilang_scraper(), GemilangUrlBuilder())), GEMILANG_SOURCE)
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_depo_scraper(), DepoUrlBuilder())), "Depo Bangunan")
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_juraganmaterial_scraper(), JuraganMaterialUrlBuilder())), JURAGAN_MATERIAL_SOURCE, _juragan_fallback)
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_mitra10_scraper(), Mitra10UrlBuilder())), MITRA10_SOURCE, _mitra10_fallback)
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_tokopedia_scraper(), TokopediaUrlBuilder())), TOKOPEDIA_SOURCE, _tokopedia_fallback)

    # Get locations for Gemilang (only when it has prices)
    locations_data = {}
    gemilang_has_prices = any(p.get("source") == GEMILANG_SOURCE for p in prices)
    if gemilang_has_prices:
        gemilang_locations = _run_location_scraper(request, create_gemilang_location_scraper, GEMILANG_SOURCE)
        # Create a simple mapping of vendor to locations
        if gemilang_locations:
            locations_data[GEMILANG_SOURCE] = gemilang_locations

    # sanity: drop unreal prices and dedupe the final list
    prices = [p for p in prices if p.get("value") and p["value"] >= 100]
    uniq = {}
    for p in prices:
        k = (p.get("source"), p.get("url") or "", p.get("item"), p.get("value"))
        if k not in uniq:
            uniq[k] = p
    prices = list(uniq.values())

    # Add location info to prices
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

    try:
        prices.sort(key=lambda x: (x["value"] is None, x["value"]))
    except Exception:
        pass

    return render(request, "dashboard/home.html", {"prices": prices})


@require_POST
def trigger_scrape(request):
    keyword = request.POST.get("q", "semen")
    counts = {
        "gemilang": _run_vendor_to_count(request, keyword, (lambda: (create_gemilang_scraper(), GemilangUrlBuilder())), GEMILANG_SOURCE),
        "depo": _run_vendor_to_count(request, keyword, (lambda: (create_depo_scraper(), DepoUrlBuilder())), "Depo Bangunan"),
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
    return render(request, DASHBOARD_FORM_TEMPLATE, {"title": "Save Price from Scrape", "form": form})