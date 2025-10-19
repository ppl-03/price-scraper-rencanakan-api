from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from typing import Optional, Tuple
from .factory import create_tokopedia_scraper


def _create_error_response(error_message: str, status: int = 400) -> JsonResponse:
    """Create a standardized error response"""
    return JsonResponse({
        'success': False,
        'products': [],
        'error_message': error_message,
        'url': ''
    }, status=status)


def _validate_query_parameter(request) -> Tuple[Optional[str], Optional[JsonResponse]]:
    """
    Validate and extract query parameter from request
    
    Returns:
        Tuple of (query_string, error_response)
        If validation passes: (query, None)
        If validation fails: (None, error_response)
    """
    query = request.GET.get('q')
    
    if query is None:
        return None, _create_error_response('Query parameter is required')
    
    if not query.strip():
        return None, _create_error_response('Query parameter cannot be empty')
    
    return query.strip(), None


def _parse_boolean_parameter(request, param_name: str, default: str = 'true') -> bool:
    """Parse a boolean parameter from request"""
    param_value = request.GET.get(param_name, default).lower()
    return param_value in ['true', '1', 'yes']


def _parse_integer_parameter(
    request, 
    param_name: str, 
    default: Optional[str] = None, 
    required: bool = False
) -> Tuple[Optional[int], Optional[JsonResponse]]:
    """
    Parse an integer parameter from request
    
    Returns:
        Tuple of (integer_value, error_response)
        If parsing succeeds: (value, None)
        If parsing fails: (None, error_response)
    """
    param_value = request.GET.get(param_name)
    
    if param_value is None:
        if required:
            return None, _create_error_response(f'{param_name} parameter is required')
        # Use default if provided, otherwise return None
        if default is not None:
            try:
                return int(default), None
            except ValueError:
                return None, None
        return None, None
    
    try:
        return int(param_value), None
    except ValueError:
        return None, _create_error_response(
            f'{param_name} parameter must be a valid integer'
        )


def _format_scrape_result(result) -> dict:
    """Format scraper result into response dictionary"""
    return {
        'success': result.success,
        'products': [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url
            }
            for product in result.products
        ],
        'url': result.url,
        'error_message': result.error_message
    }


@require_http_methods(["GET"])
def scrape_products(request):
    """Scrape products with basic parameters (query, sort, page)"""
    try:
        # Validate query parameter
        query, error = _validate_query_parameter(request)
        if error:
            return error
        
        # Parse sort_by_price parameter
        sort_by_price = _parse_boolean_parameter(request, 'sort_by_price', 'true')
        
        # Parse page parameter
        page, error = _parse_integer_parameter(request, 'page', '0')
        if error:
            return error
        
        # Perform scraping
        scraper = create_tokopedia_scraper()
        result = scraper.scrape_products(
            keyword=query,
            sort_by_price=sort_by_price,
            page=page
        )
        
        # Format and return response
        return JsonResponse(_format_scrape_result(result))
        
    except Exception as e:
        return _create_error_response(
            f"Tokopedia scraper error: {str(e)}", 
            status=500
        )


@require_http_methods(["GET"])
def scrape_products_with_filters(request):
    """Scrape products with advanced filters (price range, location)"""
    try:
        # Validate query parameter
        query, error = _validate_query_parameter(request)
        if error:
            return error
        
        # Parse sort_by_price parameter
        sort_by_price = _parse_boolean_parameter(request, 'sort_by_price', 'true')
        
        # Parse page parameter
        page, error = _parse_integer_parameter(request, 'page', '0')
        if error:
            return error
        
        # Parse optional price filter parameters
        min_price, error = _parse_integer_parameter(request, 'min_price', required=False)
        if error:
            return error
        
        max_price, error = _parse_integer_parameter(request, 'max_price', required=False)
        if error:
            return error
        
        # Get location parameter (string, no validation needed)
        location = request.GET.get('location')
        
        # Perform scraping with filters
        scraper = create_tokopedia_scraper()
        result = scraper.scrape_products_with_filters(
            keyword=query,
            sort_by_price=sort_by_price,
            page=page,
            min_price=min_price,
            max_price=max_price,
            location=location
        )
        
        # Format and return response
        return JsonResponse(_format_scrape_result(result))
        
    except Exception as e:
        return _create_error_response(
            f"Tokopedia scraper with filters error: {str(e)}", 
            status=500
        )