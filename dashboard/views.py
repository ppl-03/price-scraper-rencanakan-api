# dashboard/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

# For diagnostics + HTML fetching
from api.core import BaseHttpClient

# ---------------- GEMILANG ----------------
from api.gemilang.factory import create_gemilang_scraper
from api.gemilang.url_builder import GemilangUrlBuilder

# ---------------- DEPO BANGUNAN ----------------
from api.depobangunan.factory import create_depo_scraper
from api.depobangunan.url_builder import DepoUrlBuilder

# ---------------- JURAGAN MATERIAL ----------------
from api.juragan_material.factory import create_juraganmaterial_scraper
from api.juragan_material.url_builder import JuraganMaterialUrlBuilder

# ---------------- MITRA10 ----------------
from api.mitra10.factory import create_mitra10_scraper
from api.mitra10.url_builder import Mitra10UrlBuilder

# ---------------- SELENIUM (for Mitra10 fallback only) ----------------
from api.selenium_client import SeleniumSession

# Fallback parsing (views.py only — teammate folders remain untouched)
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin


# ---------- Helpers ----------
def _make_gemilang_scraper():
    scraper = create_gemilang_scraper()
    url_builder = GemilangUrlBuilder()
    return scraper, url_builder


def _make_depo_scraper():
    scraper = create_depo_scraper()
    url_builder = DepoUrlBuilder()
    return scraper, url_builder


def _make_juragan_scraper():
    scraper = create_juraganmaterial_scraper()
    url_builder = JuraganMaterialUrlBuilder()
    return scraper, url_builder


def _make_mitra_scraper():
    scraper = create_mitra10_scraper()
    url_builder = Mitra10UrlBuilder()
    return scraper, url_builder


def _build_url_defensively(url_builder, keyword: str, sort_by_price: bool, page: int) -> str:
    if hasattr(url_builder, "build_search_url"):
        return url_builder.build_search_url(keyword, sort_by_price=sort_by_price, page=page)
    if hasattr(url_builder, "build_url"):
        return url_builder.build_url(keyword)
    raise AttributeError("URL builder has no supported build methods.")


def _digits_to_int(txt: str) -> int:
    ds = re.findall(r"\d", txt or "")
    return int("".join(ds)) if ds else 0


# ---------- Juragan fallback (NO edits to api/juragan_material/*) ----------
def _juragan_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    try:
        j_urlb = JuraganMaterialUrlBuilder()
        url = _build_url_defensively(j_urlb, keyword, sort_by_price=sort_by_price, page=page)

        html = BaseHttpClient().get(url) or ""
        html_len = len(html)
        if not html:
            return [], url, 0

        soup = BeautifulSoup(html, "html.parser")

        # Your documented container; broaden lightly just in case
        cards = soup.select("div.product-card")
        if not cards:
            cards = soup.select("div.product-card__item, div.card-product, div.catalog-item, div.product")

        results = []
        for c in cards:
            # ----- NAME -----
            name = None
            for sel in ("a p.product-name", "p.product-name", ".product-name"):
                el = c.select_one(sel)
                if el:
                    txt = el.get_text(" ", strip=True)
                    if txt:
                        name = txt
                        break
            if not name:
                img = c.find("img")
                if img and img.get("alt"):
                    name = img["alt"].strip()
            if not name:
                continue

            # ----- URL -----
            link = c.select_one("a:has(p.product-name)") or c.select_one("a[href]")
            href = link.get("href") if link and link.get("href") else "/products/product"

            # ----- PRICE -----
            price_val = 0
            el = c.select_one("div.product-card-price div.price")
            if el:
                v = _digits_to_int(el.get_text(" ", strip=True))
                if v > 0:
                    price_val = v

            if price_val <= 0:
                wrapper = c.select_one("div.product-card-price")
                if wrapper:
                    for tag in wrapper.find_all(["span", "div", "p", "h1", "h2", "h3", "h4", "h5", "h6"], string=True):
                        txt = tag.get_text(" ", strip=True)
                        if "Rp" in txt or "IDR" in txt:
                            v = _digits_to_int(txt)
                            if v > 0:
                                price_val = v
                                break

            if price_val <= 0:
                for t in c.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
                    v = _digits_to_int((t or "").strip())
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


