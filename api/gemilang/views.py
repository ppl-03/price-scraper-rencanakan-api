from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import logging
from .logging_utils import get_gemilang_logger
import uuid
import time
from .logging_utils import get_gemilang_logger

from .factory import create_gemilang_scraper, create_gemilang_location_scraper
from .database_service import GemilangDatabaseService
from .security import (
    require_api_token,
    validate_input,
    enforce_resource_limits,
    InputValidator,
    SecurityDesignPatterns,
)
from .sentry_monitoring import (
    GemilangSentryMonitor,
    track_gemilang_transaction,
    GemilangTaskMonitor
)

logger = get_gemilang_logger("views")

# Constants
INTERNAL_SERVER_ERROR_MESSAGE = 'Internal server error occurred'


def _clean_location_name(location_name: str) -> str:
    if location_name.startswith('GEMILANG - '):
        return location_name.replace('GEMILANG - ', '', 1)
    return location_name


def _validate_page_param(x):
    if not x:
        return InputValidator.validate_integer(0, 'page', min_value=0, max_value=100)
    if str(x).lstrip('-').isdigit():
        return InputValidator.validate_integer(int(x), 'page', min_value=0, max_value=100)
    return (False, 'page must be a valid integer', None)


def _scrape_locations_with_monitoring():
    """Helper function to scrape locations with Sentry monitoring."""
    GemilangSentryMonitor.add_breadcrumb(
        "Starting location scraping",
        category="gemilang.location",
        level="info"
    )
    
    location_start_time = time.time()
    location_scraper = create_gemilang_location_scraper()
    location_result = location_scraper.scrape_locations(timeout=30)
    location_time = time.time() - location_start_time
    
    GemilangSentryMonitor.add_breadcrumb(
        f"Location scraping completed in {location_time:.2f}s - Found: {len(location_result.locations) if location_result.locations else 0}",
        category="gemilang.location",
        level="info" if location_result.success else "warning",
        data={
            "success": location_result.success,
            "locations_count": len(location_result.locations) if location_result.locations else 0,
            "duration": location_time
        }
    )
    
    return location_result, location_time


def _process_location_result(location_result):
    """Helper function to process location scraping result."""
    logger.info(
        f"[scrape_products] Location scraping - Success: {location_result.success}, "
        f"Count: {len(location_result.locations) if location_result.locations else 0}"
    )
    
    store_locations = []
    if location_result.success and location_result.locations:
        store_locations = [_clean_location_name(loc.name) for loc in location_result.locations]
        logger.info(f"[scrape_products] Found {len(store_locations)} locations")
    else:
        logger.warning(f"[scrape_products] No locations found - Success: {location_result.success}")
    
    all_stores_location = ", ".join(store_locations) if store_locations else ""
    logger.info(f"[scrape_products] Location string length: {len(all_stores_location)}")
    
    return all_stores_location


def _scrape_products_with_monitoring(keyword, sort_by_price, page, task):
    """Helper function to scrape products with Sentry monitoring."""
    GemilangSentryMonitor.add_breadcrumb(
        f"Starting product scraping for keyword: {keyword}",
        category="gemilang.scraper",
        level="info"
    )
    
    product_start_time = time.time()
    scraper = create_gemilang_scraper()
    result = scraper.scrape_products(
        keyword=keyword,
        sort_by_price=sort_by_price,
        page=page
    )
    product_time = time.time() - product_start_time
    
    task.record_progress(2, 2, "Product scraping completed")
    
    return result, product_time


