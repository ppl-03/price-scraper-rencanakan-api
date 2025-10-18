"""
Shared utilities for scraper API views.
"""
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def validate_scraping_request(request):
    """
    Validate common scraping request parameters.
    
    Returns:
        tuple: (keyword, sort_by_price, page, error_response)
        If validation fails, error_response will contain the JsonResponse to return.
    """
    keyword = request.GET.get('keyword')
    if not keyword or not keyword.strip():
        return None, None, None, JsonResponse({
            'error': 'Keyword parameter is required'
        }, status=400)
    
    keyword = keyword.strip()
    
    # Parse sort_by_price parameter
    sort_by_price_param = request.GET.get('sort_by_price', 'true').lower()
    sort_by_price = sort_by_price_param in ['true', '1', 'yes']
    
    # Parse page parameter
    page_param = request.GET.get('page', '0')
    try:
        page = int(page_param)
    except ValueError:
        return None, None, None, JsonResponse({
            'error': 'Page parameter must be a valid integer'
        }, status=400)
    
    return keyword, sort_by_price, page, None


def format_scraping_response(result):
    """
    Format scraping result into standard JSON response.
    
    Args:
        result: ScrapingResult object
        
    Returns:
        dict: Formatted response data
    """
    products_data = [
        {
            'name': product.name,
            'price': product.price,
            'url': product.url,
            'unit': product.unit if product.unit else None
        }
        for product in result.products
    ]
    
    return {
        'success': result.success,
        'products': products_data,
        'error_message': result.error_message,
        'url': result.url
    }


def handle_scraping_exception(e, scraper_name="scraper"):
    """
    Handle exceptions that occur during scraping.
    
    Args:
        e: Exception that occurred
        scraper_name: Name of the scraper for logging
        
    Returns:
        JsonResponse: Error response
    """
    logger.error(f"Unexpected error in {scraper_name}: {str(e)}")
    return JsonResponse({
        'error': 'Internal server error occurred'
    }, status=500)