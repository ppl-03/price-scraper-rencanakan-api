# dashboard/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

# For diagnostics + HTML fetching
from api.core import BaseHttpClient

# GEMILANG
from api.gemilang.factory import create_gemilang_scraper
from api.gemilang.url_builder import GemilangUrlBuilder

# DEPO BANGUNAN 
from api.depobangunan.factory import create_depo_scraper
from api.depobangunan.url_builder import DepoUrlBuilder

# JURAGAN MATERIAL 
from api.juragan_material.factory import create_juraganmaterial_scraper
from api.juragan_material.url_builder import JuraganMaterialUrlBuilder

# Fallback parsing (views.py only — keeps your teammate's folder untouched)
from bs4 import BeautifulSoup
import re


# Helpers 
def _make_gemilang_scraper():
    """Gemilang: use its factory + UrlBuilder."""
    scraper = create_gemilang_scraper()
    url_builder = GemilangUrlBuilder()
    return scraper, url_builder


def _make_depo_scraper():
    """Depo: use its factory + UrlBuilder."""
    scraper = create_depo_scraper()
    url_builder = DepoUrlBuilder()
    return scraper, url_builder


def _make_juragan_scraper():
    """Juragan Material: use its factory + UrlBuilder."""
    scraper = create_juraganmaterial_scraper()
    url_builder = JuraganMaterialUrlBuilder()
    return scraper, url_builder


def _build_url_defensively(url_builder, keyword: str, sort_by_price: bool, page: int) -> str:
    """
    Works with UrlBuilders that implement build_search_url() (preferred)
    or build_url(keyword).
    """
    if hasattr(url_builder, "build_search_url"):
        return url_builder.build_search_url(keyword, sort_by_price=sort_by_price, page=page)
    if hasattr(url_builder, "build_url"):
        return url_builder.build_url(keyword)
    raise AttributeError("URL builder has no supported build methods.")


# Juragan fallback 
def _digits_to_int(txt: str) -> int:
    ds = re.findall(r"\d", txt or "")
    return int("".join(ds)) if ds else 0


def _juragan_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    """
    Parse Juragan Material HTML directly from the built URL using the vendor-analysis path:
      div.product-card -> (price within card; look for 'Rp' text)
    Returns: (list_of_price_rows, built_url, html_len)
    Each row: {'item': str, 'value': int, 'source': 'Juragan Material', 'url': str}
    """
    try:
        # Build URL using the same builder (so we respect config + params)
        j_urlb = JuraganMaterialUrlBuilder()
        url = _build_url_defensively(j_urlb, keyword, sort_by_price=sort_by_price, page=page)

        html = BaseHttpClient().get(url) or ""
        html_len = len(html)
        if not html:
            return [], url, 0

        soup = BeautifulSoup(html, "html.parser")

        # Containers from your vendor analysis
        cards = soup.select("div.product-card")
        results = []

        for c in cards:
            # NAME 
            name = None
            # try link > p.product-name, then plain p.product-name, then any .product-name
            for sel in ("a p.product-name", "p.product-name", ".product-name"):
                el = c.select_one(sel)
                if el:
                    txt = el.get_text(" ", strip=True)
                    if txt:
                        name = txt
                        break
            if not name:
                # last resort: img alt
                img = c.find("img")
                if img and img.get("alt"):
                    name = img["alt"].strip()
            if not name:
                continue

            # URL
            link = c.select_one("a:has(p.product-name)") or c.select_one("a[href]")
            href = link.get("href") if link and link.get("href") else "/products/product"

            # PRICE 
            price_val = 0
            # 1) documented path: div.product-card-price div.price
            el = c.select_one("div.product-card-price div.price")
            if el:
                v = _digits_to_int(el.get_text(" ", strip=True))
                if v > 0:
                    price_val = v

            # 2) any Rp/IDR inside price wrapper, if still 0
            if price_val <= 0:
                wrapper = c.select_one("div.product-card-price")
                if wrapper:
                    for tag in wrapper.find_all(["span", "div", "p", "h1","h2","h3","h4","h5","h6"], string=True):
                        txt = tag.get_text(" ", strip=True)
                        if "Rp" in txt or "IDR" in txt:
                            v = _digits_to_int(txt)
                            if v > 0:
                                price_val = v
                                break

            # 3) last resort: any Rp/IDR anywhere inside the card
            if price_val <= 0:
                for t in c.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
                    v = _digits_to_int(t.strip())
                    if v > 0:
                        price_val = v
                        break

            if price_val <= 0:
                continue

            results.append({
                "item": name,
                "value": price_val,
                "source": "Juragan Material",
                "url": href,
            })

        return results, url, html_len

    except Exception:
        return [], "", 0


