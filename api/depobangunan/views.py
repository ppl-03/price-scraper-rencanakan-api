from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_depo_scraper, create_depo_location_scraper
import logging

logger = logging.getLogger(__name__)


def _create_error_response(message, status=400):
    return JsonResponse({'error': message}, status=status)


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        keyword = request.GET.get('keyword')
        if not keyword or not keyword.strip():
            return _create_error_response('Keyword parameter is required')
        
        keyword = keyword.strip()
        
        sort_by_price_param = request.GET.get('sort_by_price', 'true').lower()
        sort_by_price = sort_by_price_param in ['true', '1', 'yes']
        
        page_param = request.GET.get('page', '0')
        try:
            page = int(page_param)
        except ValueError:
            return _create_error_response('Page parameter must be a valid integer')
        
        scraper = create_depo_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        products_data = [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url,
                'unit': product.unit
            }
            for product in result.products
        ]
        
        response_data = {
            'success': result.success,
            'products': products_data,
            'error_message': result.error_message,
            'url': result.url
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Depo Bangunan scraper: {str(e)}")
        return _create_error_response('Internal server error occurred', 500)


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
                'store_name': location.store_name,
                'address': location.address
            }
            for location in result.locations
        ]
        
        response_data = {
            'success': result.success,
            'locations': locations_data,
            'error_message': result.error_message,
            'url': result.url
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Depo Bangunan location scraper: {str(e)}")
        return _create_error_response('Internal server error occurred', 500)