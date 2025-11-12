from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_depo_scraper, create_depo_location_scraper
from .database_service import DepoBangunanDatabaseService
import logging

logger = logging.getLogger(__name__)

# Error message constants
ERROR_KEYWORD_REQUIRED = 'Keyword parameter is required'
ERROR_PAGE_INVALID = 'Page parameter must be a valid integer'
ERROR_INTERNAL_SERVER = 'Internal server error occurred'

def _validate_sort_type(raw):
    sort_type = (raw or "cheapest").lower()
    if sort_type not in ("cheapest", "popularity"):
        return None, JsonResponse(
            {"error": 'sort_type must be either "cheapest" or "popularity"'}, status=400
        )
    return sort_type, None

def _bool_from_str(s):
    return str(s).lower() in ("true", "1", "yes")

def _pick_products(sort_type, products):
    """Return products per sort_type rule."""
    if sort_type != "popularity":
        return products
    with_sales = [p for p in products if getattr(p, "sold_count", None) is not None]
    if with_sales:
        with_sales.sort(key=lambda x: x.sold_count, reverse=True)
        return with_sales[:5]
    return products[:5]

def _response_no_products():
    return JsonResponse({
        "success": True,
        "message": "No products found to save",
        "saved": 0, "updated": 0, "inserted": 0, "anomalies": []
    })

def _response_scrape_failed(result):
    return JsonResponse({
        "success": False,
        "error": result.error_message,
        "saved": 0, "updated": 0, "inserted": 0, "anomalies": []
    }, status=500)

def _save_and_respond(db_service, products_data, use_price_update, result_url):
    if use_price_update:
        save_result = db_service.save_with_price_update(products_data)
        if not save_result.get("success", False):
            return JsonResponse({
                "success": False,
                "error": "Failed to save products to database",
                "saved": 0, "updated": 0, "inserted": 0, "anomalies": []
            }, status=500)

        anomalies = save_result.get("anomalies", [])
        return JsonResponse({
            "success": True,
            "message": (
                f"Updated {save_result['updated_count']} products, "
                f"inserted {save_result['new_count']} new products"
            ),
            "saved": save_result["updated_count"] + save_result["new_count"],
            "updated": save_result["updated_count"],
            "inserted": save_result["new_count"],
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "url": result_url
        })

    # regular save
    if not db_service.save(products_data):
        return JsonResponse({
            "success": False,
            "error": "Failed to save products to database",
            "saved": 0, "updated": 0, "inserted": 0, "anomalies": []
        }, status=500)

    return JsonResponse({
        "success": True,
        "message": f"Successfully saved {len(products_data)} products",
        "saved": len(products_data),
        "updated": 0,
        "inserted": len(products_data),
        "anomalies": [],
        "url": result_url
    })



def _create_error_response(message, status=400):
    return JsonResponse({'error': message}, status=status)


def _validate_and_parse_keyword(keyword):
    """Validate and parse keyword parameter"""
    if not keyword or not keyword.strip():
        return None, _create_error_response(ERROR_KEYWORD_REQUIRED)
    return keyword.strip(), None


def _parse_sort_by_price(sort_by_price_param):
    """Parse sort_by_price parameter"""
    if sort_by_price_param:
        return sort_by_price_param.lower() in ['true', '1', 'yes']
    return True  # Default to True


def _parse_page(page_param):
    """Parse and validate page parameter"""
    try:
        return int(page_param or '0'), None
    except ValueError:
        return None, _create_error_response(ERROR_PAGE_INVALID)


def _convert_products_to_dict(products):
    """Convert product objects to dictionary format"""
    return [
        {
            'name': product.name,
            'price': product.price,
            'url': product.url,
            'unit': product.unit
        }
        for product in products
    ]


