from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_depo_scraper, create_depo_location_scraper
from .database_service import DepoBangunanDatabaseService
from db_pricing.auto_categorization_service import AutoCategorizationService
from .security import (
    SecurityDesignPatterns,
    require_api_token,
    validate_input,
    enforce_resource_limits,
    InputValidator,
    AccessControlManager,
    RateLimiter
)
from .sentry_monitoring import (
    DepoBangunanSentryMonitor,
    track_depobangunan_transaction,
    DepoBangunanTaskMonitor
)
import logging
import uuid
import time

logger = logging.getLogger(__name__)

# Error message constants
ERROR_KEYWORD_REQUIRED = 'Keyword parameter is required'
ERROR_PAGE_INVALID = 'Page parameter must be a valid integer'
ERROR_INTERNAL_SERVER = 'Internal server error occurred'
ERROR_SAVE_DB_FAILED = 'Failed to save products to database'

# Sentry breadcrumb constants
BREADCRUMB_STARTING_LOCATION_SCRAPING = 'Starting location scraping'
CATEGORY_DEPOBANGUNAN_LOCATION = 'depobangunan.location'
CATEGORY_DEPOBANGUNAN_SCRAPER = 'depobangunan.scraper'
CATEGORY_DEPOBANGUNAN_ERROR = 'depobangunan.error'

# ---------- Helper functions ----------

def _save_products_to_database(products):
    """
    Helper function to save products to database and auto-categorize them.
    
    Args:
        products: List of product objects from scraping result
        
    Returns:
        dict: Database operation result with categorization info
    """
    if not products:
        return {'success': False, 'updated': 0, 'inserted': 0, 'anomalies': [], 'categorized': 0}
    
    try:
        # Convert products to dict format if needed
        products_data = _convert_products_to_dict(products)
        
        # Validate business logic for each product
        for product_data in products_data:
            is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(product_data)
            if not is_valid:
                logger.warning(f"Product validation failed: {error_msg}")
                return {'success': False, 'updated': 0, 'inserted': 0, 'anomalies': [], 'categorized': 0, 'error': error_msg}
        
        # Save to database with price update
        db_service = DepoBangunanDatabaseService()
        result = db_service.save_with_price_update(products_data)
        
        # Auto-categorize newly inserted products
        categorized_count = 0
        if result.get('success') and result.get('new_count', 0) > 0:
            try:
                from db_pricing.models import DepoBangunanProduct
                
                # Get recently inserted products (ones without category)
                uncategorized_products = DepoBangunanProduct.objects.filter(category='').order_by('-id')[:result['new_count']]
                product_ids = list(uncategorized_products.values_list('id', flat=True))
                
                if product_ids:
                    categorization_service = AutoCategorizationService()
                    categorization_result = categorization_service.categorize_products('depobangunan', product_ids)
                    categorized_count = categorization_result.get('categorized', 0)
                    logger.info(f"Auto-categorized {categorized_count} out of {len(product_ids)} new DepoBangunan products")
            except Exception as cat_error:
                logger.warning(f"Auto-categorization failed: {str(cat_error)}")
                # Don't fail the entire operation if categorization fails
        
        result['categorized'] = categorized_count
        return result
        
    except Exception as db_error:
        logger.error(f"Failed to save DepoBangunan products to database: {str(db_error)}")
        return {'success': False, 'updated': 0, 'inserted': 0, 'anomalies': [], 'categorized': 0}


def _parse_sorting_params(request):
    sort_type = request.POST.get('sort_type', '').lower()
    if sort_type and sort_type not in ['cheapest', 'popularity']:
        return None, None, _create_error_response('Invalid sort_type. Must be "cheapest" or "popularity"')
    sort_by_price = _parse_sort_by_price(request.POST.get('sort_by_price', 'true'))
    if not sort_type:
        sort_type = 'cheapest' if sort_by_price else 'popularity'
    return sort_type, sort_by_price, None


def _parse_boolean(value):
    return value.lower() in ['true', '1', 'yes']


def _scrape_products_by_type(scraper, keyword, sort_type, sort_by_price, page):
    if sort_type == 'popularity':
        result = scraper.scrape_popularity_products(keyword=keyword, top_n=5, page=page)
        if result.success and result.products:
            result.products = _sort_popularity_products(result.products)
        return result
    return scraper.scrape_products(keyword=keyword, sort_by_price=sort_by_price, page=page)


