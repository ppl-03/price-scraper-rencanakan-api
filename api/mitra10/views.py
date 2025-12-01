from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_mitra10_scraper, create_mitra10_location_scraper
from .database_service import Mitra10DatabaseService
from .security import SecurityDesignPatterns, enforce_resource_limits, validate_input, InputValidator, require_api_token
from db_pricing.models import Mitra10Product
from db_pricing.auto_categorization_service import AutoCategorizationService
from .sentry_monitoring import (
    Mitra10SentryMonitor,
    track_mitra10_transaction,
    Mitra10TaskMonitor
)
from .logging_utils import get_mitra10_logger
import logging
import uuid
import time

logger = get_mitra10_logger("views")

# Error message constants
ERROR_QUERY_REQUIRED = 'Query parameter is required'
ERROR_QUERY_EMPTY = 'Query parameter cannot be empty'
ERROR_PAGE_INVALID = 'Page parameter must be a valid integer'

# Sentry breadcrumb category constants
BREADCRUMB_CATEGORY_SCRAPER = 'mitra10.scraper'
BREADCRUMB_CATEGORY_ERROR = 'mitra10.error'
BREADCRUMB_CATEGORY_LOCATION = 'mitra10.location'
BREADCRUMB_CATEGORY_DATABASE = 'mitra10.database'

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
        try:
            logger.warning(
                "Invalid API token attempt from %s",
                client_ip,
                extra={"operation": "_validate_api_token"}
            )
        except Exception:
            # Don't let logging failures block auth flow
            pass
        return False, 'Invalid API token'

    token_info = API_TOKENS[token]
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    allowed_ips = token_info.get('allowed_ips', [])

    if allowed_ips and client_ip not in allowed_ips:
        try:
            logger.warning(
                "IP %s not allowed for token %s",
                client_ip, token_info['name'],
                extra={"operation": "_validate_api_token"}
            )
        except Exception:
            pass
        return False, 'IP not authorized'

    try:
        logger.info(
            "Valid API token used from %s: %s",
            client_ip, token_info['name'],
            extra={"operation": "_validate_api_token"}
        )
    except Exception:
        # Swallow logging errors to allow request to proceed
        pass
    return True, ''


def _validate_sort_by_price(v):
    """Validate sort_by_price parameter."""
    if v is None:
        return (True, '', True)
    if isinstance(v, str) and v.lower() in ['true', '1', 'yes', 'false', '0', 'no']:
        return InputValidator.validate_boolean(v, 'sort_by_price')
    return (True, '', False)