# ---------- Views ----------
def home(request):
    """
    Show product name, price, vendor by scraping Gemilang + Depo Bangunan + Juragan Material.
    """
    prices = []
    keyword = request.GET.get("q", "semen")

    # ---- GEMILANG ----
    try:
        g_scraper, g_urlb = _make_gemilang_scraper()
        g_url = _build_url_defensively(g_urlb, keyword, sort_by_price=True, page=0)

        # Optional: probe HTML size for diagnostics in the toast
        try:
            g_html_len = len(BaseHttpClient().get(g_url) or "")
        except Exception:
            g_html_len = 0

        g_res = g_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)
        messages.info(request, f"[Gemilang] URL: {g_url} | HTML: {g_html_len} bytes")

        if getattr(g_res, "success", False) and getattr(g_res, "products", None):
            for p in g_res.products:
                prices.append({
                    "item": p.name,
                    "value": p.price,
                    "source": "Gemilang Store",
                    "url": getattr(p, "url", "")
                })
        else:
            messages.warning(request, f"[Gemilang] {getattr(g_res, 'error_message', 'No products parsed')}")
    except Exception as e:
        messages.error(request, f"[Gemilang] Scraper error: {e}")

    # DEPO BANGUNAN 
    try:
        d_scraper, d_urlb = _make_depo_scraper()
        d_url = _build_url_defensively(d_urlb, keyword, sort_by_price=True, page=0)
        d_res = d_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)
        messages.info(request, f"[Depo] URL: {d_url}")

        if getattr(d_res, "success", False) and getattr(d_res, "products", None):
            for p in d_res.products:
                prices.append({
                    "item": p.name,
                    "value": p.price,
                    "source": "Depo Bangunan",
                    "url": getattr(p, "url", "")
                })
        else:
            messages.warning(request, f"[Depo] {getattr(d_res, 'error_message', 'No products parsed')}")
    except Exception as e:
        messages.error(request, f"[Depo] Scraper error: {e}")

    # JURAGAN MATERIAL
    try:
        j_scraper, j_urlb = _make_juragan_scraper()
        j_url = _build_url_defensively(j_urlb, keyword, sort_by_price=True, page=0)

        # Always probe and report HTML size so we can see the endpoint & response size
        try:
            j_html = BaseHttpClient().get(j_url) or ""
            j_html_len = len(j_html)
        except Exception:
            j_html = ""
            j_html_len = 0

        j_res = j_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)
        parsed_count = 0

        if getattr(j_res, "success", False) and getattr(j_res, "products", None):
            for p in j_res.products:
                prices.append({
                    "item": p.name,
                    "value": p.price,
                    "source": "Juragan Material",
                    "url": getattr(p, "url", "")
                })
                parsed_count += 1
            messages.info(request, f"[JuraganMaterial] URL (pkg): {j_url} | HTML: {j_html_len} bytes | parsed={parsed_count}")
        else:
            # fallback in views.py ONLY 
            fb_products, fb_url, fb_html_len = _juragan_fallback(keyword, sort_by_price=True, page=0)
            if fb_products:
                prices.extend(fb_products)
                messages.info(request, f"[JuraganMaterial] Fallback URL: {fb_url} | HTML: {fb_html_len} bytes | parsed={len(fb_products)}")
            else:
                messages.warning(request, f"[JuraganMaterial] Package returned no products; fallback also found none. URL: {j_url} | HTML: {j_html_len} bytes")
    except Exception as e:
        messages.error(request, f"[JuraganMaterial] Scraper error: {e}")

    # OPTIONAL sanity filter: drop obviously invalid prices (< Rp 100)
    prices = [p for p in prices if p.get("value") and p["value"] >= 100]

    # Sort combined list by ascending price (None last)
    try:
        prices.sort(key=lambda x: (x["value"] is None, x["value"]))
    except Exception:
        pass

    return render(request, "dashboard/home.html", {"prices": prices})


@require_POST
def trigger_scrape(request):
    """
    POST endpoint behind your 'Search' button: runs all scrapers and reports counts.
    """
    keyword = request.POST.get("q", "semen")
    counters, errors = {"gemilang": 0, "depo": 0, "juragan_material": 0}, []

    # Gemilang
    try:
        g_scraper, g_urlb = _make_gemilang_scraper()
        g_url = _build_url_defensively(g_urlb, keyword, sort_by_price=True, page=0)
        g_res = g_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)
        messages.info(request, f"[Gemilang] URL: {g_url}")
        if getattr(g_res, "success", False) and getattr(g_res, "products", None):
            counters["gemilang"] = len(g_res.products)
        else:
            errors.append(f"Gemilang: {getattr(g_res, 'error_message', 'parse failed')}")
    except Exception as e:
        errors.append(f"Gemilang error: {e}")

    # Depo
    try:
        d_scraper, d_urlb = _make_depo_scraper()
        d_url = _build_url_defensively(d_urlb, keyword, sort_by_price=True, page=0)
        d_res = d_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)
        messages.info(request, f"[Depo] URL: {d_url}")
        if getattr(d_res, "success", False) and getattr(d_res, "products", None):
            counters["depo"] = len(d_res.products)
        else:
            errors.append(f"Depo: {getattr(d_res, 'error_message', 'parse failed')}")
    except Exception as e:
        errors.append(f"Depo error: {e}")

    # Juragan Material
    try:
        j_scraper, j_urlb = _make_juragan_scraper()
        j_url = _build_url_defensively(j_urlb, keyword, sort_by_price=True, page=0)
        j_res = j_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)

        if getattr(j_res, "success", False) and getattr(j_res, "products", None):
            counters["juragan_material"] = len(j_res.products)
            messages.info(request, f"[JuraganMaterial] URL (pkg): {j_url} | parsed={counters['juragan_material']}")
        else:
            fb_products, fb_url, _ = _juragan_fallback(keyword, sort_by_price=True, page=0)
            if fb_products:
                counters["juragan_material"] = len(fb_products)
                messages.info(request, f"[JuraganMaterial] Fallback URL: {fb_url} | parsed={len(fb_products)}")
            else:
                errors.append("JuraganMaterial: parse failed (package + fallback)")
    except Exception as e:
        errors.append(f"JuraganMaterial error: {e}")

    if errors:
        messages.error(request, " | ".join(errors))
        return JsonResponse({"status": "error", "message": errors}, status=500)

    messages.success(
        request,
        "Scrape completed. Gemilang={gemilang}, Depo={depo}, JuraganMaterial={juragan}".format(
            gemilang=counters["gemilang"],
            depo=counters["depo"],
            juragan=counters["juragan_material"],
        )
    )
    return redirect("home")