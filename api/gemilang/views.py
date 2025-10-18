from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .factory import create_gemilang_scraper, create_gemilang_location_scraper
import json
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        keyword = request.GET.get('keyword')
        if not keyword or not keyword.strip():
            return JsonResponse({
                'error': 'Keyword parameter is required'
            }, status=400)
        
        keyword = keyword.strip()
        
        sort_by_price_param = request.GET.get('sort_by_price', 'true').lower()
        sort_by_price = sort_by_price_param in ['true', '1', 'yes']
        
        page_param = request.GET.get('page', '0')
        try:
            page = int(page_param)
        except ValueError:
            return JsonResponse({
                'error': 'Page parameter must be a valid integer'
            }, status=400)
        
        scraper = create_gemilang_scraper()
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
        logger.error(f"Unexpected error in Gemilang scraper: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error occurred'
        }, status=500)


class LocationRequestHandler:
    
    DEFAULT_TIMEOUT = 30
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_timeout(self, request) -> int:
        timeout_param = request.GET.get('timeout', str(self.DEFAULT_TIMEOUT))
        try:
            timeout = int(timeout_param)
            return max(0, timeout)
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid timeout parameter: {timeout_param}, using default")
            return self.DEFAULT_TIMEOUT
    
    def format_locations_response(self, result) -> dict:
        locations_data = [
            {
                'store_name': location.store_name,
                'address': location.address
            }
            for location in result.locations
        ]
        
        return {
            'success': result.success,
            'locations': locations_data,
            'error_message': result.error_message,
            'url': result.url
        }
    
    def create_error_response(self, error_message: str) -> dict:
        return {
            'success': False,
            'locations': [],
            'error_message': error_message
        }


@require_http_methods(["GET"])
def gemilang_locations_view(request):
    handler = LocationRequestHandler()
    
    try:
        timeout = handler.parse_timeout(request)
        
        scraper = create_gemilang_location_scraper()
        result = scraper.scrape_locations(timeout=timeout)
        
        response_data = handler.format_locations_response(result)
        return JsonResponse(response_data)
        
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        handler.logger.error(f"Unexpected error in Gemilang location scraper: {str(e)}")
        
        response_data = handler.create_error_response(error_message)
        return JsonResponse(response_data, status=500)