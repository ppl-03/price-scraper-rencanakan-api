# dashboard/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

# We only use this to probe HTML length for diagnostics in toasts
from api.core import BaseHttpClient

# ---------------- GEMILANG (use its own factory + url builder) ----------------
from api.gemilang.factory import create_gemilang_scraper
from api.gemilang.url_builder import GemilangUrlBuilder

# ---------------- DEPO BANGUNAN ----------------
from api.depobangunan.factory import create_depo_scraper
from api.depobangunan.url_builder import DepoUrlBuilder


# ---------- Helpers ----------
def _make_gemilang_scraper():
    """
    Use Gemilang's own factory (like Depo) for the scraper,
    and a GemilangUrlBuilder for building/logging URLs.
    """
    scraper = create_gemilang_scraper()   # ready-to-use GemilangPriceScraper
    url_builder = GemilangUrlBuilder()    # for building/logging URLs
    return scraper, url_builder


def _make_depo_scraper():
    scraper = create_depo_scraper()
    url_builder = DepoUrlBuilder()
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


# ---------- Views ----------
def home(request):
    """
    Show product name, price, vendor by scraping Gemilang + Depo Bangunan.
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

    # Sort combined list by ascending price (None last)
    try:
        prices.sort(key=lambda x: (x["value"] is None, x["value"]))
    except Exception:
        pass

    return render(request, "dashboard/home.html", {"prices": prices})


@require_POST
def trigger_scrape(request):
    """
    POST endpoint behind your 'Search' button: runs both scrapers and reports counts.
    """
    keyword = request.POST.get("q", "semen")
    counters, errors = {"gemilang": 0, "depo": 0}, []

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

    if errors:
        messages.error(request, " | ".join(errors))
        return JsonResponse({"status": "error", "message": errors}, status=500)

    messages.success(
        request,
        f"Scrape completed. Gemilang={counters['gemilang']}, Depo={counters['depo']}."
    )
    return redirect("home")