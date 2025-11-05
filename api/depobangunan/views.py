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


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        # Validate and parse parameters
        keyword, error = _validate_and_parse_keyword(request.GET.get('keyword'))
        if error:
            return error
        
        sort_by_price = _parse_sort_by_price(request.GET.get('sort_by_price', 'true'))
        
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
            'url': result.url
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
        # Validate and parse parameters
        keyword, error = _validate_and_parse_keyword(request.POST.get('keyword'))
        if error:
            return error
        
        sort_by_price = _parse_sort_by_price(request.POST.get('sort_by_price', 'true'))
        
        page, error = _parse_page(request.POST.get('page', '0'))
        if error:
            return error
        
        scraper = create_depo_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        if not result.success:
            return _create_error_response(f'Scraping failed: {result.error_message}', 500)
        
        if not result.products:
            return JsonResponse({
                'success': True,
                'message': 'No products found to save',
                'scraped_count': 0,
                'saved_count': 0
            })
        
        products_data = _convert_products_to_dict(result.products)
        
        db_service = DepoBangunanDatabaseService()
        save_result = db_service.save(products_data)
        
        if not save_result:
            return _create_error_response('Failed to save products to database', 500)
        
        response_data = {
            'success': True,
            'message': 'Products scraped and saved successfully',
            'scraped_count': len(products_data),
            'saved_count': len(products_data),
            'url': result.url
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in scrape and save: {str(e)}")
        return _create_error_response(ERROR_INTERNAL_SERVER, 500)
