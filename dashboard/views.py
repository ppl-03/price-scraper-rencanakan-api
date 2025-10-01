from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
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
def _juragan_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    try:
        url = _build_url_defensively(JuraganMaterialUrlBuilder(), keyword, sort_by_price, page)
        html = _human_get(url)
        soup = BeautifulSoup(html, "html.parser")

        # broadened a bit
        cards = soup.select("div.product-card") or \
                soup.select("div.product-card__item, div.card-product, div.catalog-item, div.product")

        out = []
        for c in cards:
            name = None
            for sel in ("a p.product-name", "p.product-name", ".product-name", "[class*=name]"):
                el = c.select_one(sel)
                if el and el.get_text(strip=True):
                    name = _clean_text(el.get_text(" ", strip=True))
                    break
            if not name:
                img = c.find("img")
                if img and img.get("alt"):
                    name = _clean_text(img["alt"])
            if not name:
                continue

            link = c.select_one("a:has(p.product-name)") or c.select_one("a[href]")
            href = link.get("href") if link and link.get("href") else "/products/product"

            price = 0
            el = c.select_one("div.product-card-price div.price")
            if el:
                price = _digits_to_int(el.get_text(" ", strip=True))
            if price <= 0:
                wrapper = c.select_one("div.product-card-price") or c
                if wrapper:
                    for tag in wrapper.find_all(["span", "div", "p", "h1", "h2", "h3", "h4", "h5", "h6"], string=True):
                        v = _digits_to_int(tag.get_text(" ", strip=True))
                        if v > 0:
                            price = v
                            break
            if price <= 0:
                for t in c.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
                    v = _digits_to_int((t or "").strip())
                    if v > 0:
                        price = v
                        break
            if price <= 0:
                continue

            out.append({"item": name, "value": price, "source": "Juragan Material", "url": href})
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
    # 1) Magento-ish: data-price-amount
    pw = node.select_one(".price-wrapper[data-price-amount]")
    if pw and pw.get("data-price-amount"):
        try:
            return int(float(pw["data-price-amount"]))
        except Exception:
            pass

    # 2) Generic price classes
    el = node.select_one(
        "span.price__final, p.price__final, .price-box .price, "
        "span.price, .price, [class*=price]"
    )
    if el and el.get_text(strip=True):
        v = _digits_to_int(el.get_text(" ", strip=True))
        if v > 0:
            return v

    # 3) Last resort: currency-looking text
    for t in node.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
        v = _digits_to_int(t)
        if v > 0:
            return v

    return 0