@require_http_methods(["GET"])
@enforce_resource_limits
@validate_input({
    'keyword': lambda x: InputValidator.validate_keyword(x or '', max_length=100),
    'page': _validate_page_param,
    'sort_by_price': lambda x: InputValidator.validate_boolean(x, 'sort_by_price')
})
def scrape_products(request):
    # Start Sentry transaction for monitoring
    with track_gemilang_transaction("gemilang_scrape_products"):
        try:
            validated_data = request.validated_data
            keyword = validated_data.get('keyword')
            sort_by_price = validated_data.get('sort_by_price', True)
            page = validated_data.get('page', 0)
            
            # Set scraping context for Sentry
            GemilangSentryMonitor.set_scraping_context(
                keyword=keyword,
                page=page,
                additional_data={
                    'sort_by_price': sort_by_price,
                    'source': 'api_endpoint',
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Create task monitor for tracking
            task_id = f"scrape_{uuid.uuid4().hex[:8]}"
            task = GemilangTaskMonitor(task_id=task_id, task_type="product_scraping")
            
            # Scrape locations with monitoring
            location_result, location_time = _scrape_locations_with_monitoring()
            all_stores_location = _process_location_result(location_result)
            
            # Update task progress
            task.record_progress(1, 2, "Locations scraped, starting product scraping...")
            
            # Scrape products with monitoring
            result, product_time = _scrape_products_with_monitoring(keyword, sort_by_price, page, task)
            
            # Track scraping result
            scraping_result = {
                'products_count': len(result.products),
                'success': result.success,
                'errors_count': 0 if result.success else 1,
                'location_time': location_time,
                'product_time': product_time,
                'total_time': location_time + product_time
            }
            GemilangSentryMonitor.track_scraping_result(scraping_result)
            
            products_data = [
                {
                    'name': product.name,
                    'price': product.price,
                    'url': product.url,
                    'unit': product.unit,
                    'location': all_stores_location
                }
                for product in result.products
            ]
            
            response_data = {
                'success': result.success,
                'products': products_data,
                'error_message': result.error_message,
                'url': result.url
            }
            
            # Complete task
            task.complete(success=result.success, result_data=scraping_result)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Unexpected error in scraper: {type(e).__name__}")
            
            # Track error in Sentry
            GemilangSentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_products: {str(e)}",
                category="gemilang.error",
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return JsonResponse({
                'error': INTERNAL_SERVER_ERROR_MESSAGE
            }, status=500)


def _validate_timeout_param(x):
    """Helper function to validate timeout parameter."""
    if not x:
        return InputValidator.validate_integer(30, 'timeout', min_value=0, max_value=120)
    if str(x).lstrip('-').isdigit():
        return InputValidator.validate_integer(int(x), 'timeout', min_value=0, max_value=120)
    return (False, 'timeout must be a valid integer', None)


@require_http_methods(["GET"])
@validate_input({
    'timeout': _validate_timeout_param
})
def gemilang_locations_view(request):
    try:
        validated_data = request.validated_data
        timeout = validated_data.get('timeout', 30)
        
        scraper = create_gemilang_location_scraper()
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
        logger.error("Unexpected error in locations endpoint: %s", type(e).__name__)
        return JsonResponse({
            'success': False,
            'locations': [],
            'error_message': f'Unexpected error: {type(e).__name__}'
        }, status=500)


def _parse_request_body(request):
    """Parse and return JSON body or error response."""
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'Invalid JSON in request body'}, status=400)


def _validate_scrape_params(body):
    """Validate all scrape and save parameters."""
    keyword = body.get('keyword')
    is_valid, error_msg, sanitized_keyword = InputValidator.validate_keyword(
        keyword or '', max_length=100
    )
    if not is_valid:
        return None, JsonResponse({'error': error_msg}, status=400)
    
    page = body.get('page', 0)
    is_valid, error_msg, validated_page = InputValidator.validate_integer(
        page, 'page', min_value=0, max_value=100
    )
    if not is_valid:
        return None, JsonResponse({'error': error_msg}, status=400)
    
    sort_by_price = body.get('sort_by_price', True)
    is_valid, error_msg, validated_sort = InputValidator.validate_boolean(
        sort_by_price, 'sort_by_price'
    )
    if not is_valid:
        return None, JsonResponse({'error': error_msg}, status=400)
    
    use_price_update = body.get('use_price_update', False)
    is_valid, error_msg, validated_update = InputValidator.validate_boolean(
        use_price_update, 'use_price_update'
    )
    if not is_valid:
        return None, JsonResponse({'error': error_msg}, status=400)
    
    return {
        'keyword': sanitized_keyword,
        'page': validated_page,
        'sort_by_price': validated_sort,
        'use_price_update': validated_update
    }, None


def _validate_products_business_logic(products_data):
    """Validate business logic for all products."""
    for idx, product in enumerate(products_data):
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(product)
        if not is_valid:
            return JsonResponse({'error': f'Product {idx}: {error_msg}'}, status=400)
    return None


