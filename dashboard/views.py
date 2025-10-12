from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from .forms import ItemPriceProvinceForm
from . import models

from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re, json, os, time, random

# For diagnostics + plain HTML fetch
from api.core import BaseHttpClient

# Vendors (use each package's own factory + url builder)
from api.gemilang.factory import create_gemilang_scraper
from api.gemilang.url_builder import GemilangUrlBuilder

from api.depobangunan.factory import create_depo_scraper
from api.depobangunan.url_builder import DepoUrlBuilder

from api.juragan_material.factory import create_juraganmaterial_scraper
from api.juragan_material.url_builder import JuraganMaterialUrlBuilder

from api.mitra10.factory import create_mitra10_scraper
from api.mitra10.url_builder import Mitra10UrlBuilder

# Playwright fallback (optional at runtime)
HAS_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except Exception:
    HAS_PLAYWRIGHT = False

USE_BROWSER_FALLBACK = os.getenv("USE_BROWSER_FALLBACK", "auto").lower()  # auto|always|never

# Constants to avoid duplication
JURAGAN_MATERIAL_SOURCE = "Juragan Material"
MITRA10_SOURCE = "Mitra10"
DASHBOARD_FORM_TEMPLATE = "dashboard/form.html"
JSON_LD_TYPE_KEY = "@type"


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
        time.sleep(sleep_sec + random.random() * 0.4)
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
    el = card.select_one("div.product-card-price div.price")
    if el:
        price = _digits_to_int(el.get_text(" ", strip=True))
        if price > 0:
            return price
    
    # Try secondary price selectors
    wrapper = card.select_one("div.product-card-price") or card
    if wrapper:
        for tag in wrapper.find_all(["span", "div", "p", "h1", "h2", "h3", "h4", "h5", "h6"], string=True):
            v = _digits_to_int(tag.get_text(" ", strip=True))
            if v > 0:
                return v
    
    # Try currency text fallback
    for t in card.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
        v = _digits_to_int((t or "").strip())
        if v > 0:
            return v
    
    return 0


