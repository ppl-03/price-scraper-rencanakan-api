from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.conf import settings
from .services import VendorPricingService


@require_GET
def home_db(request):
    """Dashboard home view that reads vendor prices from the database.

    Query params supported:
      - q: search keyword
      - page: page number
      - per_page: items per page
    """
    q = request.GET.get("q")

    svc = VendorPricingService()
    # Render full dataset so the client-side JS can paginate/filter it.
    prices = svc.list_all_prices(q=q)

    context = {
        "prices": prices,
        "total": len(prices),
        "page": 1,
        "per_page": len(prices),
        "q": q or "",
    }
    return render(request, "dashboard/home.html", context)


@require_GET
def curated_price_list_db(request):
    """Curated price list view that uses DB vendor products for listing.

    For now this shows the same `curated_price_list.html` but uses the
    vendor product tables. This keeps the old curated CRUD endpoints intact.
    """
    svc = VendorPricingService()
    # fetch all vendor rows for curated list
    prices = svc.list_all_prices(per_vendor_limit=200)
    # Map vendor products into rows compatible with curated list template
    rows = []
    for p in prices:
        rows.append(
            {
                "item_price": {"name": p.get("item")},
                "province": {"name": p.get("location") or "-"},
                "price": p.get("value"),
            }
        )

    return render(request, "dashboard/curated_price_list.html", {"rows": rows})

@require_GET
def price_anomalies(request):
    """
    Display price anomalies page
    """
    return render(request, "dashboard/price_anomalies.html")