def _sort_popularity_products(products):
    with_sold = [p for p in products if getattr(p, 'sold_count', None) is not None]
    without_sold = [p for p in products if getattr(p, 'sold_count', None) is None]
    with_sold.sort(key=lambda p: p.sold_count, reverse=True)
    return with_sold[:5] + without_sold[:max(0, 5 - len(with_sold))]


def _empty_product_response():
    return JsonResponse({
        'success': True,
        'message': 'No products found to save',
        'saved': 0,
        'inserted': 0,
        'updated': 0,
        'anomalies': []
    })


def _convert_products(products, location_value):
    return [
        {
            'name': p.name,
            'price': p.price,
            'url': p.url,
            'unit': p.unit,
            'location': location_value
        }
        for p in products
    ]


def _auto_categorize_products(product_count):
    """Auto-categorize newly inserted products.
    
    Args:
        product_count: Number of products to categorize
        
    Returns:
        int: Number of products successfully categorized
    """
    try:
        from db_pricing.models import DepoBangunanProduct
        
        # Get recently inserted products (ones without category)
        uncategorized_products = DepoBangunanProduct.objects.filter(category='').order_by('-id')[:product_count]
        product_ids = list(uncategorized_products.values_list('id', flat=True))
        
        if product_ids:
            categorization_service = AutoCategorizationService()
            categorization_result = categorization_service.categorize_products('depobangunan', product_ids)
            categorized_count = categorization_result.get('categorized', 0)
            logger.info(f"Auto-categorized {categorized_count} out of {len(product_ids)} new DepoBangunan products")
            return categorized_count
    except Exception as cat_error:
        logger.warning(f"Auto-categorization failed: {str(cat_error)}")
    
    return 0


def _save_products(db_service, products_data, use_price_update, result_url):
    # Validate business logic for each product
    for product_data in products_data:
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(product_data)
        if not is_valid:
            logger.warning(f"Product validation failed: {error_msg}")
            return None, _create_error_response(f"Validation error: {error_msg}", 400)
    
    if use_price_update:
        save_result = db_service.save_with_price_update(products_data)
        if not save_result.get('success'):
            return None, _create_error_response(ERROR_SAVE_DB_FAILED, 500)
        
        # Auto-categorize newly inserted products
        categorized_count = _auto_categorize_products(save_result.get('new_count', 0))
        
        return ({
            'success': True,
            'message': 'Products scraped and saved with price update',
            'saved': save_result.get('updated_count', 0) + save_result.get('new_count', 0),
            'inserted': save_result.get('new_count', 0),
            'updated': save_result.get('updated_count', 0),
            'categorized': categorized_count,
            'anomalies': save_result.get('anomalies', []),
            'url': result_url
        }, None)

    save_result = db_service.save(products_data)
    if not save_result:
        return None, _create_error_response(ERROR_SAVE_DB_FAILED, 500)
    
    # Auto-categorize newly saved products
    categorized_count = _auto_categorize_products(len(products_data))
    
    return ({
        'success': True,
        'message': f'Successfully saved {len(products_data)} products',
        'saved': len(products_data),
        'inserted': len(products_data),
        'updated': 0,
        'categorized': categorized_count,
        'anomalies': [],
        'url': result_url
    }, None)


def _create_error_response(message, status=400):
    return JsonResponse({'error': message}, status=status)


def _validate_and_parse_keyword(keyword):
    """Validate and parse keyword parameter with security checks"""
    if not keyword or not keyword.strip():
        return None, _create_error_response(ERROR_KEYWORD_REQUIRED)
    
    # Validate keyword for SQL injection and XSS
    validator = InputValidator()
    is_valid, error_msg, sanitized_keyword = validator.validate_keyword(keyword.strip())
    if not is_valid:
        return None, _create_error_response(error_msg)
    
    return sanitized_keyword, None


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


def _parse_top_n(top_n_param):
    """Parse and validate top_n parameter"""
    try:
        top_n = int(top_n_param) if top_n_param else 5
        if top_n <= 0:
            return None, _create_error_response('top_n must be a positive integer')
        return top_n, None
    except ValueError:
        return None, _create_error_response('top_n must be a valid integer')


