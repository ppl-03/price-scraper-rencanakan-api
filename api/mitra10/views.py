from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_mitra10_scraper, create_mitra10_location_scraper
from .database_service import Mitra10DatabaseService
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
    """Validate API token from request headers"""
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
        query = request.GET.get('q')
        if query is None:
            return JsonResponse({
                'success': False,
                'products': [],
                'error_message': 'Query parameter is required',
                'url': ''
            }, status=400)
        
        if not query.strip():
            return JsonResponse({
                'success': False,
                'products': [],
                'error_message': 'Query parameter cannot be empty',
                'url': ''
            }, status=400)
        
        query = query.strip()
        
        # Parse sort_by_price parameter
        sort_by_price_param = request.GET.get('sort_by_price', 'true').lower()
        sort_by_price = sort_by_price_param in ['true', '1', 'yes']
        
        # Parse page parameter
        page_param = request.GET.get('page', '0')
        try:
            page = int(page_param)
        except ValueError:
            return JsonResponse({
                'success': False,
                'products': [],
                'error_message': 'Page parameter must be a valid integer',
                'url': ''
            }, status=400)
        
        # Create scraper and scrape products
        scraper = create_mitra10_scraper()
        result = scraper.scrape_products(
            keyword=query,
            sort_by_price=sort_by_price,
            page=page
        )
        
        # Format products data
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
        
        logger.info(f"Mitra10 scraping successful for query '{query}': {len(result.products)} products found")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in scrape_products: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'products': [],
            'error_message': f'Internal server error: {str(e)}',
            'url': ''
        }, status=500)

@require_http_methods(["GET"])
def scrape_locations(request):
    """Django view to scrape Mitra10 store locations."""
    try:
        scraper = create_mitra10_location_scraper()
        result = scraper.scrape_locations()

        # Result is a dict with 'success', 'locations', 'error_message'
        # Locations are returned as strings (location names)
        if result['success'] and result['locations']:
            locations_data = []
            for idx, location in enumerate(result['locations'], 1):
                if isinstance(location, str):
                    locations_data.append({
                        'name': location,
                        'code': f'MITRA10_{idx}'
                    })
                elif isinstance(location, dict):
                    locations_data.append(location)
                else:
                    locations_data.append({
                        'name': getattr(location, 'name', str(location)),
                        'code': getattr(location, 'code', f'MITRA10_{idx}')
                    })
        else:
            locations_data = []

        return JsonResponse({
            "success": result['success'],
            "locations": locations_data,
            "count": len(locations_data),
            "error_message": result['error_message']
        })

    except Exception as e:
        logger.error(f"Error in scrape_locations: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'locations': [],
            'count': 0,
            'error_message': f'Internal server error: {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
def scrape_and_save_products(request):
    # Validate API token
    is_valid, error_message = _validate_api_token(request)
    if not is_valid:
        return JsonResponse({
            'success': False,
            'inserted': 0,
            'updated': 0,
            'anomalies': [],
            'error_message': error_message
        }, status=401)
    
    try:
        query = request.GET.get('q')
        if query is None:
            return JsonResponse({
                'success': False,
                'inserted': 0,
                'updated': 0,
                'anomalies': [],
                'error_message': 'Query parameter is required'
            }, status=400)
        
        if not query.strip():
            return JsonResponse({
                'success': False,
                'inserted': 0,
                'updated': 0,
                'anomalies': [],
                'error_message': 'Query parameter cannot be empty'
            }, status=400)
        
        query = query.strip()
        
        sort_by_price_param = request.GET.get('sort_by_price', 'true').lower()
        sort_by_price = sort_by_price_param in ['true', '1', 'yes']
        
        page_param = request.GET.get('page', '0')
        try:
            page = int(page_param)
        except ValueError:
            return JsonResponse({
                'success': False,
                'inserted': 0,
                'updated': 0,
                'anomalies': [],
                'error_message': 'Page parameter must be a valid integer'
            }, status=400)
        
        try:
            scraper = create_mitra10_scraper()
            result = scraper.scrape_products(
                keyword=query,
                sort_by_price=sort_by_price,
                page=page
            )
        except Exception as e:
            logger.error(f"Scraping error: {str(e)}")
            return JsonResponse({
                'success': False,
                'inserted': 0,
                'updated': 0,
                'anomalies': [],
                'error_message': f'Scraping failed: {str(e)}'
            }, status=500)
        
        if not result.success:
            return JsonResponse({
                'success': False,
                'inserted': 0,
                'updated': 0,
                'anomalies': [],
                'error_message': result.error_message
            }, status=400)
        
        products_data = [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url,
                'unit': product.unit
            }
            for product in result.products
        ]
        
        try:
            service = Mitra10DatabaseService()
            save_result = service.save_with_price_update(products_data)
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return JsonResponse({
                'success': False,
                'inserted': 0,
                'updated': 0,
                'anomalies': [],
                'error_message': f'Database error: {str(e)}'
            }, status=500)
        
        logger.info(f"Mitra10 saved {save_result['inserted']} new, updated {save_result['updated']}, detected {len(save_result['anomalies'])} anomalies for query '{query}'")
        
        return JsonResponse({
            'success': save_result['success'],
            'inserted': save_result['inserted'],
            'updated': save_result['updated'],
            'anomalies': save_result['anomalies'],
            'total_products': len(products_data),
            'error_message': ''
        })
        
    except Exception as e:
        logger.error(f"Error in scrape_and_save_products: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'inserted': 0,
            'updated': 0,
            'anomalies': [],
            'error_message': f'Internal server error: {str(e)}'
        }, status=500)
    