@require_http_methods(["GET"])
@validate_input({
    'q': lambda v: InputValidator.validate_keyword(v or '', max_length=100),
    'page': lambda v: (False, 'page must be a valid integer', None) if v == '' else InputValidator.validate_integer(v or '0', 'page', min_value=0, max_value=1000),
    'sort_by_price': _validate_sort_by_price
})
@enforce_resource_limits
def scrape_products(request):
    # Start Sentry transaction for monitoring
    with track_mitra10_transaction("mitra10_scrape_products"):
        try:
            query = request.validated_data.get('q')
            page = request.validated_data.get('page', 0)
            sort_by_price = request.validated_data.get('sort_by_price', True)
            
            # Set scraping context for Sentry
            Mitra10SentryMonitor.set_scraping_context(
                keyword=query,
                page=page,
                additional_data={
                    'sort_by_price': sort_by_price,
                    'source': 'api_endpoint',
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Create task monitor for tracking
            task_id = f"scrape_{uuid.uuid4().hex[:8]}"
            task = Mitra10TaskMonitor(task_id=task_id, task_type="product_scraping")
            
            # Track scraping start
            Mitra10SentryMonitor.add_breadcrumb(
                f"Starting product scraping for keyword: {query}",
                category=BREADCRUMB_CATEGORY_SCRAPER,
                level="info"
            )
            
            scraping_start_time = time.time()
            
            # Create scraper and scrape products
            scraper = create_mitra10_scraper()
            result = scraper.scrape_products(
                keyword=query,
                sort_by_price=sort_by_price,
                page=page
            )
            
            scraping_time = time.time() - scraping_start_time
        
            # Track scraping result
            scraping_result = {
                'products_count': len(result.products),
                'success': result.success,
                'errors_count': 0 if result.success else 1,
                'scraping_time': scraping_time
            }
            Mitra10SentryMonitor.track_scraping_result(scraping_result)
            
            # Complete task
            task.complete(success=result.success, result_data=scraping_result)
            
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
            
            logger.info(
                "Mitra10 scraping successful for query '%s': %s products found",
                query, len(result.products),
                extra={"operation": "scrape_products"}
            )
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(
                "Error in scrape_products: %s",
                str(e),
                exc_info=True,
                extra={"operation": "scrape_products"}
            )
            
            # Track error in Sentry
            Mitra10SentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_products: {str(e)}",
                category=BREADCRUMB_CATEGORY_ERROR,
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return JsonResponse({
                'success': False,
                'products': [],
                'error_message': f'Internal server error: {str(e)}',
                'url': ''
            }, status=500)

@require_http_methods(["GET"])
@enforce_resource_limits
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
        logger.error(
            "Error in scrape_locations: %s",
            str(e),
            exc_info=True,
            extra={"operation": "scrape_locations"}
        )
        return JsonResponse({
            'success': False,
            'locations': [],
            'count': 0,
            'error_message': f'Internal server error: {str(e)}'
        }, status=500)


def _create_error_response(error_message, status_code=400):
    """Helper to create standardized error response."""
    return JsonResponse({
        'success': False,
        'inserted': 0,
        'updated': 0,
        'anomalies': [],
        'error_message': error_message
    }, status=status_code)

def _perform_scraping(query, params):
    """Execute scraping based on sort type."""
    scraper = create_mitra10_scraper()
    
    if params['sort_type'] == 'popularity':
        return scraper.scrape_by_popularity(
            keyword=query,
            top_n=5,
            page=params['page']
        )
    else:
        return scraper.scrape_products(
            keyword=query,
            sort_by_price=params['sort_by_price'],
            page=params['page']
        )


def _scrape_location_data():
    """Scrape and return location data as a string."""
    try:
        location_scraper = create_mitra10_location_scraper()
        loc_result = location_scraper.scrape_locations()
        if loc_result.get('success') and loc_result.get('locations'):
            return ', '.join([str(l) for l in loc_result.get('locations', [])])
    except Exception as e:
        logger.warning(
            "Failed to scrape locations; continuing without locations: %s",
            e,
            extra={"operation": "_scrape_location_data"}
        )
    return ''


def _format_products_data(products, location_value):
    """Format product objects into dictionary data."""
    products_data = []
    for product in products:
        product_dict = {
            'name': product.name,
            'price': product.price,
            'url': product.url,
            'unit': product.unit,
            'location': location_value
        }
        if hasattr(product, 'sold_count') and product.sold_count is not None:
            product_dict['sold_count'] = product.sold_count
        products_data.append(product_dict)
    return products_data


def _auto_categorize_new_products(save_result):
    """Auto-categorize newly inserted products."""
    if not (save_result.get('success') and save_result.get('inserted', 0) > 0):
        return 0
    
    try:
        # Get recently inserted products (ones without category)
        uncategorized_products = Mitra10Product.objects.filter(category='').order_by('-id')[:save_result['inserted']]
        product_ids = list(uncategorized_products.values_list('id', flat=True))
        
        if product_ids:
            categorization_service = AutoCategorizationService()
            categorization_result = categorization_service.categorize_products('mitra10', product_ids)
            categorized_count = categorization_result.get('categorized', 0)
            
            logger.info(
                "Auto-categorized %s out of %s new Mitra10 products",
                categorized_count, len(product_ids),
                extra={"operation": "_auto_categorize_new_products"}
            )
            return categorized_count
    except Exception as cat_error:
        logger.warning(
            "Auto-categorization failed: %s",
            str(cat_error),
            extra={"operation": "_auto_categorize_new_products"}
        )
        # Don't fail the entire operation if categorization fails
    
    return 0


def _handle_scraping_phase(query, params, task):
    """Handle the scraping phase and return result or error response."""
    Mitra10SentryMonitor.add_breadcrumb(
        f"Starting scraping phase for: {query}",
        category=BREADCRUMB_CATEGORY_SCRAPER,
        level="info"
    )
    
    try:
        scraping_start_time = time.time()
        result = _perform_scraping(query, params)
        scraping_time = time.time() - scraping_start_time
        
        Mitra10SentryMonitor.add_breadcrumb(
            f"Scraping completed in {scraping_time:.2f}s - Found: {len(result.products) if result.success else 0}",
            category=BREADCRUMB_CATEGORY_SCRAPER,
            level="info" if result.success else "warning",
            data={"scraping_time": scraping_time, "products_count": len(result.products) if result.success else 0}
        )
        return result, None
    except Exception as e:
        logger.error(
            "Scraping error: %s",
            str(e),
            extra={"operation": "_handle_scraping_phase"}
        )
        Mitra10SentryMonitor.add_breadcrumb(
            f"Scraping failed: {str(e)}",
            category=BREADCRUMB_CATEGORY_ERROR,
            level="error"
        )
        task.complete(success=False)
        return None, _create_error_response(f'Scraping failed: {str(e)}', status_code=500)


def _handle_database_save(products_data, task):
    """Handle database save phase and return result or error response."""
    Mitra10SentryMonitor.add_breadcrumb(
        "Starting database save",
        category=BREADCRUMB_CATEGORY_DATABASE,
        level="info"
    )
    
    try:
        db_start_time = time.time()
        service = Mitra10DatabaseService()
        save_result = service.save_with_price_update(products_data)
        db_time = time.time() - db_start_time
        
        Mitra10SentryMonitor.add_breadcrumb(
            f"Database save completed in {db_time:.2f}s - Inserted: {save_result.get('inserted', 0)}, Updated: {save_result.get('updated', 0)}",
            category=BREADCRUMB_CATEGORY_DATABASE,
            level="info",
            data={
                "db_time": db_time,
                "inserted": save_result.get('inserted', 0),
                "updated": save_result.get('updated', 0),
                "anomalies": len(save_result.get('anomalies', []))
            }
        )
        return save_result, None
    except Exception as e:
        logger.error(
            "Database error: %s",
            str(e),
            extra={"operation": "_handle_database_save"}
        )
        Mitra10SentryMonitor.add_breadcrumb(
            f"Database save failed: {str(e)}",
            category=BREADCRUMB_CATEGORY_ERROR,
            level="error"
        )
        task.complete(success=False)
        return None, _create_error_response(f'Database error: {str(e)}', status_code=500)


@require_http_methods(["POST"])
@require_api_token('write')
@validate_input({
    'q': lambda v: InputValidator.validate_keyword(v or '', max_length=100),
    'page': lambda v: (False, 'page must be a valid integer', None) if v == '' else InputValidator.validate_integer(v or '0', 'page', min_value=0, max_value=1000),
    'sort_type': lambda v: (True, '', (v or 'cheapest').lower()) if (v or 'cheapest').lower() in ['cheapest', 'popularity'] else (False, 'sort_type must be cheapest or popularity', None)
})
@enforce_resource_limits
def scrape_and_save_products(request):
    # Start Sentry transaction for monitoring
    with track_mitra10_transaction("mitra10_scrape_and_save_products"):
        try:
            query = request.validated_data.get('q')
            page = request.validated_data.get('page', 0)
            sort_type = request.validated_data.get('sort_type', 'cheapest')
            
            # Set scraping context for Sentry
            Mitra10SentryMonitor.set_scraping_context(
                keyword=query,
                page=page,
                additional_data={
                    'sort_type': sort_type,
                    'source': 'scrape_and_save',
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Create task monitor
            task_id = f"scrape_save_{uuid.uuid4().hex[:8]}"
            task = Mitra10TaskMonitor(task_id=task_id, task_type="scrape_and_save")
            
            params = {
                'sort_type': sort_type,
                'sort_by_price': None,
                'page': page
            }
            
            # Handle scraping phase
            result, error_response = _handle_scraping_phase(query, params, task)
            if error_response:
                return error_response
        
            if not result.success:
                task.complete(success=False)
                return _create_error_response(result.error_message)
            
            # Update task progress
            task.record_progress(1, 3, "Scraping completed, fetching locations...")
            
            # Track location scraping
            Mitra10SentryMonitor.add_breadcrumb(
                "Starting location scraping",
                category=BREADCRUMB_CATEGORY_LOCATION,
                level="info"
            )
            
            location_start_time = time.time()
            run_location_value = _scrape_location_data()
            location_time = time.time() - location_start_time
            
            Mitra10SentryMonitor.add_breadcrumb(
                f"Location scraping completed in {location_time:.2f}s",
                category=BREADCRUMB_CATEGORY_LOCATION,
                level="info",
                data={"location_time": location_time}
            )
            
            products_data = _format_products_data(result.products, run_location_value)
            
            # Update task progress
            task.record_progress(2, 3, "Saving to database...")
            
            # Handle database save
            save_result, error_response = _handle_database_save(products_data, task)
            if error_response:
                return error_response
            
            # Update task progress
            task.record_progress(3, 3, "Finalizing...")
            
            _auto_categorize_new_products(save_result)
            
            # Track complete operation result
            operation_result = {
                'products_count': len(products_data),
                'success': save_result.get('success', False),
                'errors_count': 0 if save_result.get('success', False) else 1,
                'inserted': save_result.get('inserted', 0),
                'updated': save_result.get('updated', 0),
                'anomalies_count': len(save_result.get('anomalies', []))
            }
            Mitra10SentryMonitor.track_scraping_result(operation_result)
            
            # Complete task
            task.complete(success=save_result.get('success', False), result_data=operation_result)
            
            logger.info(
                "Mitra10 saved %s new, updated %s, detected %s anomalies for query '%s'",
                save_result.get('inserted', 0), save_result.get('updated', 0),
                len(save_result.get('anomalies', [])), query,
                extra={"operation": "scrape_and_save_products"}
            )
            
            return JsonResponse({
                'success': save_result.get('success', False),
                'inserted': save_result.get('inserted', 0),
                'updated': save_result.get('updated', 0),
                'anomalies': save_result.get('anomalies', []),
                'total_products': len(products_data),
                'error_message': save_result.get('error_message', '')
            })
            
        except Exception as e:
            logger.error(
                "Error in scrape_and_save_products: %s",
                str(e),
                exc_info=True,
                extra={"operation": "scrape_and_save_products"}
            )
            
            # Track error in Sentry
            Mitra10SentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_and_save_products: {str(e)}",
                category=BREADCRUMB_CATEGORY_ERROR,
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return _create_error_response(f'Internal server error: {str(e)}', status_code=500)
    
@require_http_methods(["GET"])
@validate_input({
    'q': lambda v: InputValidator.validate_keyword(v or '', max_length=100),
    'page': lambda v: (False, 'page must be a valid integer', None) if v == '' else InputValidator.validate_integer(v or '0', 'page', min_value=0, max_value=1000)
})
@enforce_resource_limits
def scrape_popularity(request):
    """Scrape products sorted by popularity and return top 5 best sellers."""
    try:
        query = request.validated_data.get('q')
        page = request.validated_data.get('page', 0)
        
        # Create scraper and scrape top 5 products by popularity
        scraper = create_mitra10_scraper()
        result = scraper.scrape_by_popularity(
            keyword=query,
            top_n=5,
            page=page
        )
        
        # Format products data including sold_count
        products_data = [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url,
                'unit': product.unit,
                'sold_count': product.sold_count
            }
            for product in result.products
        ]
        
        response_data = {
            'success': result.success,
            'products': products_data,
            'total_products': len(products_data),
            'error_message': result.error_message,
            'url': result.url
        }
        
        logger.info(
            "Mitra10 popularity scraping successful for query '%s': %s best sellers found",
            query, len(result.products),
            extra={"operation": "scrape_popularity"}
        )
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(
            "Error in scrape_popularity: %s",
            str(e),
            exc_info=True,
            extra={"operation": "scrape_popularity"}
        )
        return JsonResponse({
            'success': False,
            'products': [],
            'error_message': f'Internal server error: {str(e)}',
            'url': ''
        }, status=500)