def _scrape_location_names():
    """Scrape location names and return as comma-separated string.
    
    Returns empty string on failure to avoid breaking the main scraping flow.
    Handles MagicMock objects during testing by checking attributes and converting to string.
    """
    try:
        location_scraper = create_depo_location_scraper()
        loc_result = location_scraper.scrape_locations(timeout=30)
        
        if loc_result.success and loc_result.locations:
            # Handle both real Location objects and MagicMock test objects
            location_names = []
            for location in loc_result.locations:
                if hasattr(location, 'name'):
                    # Convert to string to handle MagicMock objects
                    location_names.append(str(location.name))
            
            if location_names:
                return ', '.join(location_names)
        
        return ''
    except Exception as e:
        logger.warning(f"Failed to scrape locations; continuing without locations: {e}")
        return ''


def _convert_products_to_dict(products):
    """Convert product objects to dictionary format"""
    return [
        {
            'name': product.name,
            'price': product.price,
            'url': product.url,
            'unit': product.unit,
            'location': product.location if hasattr(product, 'location') else ''
        }
        for product in products
    ]


def _convert_products_to_dict_with_sold_count(products):
    """Convert product objects to dictionary format including sold_count"""
    return [
        {
            'name': product.name,
            'price': product.price,
            'url': product.url,
            'unit': product.unit,
            'location': product.location if hasattr(product, 'location') else '',
            'sold_count': product.sold_count if hasattr(product, 'sold_count') and product.sold_count is not None else 0
        }
        for product in products
    ]


def _convert_products_to_dict_with_sold_count(products):
    """Convert product objects to dictionary format including sold_count"""
    return [
        {
            'name': product.name,
            'price': product.price,
            'url': product.url,
            'unit': product.unit,
            'location': product.location if hasattr(product, 'location') else '',
            'sold_count': product.sold_count if hasattr(product, 'sold_count') and product.sold_count is not None else 0
        }
        for product in products
    ]


def _parse_sort_parameters(request):
    """Parse and validate sort-related parameters from request.
    
    Returns:
        tuple: (sort_type, sort_by_price, final_sort_type, error_response)
    """
    sort_type = request.GET.get('sort_type', '').lower()
    sort_by_price_param = request.GET.get('sort_by_price', 'true')
    
    # Validate sort_type if provided
    if sort_type and sort_type not in ['cheapest', 'popularity']:
        return None, None, None, _create_error_response('Invalid sort_type. Must be either "cheapest" or "popularity"')
    
    # Determine sort_by_price based on sort_type or sort_by_price parameter
    if sort_type:
        sort_by_price = (sort_type == 'cheapest')
        final_sort_type = sort_type
    else:
        sort_by_price = _parse_sort_by_price(sort_by_price_param)
        final_sort_type = 'cheapest' if sort_by_price else 'popularity'
    
    return sort_type, sort_by_price, final_sort_type, None


def _scrape_and_track_locations():
    """Scrape locations with monitoring and error handling.
    
    Returns:
        tuple: (location_value, location_time)
    """
    DepoBangunanSentryMonitor.add_breadcrumb(
        BREADCRUMB_STARTING_LOCATION_SCRAPING,
        category=CATEGORY_DEPOBANGUNAN_LOCATION,
        level="info"
    )
    
    location_start_time = time.time()
    try:
        location_scraper = create_depo_location_scraper()
        loc_result = location_scraper.scrape_locations(timeout=30)
        if loc_result.success and loc_result.locations:
            run_location_value = ', '.join([location.name for location in loc_result.locations])
        else:
            run_location_value = ''
    except Exception as e:
        logger.warning(f"Failed to scrape locations; continuing without locations: {e}")
        run_location_value = ''
    
    location_time = time.time() - location_start_time
    
    # Log location result to Sentry
    DepoBangunanSentryMonitor.add_breadcrumb(
        f"Location scraping completed in {location_time:.2f}s - Found: {len(run_location_value.split(', ')) if run_location_value else 0}",
        category=CATEGORY_DEPOBANGUNAN_LOCATION,
        level="info",
        data={
            "success": bool(run_location_value),
            "locations_count": len(run_location_value.split(', ')) if run_location_value else 0,
            "duration": location_time
        }
    )
    
    return run_location_value, location_time


