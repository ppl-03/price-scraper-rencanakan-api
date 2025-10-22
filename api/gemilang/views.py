from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_gemilang_scraper, create_gemilang_location_scraper
from .database_service import GemilangDatabaseService
import json
import logging

logger = logging.getLogger(__name__)

API_TOKENS = {
    'dev-token-12345': {
        'name': 'Development Token',
        'allowed_ips': [],
        'created': '2024-01-01',
        'expires': None
    },
    'legacy-api-token-67890': {
        'name': 'Legacy Client Token',
        'allowed_ips': [],
        'created': '2024-01-01',
        'expires': None
    }
}

def _validate_api_token(request) -> tuple[bool, str]:
    token = request.headers.get('X-API-Token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return False, 'API token required'
    
    if token not in API_TOKENS:
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        logger.warning(f"Invalid API token attempt from {client_ip}")
        return False, 'Invalid API token'
    
    token_info = API_TOKENS[token]
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    allowed_ips = token_info.get('allowed_ips', [])
    
    if allowed_ips and client_ip not in allowed_ips:
        logger.warning(f"IP {client_ip} not allowed for token {token_info['name']}")
        return False, 'IP not authorized'
    
    logger.info(f"Valid API token used from {client_ip}: {token_info['name']}")
    return True, ''


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
                'name': location.name,
                'code': location.code
            }
            for location in result.locations
        ]
        
        return {
            'success': result.success,
            'locations': locations_data,
            'error_message': result.error_message
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


@require_http_methods(["POST"])
def scrape_and_save(request):
    is_valid, error_message = _validate_api_token(request)
    if not is_valid:
        return JsonResponse({'error': error_message}, status=401)
    
    try:
        body = json.loads(request.body)
        keyword = body.get('keyword')
        
        if not keyword or not keyword.strip():
            return JsonResponse({
                'error': 'Keyword parameter is required'
            }, status=400)
        
        keyword = keyword.strip()
        sort_by_price = body.get('sort_by_price', True)
        page = body.get('page', 0)
        use_price_update = body.get('use_price_update', False)
        
        if not isinstance(page, int):
            return JsonResponse({
                'error': 'Page parameter must be an integer'
            }, status=400)
        
        scraper = create_gemilang_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        if not result.success:
            return JsonResponse({
                'success': False,
                'error': result.error_message,
                'saved': 0,
                'updated': 0,
                'inserted': 0,
                'anomalies': []
            }, status=500)
        
        products_data = [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url,
                'unit': product.unit
            }
            for product in result.products
        ]
        
        if not products_data:
            return JsonResponse({
                'success': True,
                'message': 'No products found to save',
                'saved': 0,
                'updated': 0,
                'inserted': 0,
                'anomalies': []
            })
        
        db_service = GemilangDatabaseService()
        
        if use_price_update:
            save_result = db_service.save_with_price_update(products_data)
            return JsonResponse({
                'success': save_result['success'],
                'message': f"Updated {save_result['updated']} products, inserted {save_result['inserted']} new products",
                'saved': save_result['updated'] + save_result['inserted'],
                'updated': save_result['updated'],
                'inserted': save_result['inserted'],
                'anomalies': save_result['anomalies'],
                'anomaly_count': len(save_result['anomalies'])
            })
        else:
            save_success = db_service.save(products_data)
            if save_success:
                return JsonResponse({
                    'success': True,
                    'message': f"Successfully saved {len(products_data)} products",
                    'saved': len(products_data),
                    'updated': 0,
                    'inserted': len(products_data),
                    'anomalies': []
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to save products to database',
                    'saved': 0,
                    'updated': 0,
                    'inserted': 0,
                    'anomalies': []
                }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in scrape_and_save: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error occurred'
        }, status=500)
