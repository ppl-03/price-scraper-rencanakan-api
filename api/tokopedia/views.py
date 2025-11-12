from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from typing import Optional, Tuple
from .factory import create_tokopedia_scraper
from .database_service import TokopediaDatabaseService
import re
from .url_builder_ulasan import TokopediaUrlBuilderUlasan
from .http_client import TokopediaHttpClient
from .html_parser import TokopediaHtmlParser
from .scraper import TokopediaPriceScraper

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


def _format_scrape_result(result, db_result=None) -> dict:
    """Format scraper result into response dictionary.

    Ensures all product fields are JSON-serializable. In particular, avoid
    leaking MagicMock instances (from tests) into the JSON encoder which would
    raise a serialization error and cause a 500 response.
    
    Args:
        result: ScrapingResult from the scraper
        db_result: Optional database save result
    """

    def _safe_value(value):
        # Allow only primitive JSON types; coerce everything else to None
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return None

    products = []
    for product in result.products:
        products.append({
            'name': _safe_value(getattr(product, 'name', None)),
            'price': _safe_value(getattr(product, 'price', None)),
            'url': _safe_value(getattr(product, 'url', None)),
            'location': _safe_value(getattr(product, 'location', None)),
            'unit': _safe_value(getattr(product, 'unit', None)),
        })

    response = {
        'success': bool(getattr(result, 'success', False)),
        'products': products,
        'url': _safe_value(getattr(result, 'url', '')),
        'error_message': _safe_value(getattr(result, 'error_message', None)),
    }
    
    # Add database save information if available
    if db_result:
        response['database'] = {
            'saved': db_result.get('success', False),
            'inserted': db_result.get('inserted', 0),
            'updated': db_result.get('updated', 0),
            'anomalies': db_result.get('anomalies', [])
        }
    
    return response


def _save_products_to_database(products) -> dict:
    """
    Save scraped products to database.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        Database operation result
    """
    if not products:
        return {'success': False, 'updated': 0, 'inserted': 0, 'anomalies': []}
    
    try:
        db_service = TokopediaDatabaseService()
        return db_service.save_with_price_update(products)
    except Exception as e:
        # Log the error but don't fail the entire request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Database save error: {str(e)}")
        return {'success': False, 'updated': 0, 'inserted': 0, 'anomalies': []}


def _convert_products_to_dict(products) -> list:
    """
    Convert Product objects to dictionary format for database storage.
    
    Args:
        products: List of Product objects
        
    Returns:
        List of product dictionaries
    """
    products_data = []
    for product in products:
        products_data.append({
            'name': product.name if product.name else '',
            'price': product.price if product.price else 0,
            'url': product.url if product.url else '',
            'unit': product.unit if (hasattr(product, 'unit') and product.unit) else '',
            'location': product.location if (hasattr(product, 'location') and product.location) else ''
        })
    return products_data


def _parse_common_parameters(request) -> Tuple[Optional[dict], Optional[JsonResponse]]:
    """
    Parse common parameters shared by both scrape endpoints.
    
    Args:
        request: Django request object
        
    Returns:
        Tuple of (parameters_dict, error_response)
        If parsing succeeds: (params, None)
        If parsing fails: (None, error_response)
    """
    # Validate query parameter
    query, error = _validate_query_parameter(request)
    if error:
        return None, error
    
    # Parse sort_by_price parameter
    sort_by_price = _parse_boolean_parameter(request, 'sort_by_price', DEFAULT_SORT_BY_PRICE)
    
    # Parse page parameter
    page, error = _parse_integer_parameter(request, 'page', DEFAULT_PAGE, min_value=MIN_PAGE)
    if error:
        return None, error
    
    # Parse optional limit parameter
    limit, error = _parse_integer_parameter(
        request, 'limit', default=DEFAULT_LIMIT, required=False, min_value=MIN_LIMIT, max_value=MAX_LIMIT
    )
    if error:
        return None, error
    
    return {
        'query': query,
        'sort_by_price': sort_by_price,
        'page': page,
        'limit': limit
    }, None


def _handle_scraping_result(result):
    """
    Process scraping result and save to database if successful.
    
    Args:
        result: ScrapingResult from the scraper
        
    Returns:
        Tuple of (result, db_result)
    """
    db_result = None
    if result.success and result.products:
        products_data = _convert_products_to_dict(result.products)
        db_result = _save_products_to_database(products_data)
    return result, db_result


