from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.conf import settings
from django.http import JsonResponse
import json

from .services import VendorPricingService, CategoryUpdateService


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

@require_POST
def update_product_category(request):
    """API endpoint to update a product's category.
    
    Expected JSON payload:
    {
        "source": "Gemilang Store",
        "product_url": "https://example.com/product",
        "new_category": "New Category Name"
    }
    
    Returns:
        JsonResponse with success status and updated product information
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
        
        source = data.get("source")
        product_url = data.get("product_url")
        new_category = data.get("new_category")
        
        # Use the CategoryUpdateService to handle the update
        service = CategoryUpdateService()
        result = service.update_category(source, product_url, new_category)
        
        if result.get("success"):
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON payload"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Server error: {str(e)}"
        }, status=500)


@require_POST
def bulk_update_categories(request):
    """API endpoint to update multiple product categories at once.
    
    Expected JSON payload:
    {
        "updates": [
            {
                "source": "Gemilang Store",
                "product_url": "https://example.com/product1",
                "new_category": "Category A"
            },
            {
                "source": "Mitra10",
                "product_url": "https://example.com/product2",
                "new_category": "Category B"
            }
        ]
    }
    
    Returns:
        JsonResponse with bulk update results
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
        updates = data.get("updates", [])
        
        if not isinstance(updates, list):
            return JsonResponse({
                "success": False,
                "error": "updates must be a list"
            }, status=400)
        
        # Use the CategoryUpdateService to handle bulk updates
        service = CategoryUpdateService()
        result = service.bulk_update_categories(updates)
        
        return JsonResponse(result, status=200)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON payload"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Server error: {str(e)}"
        }, status=500)


@require_GET
def get_available_vendors(request):
    """API endpoint to get list of available vendor sources.
    
    Returns:
        JsonResponse with list of vendor names
    """
    try:
        service = CategoryUpdateService()
        vendors = service.get_available_vendors()
        
        return JsonResponse({
            "success": True,
            "vendors": vendors
        }, status=200)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Server error: {str(e)}"
        }, status=500)