def _juragan_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    try:
        url = _build_url_defensively(JuraganMaterialUrlBuilder(), keyword, sort_by_price, page)
        html = _human_get(url)
        soup = BeautifulSoup(html, "html.parser")

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
    # 1) Data attributes
    for attr in ["data-price-amount", "data-price", "data-cost"]:
        elem = node.find(attrs={attr: True})
        if elem and elem.get(attr):
            try:
                return int(float(str(elem[attr]).replace(",", "")))
            except Exception:
                pass

    # 2) Specific price classes
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

    # 3) Generic class-based search
    try:
        price_elements = node.select("[class*=price]")
        for el in price_elements:
            v = _digits_to_int(el.get_text(" ", strip=True))
            if v > 0:
                return v
    except Exception:
        pass

    # 4) Currency text search
    currency_patterns = ["Rp", "IDR", "rupiah"]
    for pattern in currency_patterns:
        for t in node.find_all(string=lambda s: s and pattern in str(s)):
            v = _digits_to_int(str(t))
            if v > 0:
                return v

    # 5) All text containing numbers (last resort)
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

    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (sc.string or sc.text or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        try:
            _parse_jsonld_itemlist(data, _emit)
        except Exception:
            pass

        try:
            _parse_jsonld_products(data, _emit)
        except Exception:
            pass

    return out


def _extract_mitra10_product_name(container) -> str | None:
    """Extract product name from Mitra10 DOM container with generic fallbacks."""
    # Try specific product selectors first
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

    # Try image alt text
    img = container.find("img")
    if img and img.get("alt"):
        alt_text = _clean_text(img["alt"])
        if len(alt_text) > 3:  # Avoid tiny alt texts
            return alt_text

    # Try link titles and text
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

    # Generic fallback: longest meaningful text in container
    text_elements = container.find_all(["span", "div", "p"], string=True)
    candidates = []
    for elem in text_elements:
        text = _clean_text(elem.get_text())
        if 10 <= len(text) <= 200 and not any(skip in text.lower() for skip in ["rp", "price", "buy", "cart"]):
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
    out = []
    containers = []
    
    # Try specific selectors first
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
                containers = test_containers
                break
        except Exception:
            continue
    
    # If no specific containers found, try generic approach
    if not containers:
        # Look for any elements that contain both links and price-like text
        all_elements = soup.find_all(["div", "li", "article", "section"])
        for elem in all_elements:
            # Skip if too small or too large
            elem_text = elem.get_text(strip=True)
            if len(elem_text) < 10 or len(elem_text) > 1000:
                continue
                
            # Must have a link
            links = elem.find_all("a", href=True)
            if not links:
                continue
                
            # Must have price-like content
            if not any(indicator in elem_text.lower() for indicator in ["rp", "idr", "price", "harga"]):
                continue
                
            # This element might be a product container
            containers.append(elem)
            
            # Limit to avoid too many false positives
            if len(containers) >= 50:
                break

    for container in containers:
        name = _extract_mitra10_product_name(container)
        if not name:
            continue

        full_url = _extract_mitra10_product_url(container, request_url)
        price = _extract_price_from_node(container)
        
        if price <= 0:
            continue

        key = full_url or (name, price)
        if key in seen:
            continue
        seen.add(key)

        out.append({"item": name, "value": price, "source": MITRA10_SOURCE, "url": full_url})

    return out


def _parse_mitra10_html(html: str, request_url: str) -> list[dict]:
    """
    Robust Mitra10 parser:
      A) JSON-LD (if present)
      B) DOM cards with broader selectors (Magento/MUI/React variants)
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
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
        urlb = Mitra10UrlBuilder()

        # First attempt: Simple URL without complex sort parameters
        simple_url = f"https://www.mitra10.com/catalogsearch/result?q={keyword}"
        html1 = _human_get(simple_url)
        prods1 = _parse_mitra10_html(html1, simple_url)
        if prods1:
            return prods1, simple_url, len(html1)

        # Second attempt: Try with Playwright if available (Mitra10 likely needs JS)
        if HAS_PLAYWRIGHT:
            html_js = _fetch_with_playwright(simple_url, wait_selector="div", timeout_ms=15000)
            if html_js and len(html_js) > len(html1):  # Got more content with JS
                prods_js = _parse_mitra10_html(html_js, simple_url)
                if prods_js:
                    return prods_js, simple_url, len(html_js)

        # Third attempt: Try the original complex URL
        url1 = _build_url_defensively(urlb, keyword, sort_by_price, page)
        if url1 != simple_url:  # Only if different from simple URL
            html2 = _human_get(url1)
            prods2 = _parse_mitra10_html(html2, url1)
            if prods2:
                return prods2, url1, len(html2)

        # Fourth attempt: Try alternative search patterns
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

        # Return the best attempt we made
        return [], simple_url, len(html1)
    except Exception:
        return [], "", 0


# ---------------- generic runners ----------------
def _handle_successful_scrape(request, res, label: str, url: str, html_len: int) -> list[dict]:
    """Handle successful scrape results."""
    rows = []
    for p in res.products:
        rows.append({"item": p.name, "value": p.price, "source": label, "url": getattr(p, "url", "")})
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


# ---------------- views ----------------
def home(request):
    keyword = request.GET.get("q", "semen")
    prices = []
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_gemilang_scraper(), GemilangUrlBuilder())), "Gemilang Store")
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_depo_scraper(), DepoUrlBuilder())), "Depo Bangunan")
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_juraganmaterial_scraper(), JuraganMaterialUrlBuilder())), "Juragan Material", _juragan_fallback)
    prices += _run_vendor_to_prices(request, keyword, (lambda: (create_mitra10_scraper(), Mitra10UrlBuilder())), "Mitra10", _mitra10_fallback)

    # sanity: drop unreal prices and dedupe the final list
    prices = [p for p in prices if p.get("value") and p["value"] >= 100]
    uniq = {}
    for p in prices:
        k = (p.get("source"), p.get("url") or "", p.get("item"), p.get("value"))
        if k not in uniq:
            uniq[k] = p
    prices = list(uniq.values())

    try:
        prices.sort(key=lambda x: (x["value"] is None, x["value"]))
    except Exception:
        pass

    return render(request, "dashboard/home.html", {"prices": prices})


@require_POST
def trigger_scrape(request):
    keyword = request.POST.get("q", "semen")
    counts = {
        "gemilang": _run_vendor_to_count(request, keyword, (lambda: (create_gemilang_scraper(), GemilangUrlBuilder())), "Gemilang Store"),
        "depo": _run_vendor_to_count(request, keyword, (lambda: (create_depo_scraper(), DepoUrlBuilder())), "Depo Bangunan"),
        "juragan": _run_vendor_to_count(request, keyword, (lambda: (create_juraganmaterial_scraper(), JuraganMaterialUrlBuilder())), "Juragan Material", _juragan_fallback),
        "mitra10": _run_vendor_to_count(request, keyword, (lambda: (create_mitra10_scraper(), Mitra10UrlBuilder())), "Mitra10", _mitra10_fallback),
    }
    messages.success(
        request,
        "Scrape completed. Gemilang={gemilang}, Depo={depo}, JuraganMaterial={juragan}, Mitra10={mitra}".format(
            gemilang=counts["gemilang"], depo=counts["depo"], juragan=counts["juragan"], mitra=counts["mitra10"]
        )
    )
    return redirect("home")


@require_GET
def curated_price_list(request):
    qs = models.ItemPriceProvince.objects.select_related("item_price", "province")
    return render(request, "dashboard/curated_price_list.html", {"rows": qs})


@csrf_protect
@require_http_methods(["GET", "POST"])
def curated_price_create(request):
    form = ItemPriceProvinceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Curated price saved")
        return redirect("curated_price_list")
    return render(request, DASHBOARD_FORM_TEMPLATE, {"title": "New Curated Price", "form": form})


@csrf_protect
@require_http_methods(["GET", "POST"])
def curated_price_update(request, pk):
    obj = get_object_or_404(models.ItemPriceProvince, pk=pk)
    form = ItemPriceProvinceForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Curated price updated")
        return redirect("curated_price_list")
    return render(request, DASHBOARD_FORM_TEMPLATE, {"title": "Edit Curated Price", "form": form})


@csrf_protect
@require_http_methods(["GET", "POST"])
def curated_price_delete(request, pk):
    obj = get_object_or_404(models.ItemPriceProvince, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Curated price deleted")
        return redirect("curated_price_list")
    return render(request, "dashboard/confirm_delete.html", {"title": "Delete Curated Price", "obj": obj})


@require_POST
def curated_price_from_scrape(request):
    initial = {
        "price": request.POST.get("value") or None,
        "source": request.POST.get("source") or "",
        "url": request.POST.get("url") or "",
    }
    form = ItemPriceProvinceForm(initial=initial)
    return render(request, DASHBOARD_FORM_TEMPLATE, {"title": "Save Price from Scrape", "form": form})