def _parse_mitra10_html(html: str, request_url: str) -> list[dict]:
    """
    Robust Mitra10 parser:
      A) JSON-LD (if present)
      B) DOM cards with broader selectors (Magento/MUI/React variants)
    """
    out: list[dict] = []
    if not html:
        return out

    soup = BeautifulSoup(html, "html.parser")
    seen = set()

    # ---------- A) JSON-LD ----------
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (sc.string or sc.text or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        def _emit(name: str | None, price_val: int, href: str | None):
            if not name or price_val <= 0:
                return
            full_url = urljoin(request_url, href or "")
            key = full_url or (name, price_val)
            if key in seen:
                return
            seen.add(key)
            out.append({"item": _clean_text(name), "value": price_val, "source": "Mitra10", "url": full_url})

        # ItemList / SearchResultsPage
        try:
            if isinstance(data, dict) and data.get("@type") in ("ItemList", "SearchResultsPage"):
                elems = data.get("itemListElement") or []
                for e in elems:
                    prod = e.get("item") if isinstance(e, dict) else None
                    if isinstance(prod, dict) and (prod.get("@type") == "Product" or "name" in prod):
                        name = prod.get("name")
                        price_val = 0
                        offers = prod.get("offers")
                        if isinstance(offers, dict) and offers.get("price"):
                            try:
                                price_val = int(float(str(offers.get("price")).replace(",", "")))
                            except Exception:
                                price_val = _digits_to_int(str(offers.get("price")))
                        url_ = prod.get("url") or prod.get("@id")
                        _emit(name, price_val, url_)
        except Exception:
            pass

        # Standalone Product(s)
        try:
            candidates = data if isinstance(data, list) else [data]
            for d in candidates:
                if not isinstance(d, dict):
                    continue
                if d.get("@type") == "Product" or "name" in d:
                    name = d.get("name")
                    price_val = 0
                    offers = d.get("offers")
                    if isinstance(offers, dict) and offers.get("price"):
                        try:
                            price_val = int(float(str(offers.get("price")).replace(",", "")))
                        except Exception:
                            price_val = _digits_to_int(str(offers.get("price")))
                    url_ = d.get("url") or d.get("@id")
                    _emit(name, price_val, url_)
        except Exception:
            pass

    if out:
        return out  # JSON-LD was enough

    # ---------- B) DOM-based parsing ----------
    containers = (
        soup.select("li.product-item") or
        soup.select("div.product-item, div.product-item-info") or
        soup.select("div.MuiGrid2-root.MuiGrid2-item, div.MuiGrid-item") or
        soup.select("div[class*=ProductCard], section[class*=product]") or
        soup.select("[data-product-id], [data-product-sku]") or
        soup.select("article:has(a[href])") or
        []
    )

    for it in containers:
        # name resolution
        name = None
        a = it.select_one("a.product-item-link")
        if a and _clean_text(a.get_text()):
            name = _clean_text(a.get_text())

        if not name:
            for sel in ("h3, h2, h1, .product-name, .MuiTypography-root, [class*=title], [class*=name]"):
                el = it.select_one(sel)
                if el and _clean_text(el.get_text()):
                    name = _clean_text(el.get_text())
                    break

        if not name:
            img = it.find("img")
            if img and img.get("alt"):
                name = _clean_text(img["alt"])

        if not name:
            link_guess = it.select_one("a[href][title]") or it.select_one("a[href]")
            if link_guess and link_guess.get("title"):
                name = _clean_text(link_guess["title"])

        if not name:
            continue

        # URL
        link = (
            a or
            it.select_one("a.gtm_mitra10_cta_product") or
            it.select_one('a[href*="/product/"], a[href*="/catalog/"], a[href]')
        )
        href = link.get("href") if link and link.get("href") else ""
        full_url = urljoin(request_url, href)

        # price
        price = _extract_price_from_node(it)
        if price <= 0:
            continue

        key = full_url or (name, price)
        if key in seen:
            continue
        seen.add(key)

        out.append({"item": name, "value": price, "source": "Mitra10", "url": full_url})

    return out


def _mitra10_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    """
    1) GET with retry; parse.
    2) If empty, try an alternate URL (no sort, page=1).
    3) If still empty and Playwright is allowed/available, render.
    """
    try:
        urlb = Mitra10UrlBuilder()

        # First attempt
        url1 = _build_url_defensively(urlb, keyword, sort_by_price, page)
        html1 = _human_get(url1)
        prods1 = _parse_mitra10_html(html1, url1)
        if prods1:
            return prods1, url1, len(html1)

        # Alternate attempt: remove sort, page=1
        try:
            url2 = _build_url_defensively(urlb, keyword, False, 1)
        except Exception:
            url2 = url1
        html2 = _human_get(url2)
        prods2 = _parse_mitra10_html(html2, url2)
        if prods2:
            return prods2, url2, len(html2)

        # Playwright render (optional)
        allow_browser = (USE_BROWSER_FALLBACK != "never") and HAS_PLAYWRIGHT
        must_browser = (USE_BROWSER_FALLBACK == "always")
        should_browser = must_browser or _looks_like_bot_challenge(html1) or _looks_like_bot_challenge(html2)
        if allow_browser and should_browser:
            html3 = _fetch_with_playwright(url1, wait_selector="li.product-item")
            prods3 = _parse_mitra10_html(html3, url1)
            if prods3:
                return prods3, url1, len(html3)

        return [], url1, len(html1)
    except Exception:
        return [], "", 0


# ---------------- generic runners ----------------
def _run_vendor_to_prices(request, keyword: str, maker, label: str, fallback=None) -> list[dict]:
    rows = []
    try:
        scraper, urlb = maker()
        url = _build_url_defensively(urlb, keyword, sort_by_price=True, page=0)
        html_len = _fetch_len(url)
        res = scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)

        if getattr(res, "success", False) and getattr(res, "products", None):
            for p in res.products:
                rows.append({"item": p.name, "value": p.price, "source": label, "url": getattr(p, "url", "")})
            messages.info(request, f"[{label}] URL: {url} | HTML: {html_len} bytes | parsed={len(rows)}")
        else:
            if fallback:
                fb_rows, fb_url, fb_len = fallback(keyword, sort_by_price=True, page=0)
                if fb_rows:
                    rows.extend(fb_rows)
                    messages.info(request, f"[{label}] Fallback URL: {fb_url} | HTML: {fb_len} bytes | parsed={len(fb_rows)}")
                else:
                    # compute hint safely (no undefined 'html' var)
                    hint = ""
                    try:
                        html_preview = _human_get(url, tries=1)
                        if _looks_like_bot_challenge(html_preview):
                            hint = " (bot-challenge detected)"
                    except Exception:
                        pass
                    messages.warning(
                        request,
                        f"[{label}] Package returned no products; fallback also found none{hint}. "
                        f"URL: {url} | HTML: {html_len} bytes"
                    )
            else:
                messages.warning(request, f"[{label}] {getattr(res, 'error_message', 'No products parsed')}")
    except Exception as e:
        messages.error(request, f"[{label}] Scraper error: {e}")
    return rows


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


def curated_price_list(request):
    qs = models.ItemPriceProvince.objects.select_related("item_price", "province")
    return render(request, "dashboard/curated_price_list.html", {"rows": qs})


def curated_price_create(request):
    form = ItemPriceProvinceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Curated price saved")
        return redirect("curated_price_list")
    return render(request, "dashboard/form.html", {"title": "New Curated Price", "form": form})


def curated_price_update(request, pk):
    obj = get_object_or_404(models.ItemPriceProvince, pk=pk)
    form = ItemPriceProvinceForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Curated price updated")
        return redirect("curated_price_list")
    return render(request, "dashboard/form.html", {"title": "Edit Curated Price", "form": form})


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
    return render(request, "dashboard/form.html", {"title": "Save Price from Scrape", "form": form})