@require_http_methods(["GET"])
@enforce_resource_limits
def scrape_products(request):
    # Start Sentry transaction for monitoring
    with track_depobangunan_transaction("depobangunan_scrape_products"):
        try:
            # Validate and parse parameters
            keyword, error = _validate_and_parse_keyword(request.GET.get('keyword'))
            if error:
                return error
            
            # Parse sort parameters
            sort_type, sort_by_price, final_sort_type, error = _parse_sort_parameters(request)
            if error:
                return error
            
            page, error = _parse_page(request.GET.get('page', '0'))
            if error:
                return error
            
            # Set scraping context for Sentry
            DepoBangunanSentryMonitor.set_scraping_context(
                keyword=keyword,
                page=page,
                additional_data={
                    'sort_by_price': sort_by_price,
                    'sort_type': final_sort_type,
                    'source': 'api_endpoint',
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Create task monitor for tracking
            task_id = f"scrape_{uuid.uuid4().hex[:8]}"
            task = DepoBangunanTaskMonitor(task_id=task_id, task_type="product_scraping")
            
            # Scrape locations with monitoring
            run_location_value, location_time = _scrape_and_track_locations()
            
            # Update task progress
            task.record_progress(1, 2, "Locations scraped, starting product scraping...")
            
            # Track product scraping
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Starting product scraping for keyword: {keyword}",
                category=CATEGORY_DEPOBANGUNAN_SCRAPER,
                level="info"
            )
            
            product_start_time = time.time()
            scraper = create_depo_scraper()
            result = scraper.scrape_products(
                keyword=keyword,
                sort_by_price=sort_by_price,
                page=page
            )
            product_time = time.time() - product_start_time
            
            # Update task progress
            task.record_progress(2, 2, "Product scraping completed")
            
            # Track scraping result
            scraping_result = {
                'products_count': len(result.products),
                'success': result.success,
                'errors_count': 0 if result.success else 1,
                'location_time': location_time,
                'product_time': product_time,
                'total_time': location_time + product_time
            }
            DepoBangunanSentryMonitor.track_scraping_result(scraping_result)
            
            # Convert products to dict and add location
            products_data = [
                {
                    'name': product.name,
                    'price': product.price,
                    'url': product.url,
                    'unit': product.unit,
                    'location': run_location_value
                }
                for product in result.products
            ]
            
            response_data = {
                'success': result.success,
                'products': products_data,
                'error_message': result.error_message,
                'url': result.url,
                'sort_type': final_sort_type
            }
            
            # Complete task
            task.complete(success=result.success, result_data=scraping_result)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Unexpected error in Depo Bangunan scraper: {str(e)}")
            
            # Track error in Sentry
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_products: {str(e)}",
                category=CATEGORY_DEPOBANGUNAN_ERROR,
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return _create_error_response(ERROR_INTERNAL_SERVER, 500)


@require_http_methods(["GET"])
@enforce_resource_limits
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
@require_api_token(required_permission='write')
@enforce_resource_limits
def scrape_and_save_products(request):
    # Start Sentry transaction for monitoring
    with track_depobangunan_transaction("depobangunan_scrape_and_save"):
        try:
            keyword, error = _validate_and_parse_keyword(request.POST.get('keyword'))
            if error:
                return error

            sort_type, sort_by_price, error = _parse_sorting_params(request)
            if error:
                return error

            page, error = _parse_page(request.POST.get('page', '0'))
            if error:
                return error

            use_price_update = _parse_boolean(request.POST.get('use_price_update', 'false'))
            
            # Set scraping context for Sentry
            DepoBangunanSentryMonitor.set_scraping_context(
                keyword=keyword,
                page=page,
                additional_data={
                    'sort_by_price': sort_by_price,
                    'sort_type': sort_type,
                    'use_price_update': use_price_update,
                    'source': 'scrape_and_save',
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Create task monitor for tracking
            task_id = f"save_{uuid.uuid4().hex[:8]}"
            task = DepoBangunanTaskMonitor(task_id=task_id, task_type="scrape_and_save")
            
            scraper = create_depo_scraper()

            # Track product scraping
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Starting product scraping for keyword: {keyword}",
                category=CATEGORY_DEPOBANGUNAN_SCRAPER,
                level="info"
            )
            
            scrape_start_time = time.time()
            result = _scrape_products_by_type(scraper, keyword, sort_type, sort_by_price, page)
            scrape_time = time.time() - scrape_start_time
            
            if not result.success:
                DepoBangunanSentryMonitor.add_breadcrumb(
                    f"Scraping failed: {result.error_message}",
                    category=CATEGORY_DEPOBANGUNAN_ERROR,
                    level="error"
                )
                task.complete(success=False)
                return _create_error_response(result.error_message, 500)
            
            if not result.products:
                task.complete(success=True, result_data={'products_count': 0})
                return _empty_product_response()

            # Update progress
            task.record_progress(1, 3, "Products scraped, fetching locations...")
            
            # Track location scraping
            DepoBangunanSentryMonitor.add_breadcrumb(
                BREADCRUMB_STARTING_LOCATION_SCRAPING,
                category=CATEGORY_DEPOBANGUNAN_LOCATION,
                level="info"
            )
            
            location_start_time = time.time()
            run_location_value = _scrape_location_names()
            location_time = time.time() - location_start_time
            
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Location scraping completed in {location_time:.2f}s",
                category=CATEGORY_DEPOBANGUNAN_LOCATION,
                level="info",
                data={"locations_found": bool(run_location_value)}
            )
            
            products_data = _convert_products(result.products, run_location_value)

            # Update progress
            task.record_progress(2, 3, "Saving to database...")
            
            # Track database save
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Saving {len(products_data)} products to database",
                category="depobangunan.database",
                level="info",
                data={"use_price_update": use_price_update}
            )
            
            db_start_time = time.time()
            db_service = DepoBangunanDatabaseService()
            response_data, error = _save_products(db_service, products_data, use_price_update, result.url)
            db_time = time.time() - db_start_time
            
            if error:
                DepoBangunanSentryMonitor.add_breadcrumb(
                    "Database save failed",
                    category=CATEGORY_DEPOBANGUNAN_ERROR,
                    level="error"
                )
                task.complete(success=False)
                return error
            
            # Update progress
            task.record_progress(3, 3, "Save completed")
            
            # Track overall result
            scraping_result = {
                'products_count': len(products_data),
                'success': True,
                'errors_count': 0,
                'scrape_time': scrape_time,
                'location_time': location_time,
                'db_time': db_time,
                'total_time': scrape_time + location_time + db_time,
                'saved': response_data.get('saved', 0),
                'updated': response_data.get('updated', 0),
                'inserted': response_data.get('inserted', 0)
            }
            DepoBangunanSentryMonitor.track_scraping_result(scraping_result)
            
            task.complete(success=True, result_data=scraping_result)
            
            return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"Unexpected error in scrape and save: {str(e)}")
            
            # Track error in Sentry
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_and_save_products: {str(e)}",
                category=CATEGORY_DEPOBANGUNAN_ERROR,
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return _create_error_response(ERROR_INTERNAL_SERVER, 500)

