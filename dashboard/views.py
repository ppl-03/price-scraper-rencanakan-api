from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages



# GEMILANG 
from api.core import BaseHttpClient, BaseUrlBuilder
from api.gemilang.scraper import GemilangPriceScraper
from api.gemilang.html_parser import GemilangHtmlParser

# DEPO BANGUNAN
from api.depobangunan.factory import create_depo_scraper
from api.depobangunan.url_builder import DepoUrlBuilder



GEMILANG_BASE_URL = "https://gemilang-store.com"
GEMILANG_SEARCH_PATH = "/pusat/shop"


class GemilangUrlBuilder(BaseUrlBuilder):
    # Only override how query params are built
    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        params = {"keyword": keyword, "page": page}
        if sort_by_price:
            params["sort"] = "price_asc"
        return params


def _make_gemilang_scraper():
    http_client = BaseHttpClient()
    url_builder = GemilangUrlBuilder(
        base_url=GEMILANG_BASE_URL,
        search_path=GEMILANG_SEARCH_PATH,
    )
    html_parser = GemilangHtmlParser()
    scraper = GemilangPriceScraper(http_client, url_builder, html_parser)
    return scraper, http_client, url_builder


def _make_depo_scraper():
    # Factory returns an IPriceScraper (DepoPriceScraper)
    scraper = create_depo_scraper()
    url_builder = DepoUrlBuilder()  # uses defaults from api.config.config
    return scraper, url_builder


def _build_url_defensively(url_builder, keyword: str, sort_by_price: bool, page: int) -> str:
    # Handle builders that might expose build_search_url or build_url
    if hasattr(url_builder, "build_search_url"):
        return url_builder.build_search_url(keyword, sort_by_price=sort_by_price, page=page)
    if hasattr(url_builder, "build_url"):
        return url_builder.build_url(keyword)
    raise AttributeError("URL builder has no supported build methods.")

def home(request):
    # Show product name, price, vendor by scraping Gemilang + Depo Bangunan
    prices = []
    keyword = request.GET.get("q", "semen")

    # GEMILANG
    try:
        g_scraper, g_http, g_urlb = _make_gemilang_scraper()
        g_url = _build_url_defensively(g_urlb, keyword, sort_by_price=True, page=0)
        g_html = g_http.get(g_url)  # optional: to show HTML length in messages
        g_res = g_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)

        messages.info(request, f"[Gemilang] URL: {g_url} | HTML: {len(g_html)} bytes")

        if getattr(g_res, "success", False) and getattr(g_res, "products", None):
            for p in g_res.products:
                prices.append({"item": p.name, "value": p.price, "source": "Gemilang Store"})
        else:
            messages.warning(request, f"[Gemilang] {getattr(g_res, 'error_message', 'No products parsed')}")
    except Exception as e:
        messages.error(request, f"[Gemilang] Scraper error: {e}")

    # DEPO BANGUNAN
    try:
        d_scraper, d_urlb = _make_depo_scraper()
        # Depo builder adds ?q=... and product_list_order=low_to_high if sort_by_price=True
        d_url = _build_url_defensively(d_urlb, keyword, sort_by_price=True, page=0)
        # For debugging consistency.
        d_res = d_scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)

        messages.info(request, f"[Depo] URL: {d_url}")

        if getattr(d_res, "success", False) and getattr(d_res, "products", None):
            for p in d_res.products:
                prices.append({"item": p.name, "value": p.price, "source": "Depo Bangunan"})
        else:
            messages.warning(request, f"[Depo] {getattr(d_res, 'error_message', 'No products parsed')}")
    except Exception as e:
        messages.error(request, f"[Depo] Scraper error: {e}")

    # Optional: sort combined results by ascending price (None last)
    try:
        prices.sort(key=lambda x: (x["value"] is None, x["value"]))
    except Exception:
        pass

    return render(request, "dashboard/home.html", {"prices": prices})


@require_POST
def trigger_scrape(request):
    # Manually trigger a scrape (both vendors) then redirect to home.

    keyword = request.POST.get("q", "semen")

    counters = {"gemilang": 0, "depo": 0}
    errors = []

    # Gemilang
    try:
        g_scraper, g_http, g_urlb = _make_gemilang_scraper()
        g_url = _build_url_defensively(g_urlb, keyword, sort_by_price=True, page=0)
        _ = g_http.get(g_url)
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

    messages.success(request, f"Scrape completed. Gemilang={counters['gemilang']}, Depo={counters['depo']}.")
    return redirect("home")