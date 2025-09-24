from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages


from api.gemilang.scraper import GemilangPriceScraper
from api.core import BaseHttpClient, BaseUrlBuilder
from api.gemilang.html_parser import GemilangHtmlParser


GEMILANG_BASE_URL = "https://gemilang-store.com"
GEMILANG_SEARCH_PATH = "/pusat/shop"  


class GemilangUrlBuilder(BaseUrlBuilder):
    """Only override how query params are built."""
    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        params = {"keyword": keyword, "page": page}
        if sort_by_price:
            params["sort"] = "price_asc"
        return params


def _make_scraper():
    http_client = BaseHttpClient() 
    url_builder = GemilangUrlBuilder(
        base_url=GEMILANG_BASE_URL,
        search_path=GEMILANG_SEARCH_PATH,
    )
    html_parser = GemilangHtmlParser()
    scraper = GemilangPriceScraper(http_client, url_builder, html_parser)
    return scraper, http_client, url_builder


def home(request):
    """
    Show product name, price, vendor directly from Gemilang (no DB yet).
    """
    prices = []
    keyword = request.GET.get("q", "semen")  
    try:
        scraper, http_client, url_builder = _make_scraper()
        url = url_builder.build_search_url(keyword, sort_by_price=True, page=0)


        html = http_client.get(url)
        messages.info(request, f"Scrape URL: {url}")
        messages.info(request, f"HTML length: {len(html)}")

        result = scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)

        if result.success and result.products:
            vendor = "Gemilang Store" 
            for idx, p in enumerate(result.products, start=1):
                prices.append({
                    "item": p.name,
                    "value": p.price,
                    "source": vendor,
                })
        else:
            messages.error(request, result.error_message or "No products parsed. Check URL/params or selectors.")
    except Exception as e:
        messages.error(request, f"Scraper error: {e}")

    return render(request, "dashboard/home.html", {"prices": prices})


@require_POST
def trigger_scrape(request):
    """
    Manually trigger a scrape, then redirect to home (so the table renders results).
    """
    keyword = request.POST.get("q", "semen")
    try:
        scraper, http_client, url_builder = _make_scraper()
        url = url_builder.build_search_url(keyword, sort_by_price=True, page=0)
        html = http_client.get(url)  # fetch once for diagnostics
        result = scraper.scrape_products(keyword=keyword, sort_by_price=True, page=0)

        messages.info(request, f"Scrape URL: {url}")
        messages.info(request, f"HTML length: {len(html)}")

        if not result.success:
            raise Exception(result.error_message or "Scraping failed")

        messages.success(request, f"Scrape completed. {len(result.products)} products fetched.")
    except Exception as e:
        messages.error(request, f"Scrape failed: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return redirect("home")