@require_http_methods(["GET"])
@enforce_resource_limits
def scrape_popularity(request):
    """Scrape products sorted by popularity and return top N best sellers."""
    # Start Sentry transaction for monitoring
    with track_depobangunan_transaction("depobangunan_scrape_popularity"):
        try:
            # Validate and parse parameters
            keyword, error = _validate_and_parse_keyword(request.GET.get('keyword'))
            if error:
                return error
            
            page, error = _parse_page(request.GET.get('page', '0'))
            if error:
                return error
            
            top_n, error = _parse_top_n(request.GET.get('top_n'))
            if error:
                return error
            
            # Set scraping context for Sentry
            DepoBangunanSentryMonitor.set_scraping_context(
                keyword=keyword,
                page=page,
                additional_data={
                    'top_n': top_n,
                    'sort_type': 'popularity',
                    'source': 'scrape_popularity',
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Create task monitor for tracking
            task_id = f"popularity_{uuid.uuid4().hex[:8]}"
            task = DepoBangunanTaskMonitor(task_id=task_id, task_type="popularity_scraping")
            
            # Track product scraping
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Starting popularity scraping for keyword: {keyword}, top_n: {top_n}",
                category=CATEGORY_DEPOBANGUNAN_SCRAPER,
                level="info"
            )
            
            scrape_start_time = time.time()
            # Create scraper and scrape top N products by popularity
            scraper = create_depo_scraper()
            result = scraper.scrape_popularity_products(
                keyword=keyword,
                top_n=top_n,
                page=page
            )
            scrape_time = time.time() - scrape_start_time
            
            # Update progress
            task.record_progress(1, 2, "Products scraped, fetching locations...")
            
            # Track location scraping
            DepoBangunanSentryMonitor.add_breadcrumb(
                BREADCRUMB_STARTING_LOCATION_SCRAPING,
                category=CATEGORY_DEPOBANGUNAN_LOCATION,
                level="info"
            )
            
            location_start_time = time.time()
            # Scrape locations and get location names
            run_location_value = _scrape_location_names()
            location_time = time.time() - location_start_time
            
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Location scraping completed in {location_time:.2f}s",
                category=CATEGORY_DEPOBANGUNAN_LOCATION,
                level="info",
                data={"locations_found": bool(run_location_value)}
            )
            
            # Update progress
            task.record_progress(2, 2, "Formatting response...")
            
            # Format products data including sold_count and location
            products_data = [
                {
                    'name': product.name,
                    'price': product.price,
                    'url': product.url,
                    'unit': product.unit,
                    'location': run_location_value,
                    'sold_count': product.sold_count if hasattr(product, 'sold_count') and product.sold_count is not None else 0
                }
                for product in result.products
            ]
            
            # Track scraping result
            scraping_result = {
                'products_count': len(products_data),
                'success': result.success,
                'errors_count': 0 if result.success else 1,
                'scrape_time': scrape_time,
                'location_time': location_time,
                'total_time': scrape_time + location_time
            }
            DepoBangunanSentryMonitor.track_scraping_result(scraping_result)
            
            response_data = {
                'success': result.success,
                'products': products_data,
                'total_products': len(products_data),
                'error_message': result.error_message,
                'url': result.url
            }
            
            logger.info(f"DepoBangunan popularity scraping successful for keyword '{keyword}': {len(result.products)} best sellers found")
            
            task.complete(success=result.success, result_data=scraping_result)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error in scrape_popularity: {str(e)}", exc_info=True)
            
            # Track error in Sentry
            DepoBangunanSentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_popularity: {str(e)}",
                category=CATEGORY_DEPOBANGUNAN_ERROR,
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return _create_error_response(ERROR_INTERNAL_SERVER, 500)