# ---------- Mitra10 helpers + fallback (NO edits to api/mitra10/*) ----------
def _looks_like_bot_challenge(html: str) -> bool:
    if not html:
        return False
    low = html.lower()
    # common Cloudflare / bot-challenge signals
    return ("attention required" in low) or ("verify you are human" in low) or ("cf-challenge" in low)


def _parse_mitra10_html(html: str, request_url: str) -> list[dict]:
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Pick the first non-empty container set to avoid nested duplicates
    containers = soup.select("li.product-item")
    if not containers:
        containers = soup.select("div.product-item")          # older markup
    if not containers:
        containers = soup.select("div.product-item-info")     # inner node (only if above are missing)

    # If Magento selectors failed, try your documented React/MUI path
    if not containers:
        containers = soup.select("div.MuiGrid-item")
        if not containers:
            containers = soup.select("div.grid-item")
        if not containers:
            containers = soup.select("div.MuiGrid2-root.MuiGrid2-item")

    seen = set()  # (url) or (name, price) if url missing

    for it in containers:
        # ----- NAME -----
        name = None
        a = it.select_one("a.product-item-link")
        if a:
            name = a.get_text(" ", strip=True)
        if not name:
            for sel in ("a.gtm_mitra10_cta_product p", "p.product-name", "h2.product-name"):
                el = it.select_one(sel)
                if el:
                    txt = el.get_text(" ", strip=True)
                    if txt:
                        name = txt
                        break
        if not name:
            img = it.find("img")
            if img and img.get("alt"):
                name = img["alt"].strip()
        if not name:
            continue

        # ----- URL -----
        link = a or it.select_one("a.gtm_mitra10_cta_product") or it.select_one("a[href]")
        href = link.get("href") if link and link.get("href") else "/product/unknown"
        full_url = urljoin(request_url, href)

        # ----- PRICE -----
        price_val = 0
        pw = it.select_one(".price-wrapper[data-price-amount]")
        if pw and pw.get("data-price-amount"):
            try:
                price_val = int(float(pw["data-price-amount"]))
            except Exception:
                price_val = 0

        if price_val <= 0:
            el = it.select_one("span.price__final, p.price__final, .price-box .price, span.price, .price")
            if el:
                price_val = _digits_to_int(el.get_text(" ", strip=True))

        if price_val <= 0:
            for t in it.find_all(string=lambda s: s and ("Rp" in s or "IDR" in s)):
                price_val = _digits_to_int(t)
                if price_val > 0:
                    break

        if price_val <= 0:
            continue

        # ----- DEDUPE -----
        key = full_url or (name, price_val)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "item": name,
            "value": price_val,
            "source": "Mitra10",
            "url": full_url,
        })

    return results


def _mitra10_fallback(keyword: str, sort_by_price: bool = True, page: int = 0):
    """
    Try normal HTTP first; if we detect bot-page/JS shell or no products, retry with Selenium.
    Returns: (products, final_url, html_len_used)
    """
    try:
        m_urlb = Mitra10UrlBuilder()
        url = _build_url_defensively(m_urlb, keyword, sort_by_price=sort_by_price, page=page)

        # 1) plain HTTP
        html = BaseHttpClient().get(url) or ""
        html_len = len(html)
        products = _parse_mitra10_html(html, url)

        if products:
            return products, url, html_len

        # No products; check if we're on a bot challenge or JS shell
        if _looks_like_bot_challenge(html) or not products:
            # 2) Selenium render
            try:
                with SeleniumSession(headless=True, wait_timeout=12) as browser:
                    html2 = browser.get(url) or ""
                html_len2 = len(html2)
                products2 = _parse_mitra10_html(html2, url)
                if products2:
                    # Return Selenium result
                    return products2, url, html_len2
                else:
                    return [], url, html_len2
            except Exception:
                # Selenium failed; fall back to original response
                return [], url, html_len

        return [], url, html_len

    except Exception:
        return [], "", 0