@require_http_methods(["GET"])
def scrape_products(request):
    """Scrape products with basic parameters (query, sort, page, limit)"""
    try:
        # Parse common parameters
        params, error = _parse_common_parameters(request)
        if error:
            return error
        
        # Perform scraping
        scraper = create_tokopedia_scraper()
        result = scraper.scrape_products(
            keyword=params['query'],
            sort_by_price=params['sort_by_price'],
            page=params['page'],
            limit=params['limit']
        )
        
        # Handle result and save to database
        result, db_result = _handle_scraping_result(result)
        
        # Format and return response
        return JsonResponse(_format_scrape_result(result, db_result))
        
    except Exception as e:
        return _create_error_response(
            f"Tokopedia scraper error: {str(e)}", 
            status=500
        )


def _parse_filter_parameters(request) -> Tuple[Optional[dict], Optional[JsonResponse]]:
    """
    Parse filter-specific parameters (price range, location).
    
    Args:
        request: Django request object
        
    Returns:
        Tuple of (filters_dict, error_response)
        If parsing succeeds: (filters, None)
        If parsing fails: (None, error_response)
    """
    # Parse optional price filter parameters
    min_price, error = _parse_integer_parameter(request, 'min_price', required=False, min_value=MIN_PRICE)
    if error:
        return None, error
    
    max_price, error = _parse_integer_parameter(request, 'max_price', required=False, min_value=MIN_PRICE)
    if error:
        return None, error
    
    # Get location parameter (string, sanitize for safety)
    location_raw = request.GET.get('location')
    location = _sanitize_string(location_raw, max_length=50) if location_raw else None
    
    return {
        'min_price': min_price,
        'max_price': max_price,
        'location': location
    }, None


@require_http_methods(["GET"])
def scrape_products_with_filters(request):
    """Scrape products with advanced filters (price range, location, limit)"""
    try:
        # Parse common parameters
        params, error = _parse_common_parameters(request)
        if error:
            return error
        
        # Parse filter parameters
        filters, error = _parse_filter_parameters(request)
        if error:
            return error
        
        # Perform scraping with filters
        scraper = create_tokopedia_scraper()
        result = scraper.scrape_products_with_filters(
            keyword=params['query'],
            sort_by_price=params['sort_by_price'],
            page=params['page'],
            min_price=filters['min_price'],
            max_price=filters['max_price'],
            location=filters['location'],
            limit=params['limit']
        )
        
        # Handle result and save to database
        result, db_result = _handle_scraping_result(result)
        
        # Format and return response
        return JsonResponse(_format_scrape_result(result, db_result))
        
    except Exception as e:
        return _create_error_response(
            f"Tokopedia scraper with filters error: {str(e)}", 
            status=500
        )


@require_http_methods(["GET"])
def scrape_products_ulasan(request):
    """Scrape products sorted by 'ulasan' (popularity/reviews).

    This endpoint uses `TokopediaUrlBuilderUlasan` which sets the
    Tokopedia `ob=5` parameter. It mirrors `scrape_products_with_filters`
    but forces the ulasan/popularity ordering.
    """
    try:
        # Parse common parameters
        params, error = _parse_common_parameters(request)
        if error:
            return error

        # Parse filter parameters
        filters, error = _parse_filter_parameters(request)
        if error:
            return error

        # Build a scraper that uses the ulasan URL builder
        http_client = TokopediaHttpClient()
        url_builder = TokopediaUrlBuilderUlasan()
        html_parser = TokopediaHtmlParser()
        scraper = TokopediaPriceScraper(http_client, url_builder, html_parser)

        # Use sort_by_price=False so the ulasan builder emits ob=5
        result = scraper.scrape_products_with_filters(
            keyword=params['query'],
            sort_by_price=False,
            page=params['page'],
            min_price=filters['min_price'],
            max_price=filters['max_price'],
            location=filters['location'],
            limit=params['limit']
        )

        # Handle result and save to database
        result, db_result = _handle_scraping_result(result)

        # Format and return response
        return JsonResponse(_format_scrape_result(result, db_result))

    except Exception as e:
        return _create_error_response(
            f"Tokopedia scraper (ulasan) error: {str(e)}",
            status=500
        )