@require_http_methods(["POST"])
@require_api_token(required_permission='write')
@enforce_resource_limits
def scrape_and_save_popularity(request):
    """Scrape products by popularity and save to database with location data."""
    try:
        # Validate and parse parameters
        keyword, error = _validate_and_parse_keyword(request.POST.get('keyword'))
        if error:
            return error
        
        page, error = _parse_page(request.POST.get('page', '0'))
        if error:
            return error
        
        top_n, error = _parse_top_n(request.POST.get('top_n'))
        if error:
            return error
        
        # Create scraper and scrape by popularity
        scraper = create_depo_scraper()
        result = scraper.scrape_popularity_products(
            keyword=keyword,
            top_n=top_n,
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
        
        # Scrape locations and get location names
        run_location_value = _scrape_location_names()
        
        # Convert products to dict and inject location
        products_data = [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url,
                'unit': product.unit,
                'location': run_location_value
            }
            for product in result.products
        ]
        
        db_service = DepoBangunanDatabaseService()
        save_result = db_service.save(products_data)
        
        if not save_result:
            return _create_error_response(ERROR_SAVE_DB_FAILED, 500)
        
        response_data = {
            'success': True,
            'message': 'Popularity products scraped and saved successfully',
            'scraped_count': len(products_data),
            'saved_count': len(products_data),
            'url': result.url
        }
        
        logger.info(f"DepoBangunan saved {len(products_data)} popularity products for keyword '{keyword}'")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in scrape_and_save_popularity: {str(e)}")
        return _create_error_response(ERROR_INTERNAL_SERVER, 500)