# ---------- Views ----------
def home(request):
    """
    Show product name, price, vendor by scraping Gemilang + Depo Bangunan + Juragan Material + Mitra10.
    """
    prices = []
    keyword = request.GET.get("q", "semen")

    # ---- GEMILANG ----
    try:
        g_scraper, g_urlb = _make_gemilang_scraper()
        g_url = _build_url_defensively(g_urlb, keyword, sort_by_price=True, page=0)
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

    # ---- DEPO BANGUNAN ----
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

    # ---- JURAGAN MATERIAL ----
    try:
        j_scraper, j_urlb = _make_juragan_scraper()
        j_url = _build_url_defensively(j_urlb, keyword, sort_by_price=True, page=0)
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
            fb_products, fb_url, fb_html_len = _juragan_fallback(keyword, sort_by_price=True, page=0)
            if fb_products:
                prices.extend(fb_products)
                messages.info(request, f"[JuraganMaterial] Fallback URL: {fb_url} | HTML: {fb_html_len} bytes | parsed={len(fb_products)}")
            else:
                messages.warning(request, f"[JuraganMaterial] Package returned no products; fallback also found none. URL: {j_url} | HTML: {j_html_len} bytes")
    except Exception as e:
        messages.error(request, f"[JuraganMaterial] Scraper error: {e}")

    # ---- MITRA10 ----
    try:
        m_scraper, m_urlb = _make_mitra_scraper()
        m_url = _build_url_defensively(m_urlb, keyword, sort_by_price=True, page=0)
        try:
            m_html = BaseHttpClient().get(m_url) or ""
            m_html_len = len(m_html)
        except Exception:
            m_html = ""
            m_html_len = 0

        m_res = m_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)
        parsed_count = 0
        if getattr(m_res, "success", False) and getattr(m_res, "products", None):
            for p in m_res.products:
                prices.append({
                    "item": p.name,
                    "value": p.price,
                    "source": "Mitra10",
                    "url": getattr(p, "url", "")
                })
                parsed_count += 1
            messages.info(request, f"[Mitra10] URL (pkg): {m_url} | HTML: {m_html_len} bytes | parsed={parsed_count}")
        else:
            fb_products, fb_url, fb_html_len = _mitra10_fallback(keyword, sort_by_price=True, page=0)
            if fb_products:
                prices.extend(fb_products)
                messages.info(request, f"[Mitra10] Fallback URL: {fb_url} | HTML: {fb_html_len} bytes | parsed={len(fb_products)}")
            else:
                messages.warning(request, f"[Mitra10] Package returned no products; fallback also found none. URL: {m_url} | HTML: {m_html_len} bytes")
    except Exception as e:
        messages.error(request, f"[Mitra10] Scraper error: {e}")

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
    counters, errors = {"gemilang": 0, "depo": 0, "juragan_material": 0, "mitra10": 0}, []

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

    # Mitra10
    try:
        m_scraper, m_urlb = _make_mitra_scraper()
        m_url = _build_url_defensively(m_urlb, keyword, sort_by_price=True, page=0)
        m_res = m_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)
        if getattr(m_res, "success", False) and getattr(m_res, "products", None):
            counters["mitra10"] = len(m_res.products)
            messages.info(request, f"[Mitra10] URL (pkg): {m_url} | parsed={counters['mitra10']}")
        else:
            fb_products, fb_url, _ = _mitra10_fallback(keyword, sort_by_price=True, page=0)
            if fb_products:
                counters["mitra10"] = len(fb_products)
                messages.info(request, f"[Mitra10] Fallback URL: {fb_url} | parsed={len(fb_products)}")
            else:
                errors.append("Mitra10: parse failed (package + fallback)")
    except Exception as e:
        errors.append(f"Mitra10 error: {e}")

    if errors:
        messages.error(request, " | ".join(errors))
        return JsonResponse({"status": "error", "message": errors}, status=500)

    messages.success(
        request,
        "Scrape completed. Gemilang={gemilang}, Depo={depo}, JuraganMaterial={juragan}, Mitra10={mitra}".format(
            gemilang=counters["gemilang"],
            depo=counters["depo"],
            juragan=counters["juragan_material"],
            mitra=counters["mitra10"],
        )
    )
    return redirect("home")