def _convert_products_to_dict_with_sold_count(products):
    """Convert product objects to dictionary format including sold_count"""
    return [
        {
            'name': product.name,
            'price': product.price,
            'url': product.url,
            'unit': product.unit,
            'sold_count': product.sold_count
        }
        for product in products
    ]


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        # Validate and parse parameters
        keyword, error = _validate_and_parse_keyword(request.GET.get('keyword'))
        if error:
            return error
        
        # Support both sort_type and sort_by_price for backward compatibility
        sort_type = request.GET.get('sort_type', '').lower()
        if sort_type:
            # If sort_type is provided, use it
            if sort_type not in ['cheapest', 'popularity']:
                return JsonResponse({
                    'error': 'sort_type must be either "cheapest" or "popularity"'
                }, status=400)
            sort_by_price = (sort_type == 'cheapest')
        else:
            # Otherwise, use the old sort_by_price parameter
            sort_by_price = _parse_sort_by_price(request.GET.get('sort_by_price', 'true'))
            sort_type = 'cheapest' if sort_by_price else 'popularity'
        
        page, error = _parse_page(request.GET.get('page', '0'))
        if error:
            return error
        
        scraper = create_depo_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        products_data = _convert_products_to_dict(result.products)
        
        response_data = {
            'success': result.success,
            'products': products_data,
            'error_message': result.error_message,
            'url': result.url,
            'sort_type': sort_type
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Depo Bangunan scraper: {str(e)}")
        return _create_error_response(ERROR_INTERNAL_SERVER, 500)


@require_http_methods(["GET"])
def depobangunan_locations_view(request):
    """View function for fetching Depo Bangunan store locations"""
    try:
        timeout_param = request.GET.get('timeout', '30')
        try:
            timeout = int(timeout_param)
        except ValueError:
            return _create_error_response('Timeout parameter must be a valid integer')
        
        scraper = create_depo_location_scraper()
        result = scraper.scrape_locations(timeout=timeout)
        
        locations_data = [
            {
                'name': location.name,
                'code': location.code
            }
            for location in result.locations
        ]
        
        response_data = {
            'success': result.success,
            'locations': locations_data,
            'error_message': result.error_message
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Depo Bangunan location scraper: {str(e)}")
        return _create_error_response(ERROR_INTERNAL_SERVER, 500)


@require_http_methods(["POST"])
def scrape_and_save_products(request):
    try:
        # params
        keyword, error = _validate_and_parse_keyword(request.POST.get("keyword"))
        if error:
            return error

        sort_type, error = _validate_sort_type(request.POST.get("sort_type"))
        if error:
            return error
        sort_by_price = (sort_type == "cheapest")

        page, error = _parse_page(request.POST.get("page", "0"))
        if error:
            return error

        use_price_update = _bool_from_str(request.POST.get("use_price_update", "false"))

        # scrape
        scraper = create_depo_scraper()
        result = scraper.scrape_products(keyword=keyword, sort_by_price=sort_by_price, page=page)
        if not result.success:
            return _response_scrape_failed(result)
        if not result.products:
            return _response_no_products()

        # choose + convert
        chosen = _pick_products(sort_type, result.products)
        products_data = _convert_products_to_dict(chosen)

        # save & respond
        db_service = DepoBangunanDatabaseService()
        return _save_and_respond(db_service, products_data, use_price_update, result.url)

    except Exception as e:
        logger.error(f"Unexpected error in scrape and save: {e}")
        return JsonResponse({"error": ERROR_INTERNAL_SERVER}, status=500)



@require_http_methods(["GET"])
def scrape_popularity(request):
    """
    Scrape products sorted by popularity (top rated) and return top N by sold count.
    
    Query Parameters:
        - keyword: Search keyword (required)
        - page: Page number to scrape (default: 0)
        - top_n: Number of top products to return (default: 5)
    """
    try:
        # Validate and parse keyword
        keyword, error = _validate_and_parse_keyword(request.GET.get('keyword'))
        if error:
            return error
        
        # Parse page parameter
        page, error = _parse_page(request.GET.get('page', '0'))
        if error:
            return error
        
        # Parse top_n parameter
        top_n_param = request.GET.get('top_n', '5')
        try:
            top_n = int(top_n_param)
            if top_n < 1:
                top_n = 5
        except ValueError:
            return _create_error_response('top_n parameter must be a valid positive integer')
        
        # Scrape with popularity sorting
        scraper = create_depo_scraper()
        result = scraper.scrape_popularity_products(
            keyword=keyword,
            page=page,
            top_n=top_n
        )
        
        # Convert to dictionary format WITH sold_count
        products_data = _convert_products_to_dict_with_sold_count(result.products)
        
        response_data = {
            'success': result.success,
            'products': products_data,
            'error_message': result.error_message,
            'url': result.url,
            'total_products': len(products_data)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in scrape popularity: {str(e)}")
        return _create_error_response(ERROR_INTERNAL_SERVER, 500)
