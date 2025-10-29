from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from typing import Optional, Tuple
from .factory import create_tokopedia_scraper
import re

# Constants
DEFAULT_LIMIT = '20'
DEFAULT_PAGE = '0'
DEFAULT_SORT_BY_PRICE = 'true'
MAX_LIMIT = 1000
MIN_LIMIT = 1
MIN_PAGE = 0
MIN_PRICE = 0
MAX_QUERY_LENGTH = 200  # Maximum allowed query length


def _sanitize_string(value: str, max_length: int = MAX_QUERY_LENGTH) -> str:
    """
    Sanitize user input string to prevent injection attacks
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not value:
        return ""
    
    # Trim to max length
    sanitized = value[:max_length]
    
    # Remove any control characters and strip whitespace
    sanitized = ''.join(char for char in sanitized if char.isprintable() or char.isspace())
    sanitized = sanitized.strip()
    
    return sanitized


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
    Validate and extract query parameter from request with sanitization
    
    Returns:
        Tuple of (query_string, error_response)
        If validation passes: (query, None)
        If validation fails: (None, error_response)
    """
    query = request.GET.get('q')
    
    if query is None:
        return None, _create_error_response('Query parameter is required')
    
    # Sanitize the query to prevent injection attacks
    sanitized_query = _sanitize_string(query)
    
    if not sanitized_query:
        return None, _create_error_response('Query parameter cannot be empty')
    
    return sanitized_query, None


def _parse_boolean_parameter(request, param_name: str, default: str = DEFAULT_SORT_BY_PRICE) -> bool:
    """Parse a boolean parameter from request"""
    param_value = request.GET.get(param_name, default).lower()
    return param_value in ['true', '1', 'yes']


def _validate_integer_range(value: int, param_name: str, min_value: Optional[int], 
                           max_value: Optional[int]) -> Optional[JsonResponse]:
    """Validate integer is within allowed range"""
    if min_value is not None and value < min_value:
        return _create_error_response(f'{param_name} must be at least {min_value}')
    if max_value is not None and value > max_value:
        return _create_error_response(f'{param_name} must not exceed {max_value}')
    return None


def _parse_default_value(default: str, min_value: Optional[int], 
                         max_value: Optional[int]) -> Optional[int]:
    """Parse and clamp default value"""
    try:
        value = int(default)
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value
        return value
    except ValueError:
        return None


def _parse_integer_parameter(
    request, 
    param_name: str, 
    default: Optional[str] = None, 
    required: bool = False,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None
) -> Tuple[Optional[int], Optional[JsonResponse]]:
    """
    Parse an integer parameter from request with optional range validation
    Sanitizes input to prevent injection attacks
    
    Returns:
        Tuple of (integer_value, error_response)
        If parsing succeeds: (value, None)
        If parsing fails: (None, error_response)
    """
    param_value = request.GET.get(param_name)
    
    if param_value is None:
        if required:
            return None, _create_error_response(f'{param_name} parameter is required')
        if default is not None:
            value = _parse_default_value(default, min_value, max_value)
            return value, None
        return None, None
    
    # Sanitize parameter value to prevent injection
    sanitized_value = _sanitize_string(param_value, max_length=20)
    
    # Validate it contains only digits (and optional minus sign)
    if not re.match(r'^-?\d+$', sanitized_value):
        return None, _create_error_response(
            f'{param_name} parameter must be a valid integer'
        )
    
    try:
        value = int(sanitized_value)
        error = _validate_integer_range(value, param_name, min_value, max_value)
        if error:
            return None, error
        return value, None
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
                'url': product.url,
                'location': product.location
            }
            for product in result.products
        ],
        'url': result.url,
        'error_message': result.error_message
    }


@require_http_methods(["GET"])
def scrape_products(request):
    """Scrape products with basic parameters (query, sort, page, limit)"""
    try:
        # Validate query parameter
        query, error = _validate_query_parameter(request)
        if error:
            return error
        
        # Parse sort_by_price parameter
        sort_by_price = _parse_boolean_parameter(request, 'sort_by_price', DEFAULT_SORT_BY_PRICE)
        
        # Parse page parameter
        page, error = _parse_integer_parameter(request, 'page', DEFAULT_PAGE, min_value=MIN_PAGE)
        if error:
            return error
        
        # Parse optional limit parameter (default to 20 products, max 1000 for security)
        limit, error = _parse_integer_parameter(
            request, 'limit', default=DEFAULT_LIMIT, required=False, min_value=MIN_LIMIT, max_value=MAX_LIMIT
        )
        if error:
            return error
        
        # Perform scraping
        scraper = create_tokopedia_scraper()
        result = scraper.scrape_products(
            keyword=query,
            sort_by_price=sort_by_price,
            page=page,
            limit=limit
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
    """Scrape products with advanced filters (price range, location, limit)"""
    try:
        # Validate query parameter
        query, error = _validate_query_parameter(request)
        if error:
            return error
        
        # Parse sort_by_price parameter
        sort_by_price = _parse_boolean_parameter(request, 'sort_by_price', DEFAULT_SORT_BY_PRICE)
        
        # Parse page parameter
        page, error = _parse_integer_parameter(request, 'page', DEFAULT_PAGE, min_value=MIN_PAGE)
        if error:
            return error
        
        # Parse optional price filter parameters
        min_price, error = _parse_integer_parameter(request, 'min_price', required=False, min_value=MIN_PRICE)
        if error:
            return error
        
        max_price, error = _parse_integer_parameter(request, 'max_price', required=False, min_value=MIN_PRICE)
        if error:
            return error
        
        # Parse optional limit parameter (default to 20 products, max 1000 for security)
        limit, error = _parse_integer_parameter(
            request, 'limit', default=DEFAULT_LIMIT, required=False, min_value=MIN_LIMIT, max_value=MAX_LIMIT
        )
        if error:
            return error
        
        # Get location parameter (string, sanitize for safety)
        location_raw = request.GET.get('location')
        location = _sanitize_string(location_raw, max_length=50) if location_raw else None
        
        # Perform scraping with filters
        scraper = create_tokopedia_scraper()
        result = scraper.scrape_products_with_filters(
            keyword=query,
            sort_by_price=sort_by_price,
            page=page,
            min_price=min_price,
            max_price=max_price,
            location=location,
            limit=limit
        )
        
        # Format and return response
        return JsonResponse(_format_scrape_result(result))
        
    except Exception as e:
        return _create_error_response(
            f"Tokopedia scraper with filters error: {str(e)}", 
            status=500
        )