def _handle_price_update_save(db_service, products_data):
    """Handle database save with price update."""
    save_result = db_service.save_with_price_update(products_data)
    
    if not save_result.get('success', False):
        return JsonResponse({
            'success': False,
            'error': save_result.get('error', 'Failed to save products'),
            'saved': 0,
            'updated': 0,
            'inserted': 0,
            'anomalies': []
        }, status=500)
    
    return JsonResponse({
        'success': True,
        'message': f"Updated {save_result['updated']} products, inserted {save_result['inserted']} new products",
        'saved': save_result['updated'] + save_result['inserted'],
        'updated': save_result['updated'],
        'inserted': save_result['inserted'],
        'anomalies': save_result.get('anomalies', []),
        'anomaly_count': len(save_result.get('anomalies', []))
    })


def _handle_regular_save(db_service, products_data):
    """Handle regular database save."""
    save_result = db_service.save(products_data)
    
    if isinstance(save_result, tuple):
        save_success, error_msg = save_result
    else:
        save_success = save_result
        error_msg = 'Failed to save products to database'
    
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
            'error': error_msg,
            'saved': 0,
            'updated': 0,
            'inserted': 0,
            'anomalies': []
        }, status=500)


def _fetch_store_locations():
    """Helper to fetch and process store locations"""
    location_scraper = create_gemilang_location_scraper()
    location_result = location_scraper.scrape_locations(timeout=30)
    
    logger.info(
        "Location scraping result - Success: %s, Locations count: %s",
        location_result.success,
        len(location_result.locations) if location_result.locations else 0
    )
    
    if not location_result.success:
        logger.error("Location scraping failed with error: %s", location_result.error_message)
        return ""
    
    if not location_result.locations:
        logger.warning("No locations found, will save without locations")
        return ""
    
    store_locations = [_clean_location_name(loc.name) for loc in location_result.locations]
    logger.info("Found %s Gemilang store locations: %s", len(store_locations), store_locations[:3])
    
    all_stores_location = ", ".join(store_locations)
    logger.info(
        "Final location string length: %s, Preview: %s",
        len(all_stores_location),
        all_stores_location[:200]
    )
    
    return all_stores_location


def _categorize_products(products_data):
    """Helper to categorize products"""
    from db_pricing.categorization import ProductCategorizer
    categorizer = ProductCategorizer()
    
    for product in products_data:
        category = categorizer.categorize(product['name'])
        product['category'] = category if category else None
        logger.info("Categorized '%s' as '%s'", product['name'], category)


@require_http_methods(["POST"])
@require_api_token(required_permission='write')
@enforce_resource_limits
def scrape_and_save(request):
    try:
        body, error_response = _parse_request_body(request)
        if error_response:
            return error_response
        
        params, error_response = _validate_scrape_params(body)
        if error_response:
            return error_response
        
        all_stores_location = _fetch_store_locations()
        
        scraper = create_gemilang_scraper()
        result = scraper.scrape_products(
            keyword=params['keyword'],
            sort_by_price=params['sort_by_price'],
            page=params['page']
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
                'unit': product.unit,
                'location': all_stores_location
            }
            for product in result.products
        ]
        
        logger.info(
            "Prepared %s products with location: %s...",
            len(products_data),
            all_stores_location[:100]
        )
        
        if not products_data:
            return JsonResponse({
                'success': True,
                'message': 'No products found to save',
                'saved': 0,
                'updated': 0,
                'inserted': 0,
                'anomalies': []
            })
        
        error_response = _validate_products_business_logic(products_data)
        if error_response:
            return error_response
        
        _categorize_products(products_data)
        
        db_service = GemilangDatabaseService()
        
        if params['use_price_update']:
            return _handle_price_update_save(db_service, products_data)
        
        return _handle_regular_save(db_service, products_data)
        
    except Exception as e:
        logger.error("Unexpected error in scraper: %s", type(e).__name__)
        return JsonResponse({
            'error': INTERNAL_SERVER_ERROR_MESSAGE
        }, status=500)

@require_http_methods(["GET"])
def scrape_popularity(request):
    try:
        keyword = request.GET.get('keyword', '').strip()
        page = int(request.GET.get('page', 0))

        if not keyword:
            return JsonResponse({'error': 'Keyword is required'}, status=400)

        if page < 0:
            return JsonResponse({'error': 'Page must be a non-negative integer'}, status=400)

        scraper = create_gemilang_scraper()
        # For popularity we just set sort_by_price to False so url_builder uses sort=new
        result = scraper.scrape_products(keyword=keyword, sort_by_price=False, page=page)

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
        logger.error("Unexpected error in scraper: %s", type(e).__name__)
        return JsonResponse({
            'error': INTERNAL_SERVER_ERROR_MESSAGE
        }, status=500)
