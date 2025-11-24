from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_juraganmaterial_scraper
from .database_service import JuraganMaterialDatabaseService
from api.views_utils import validate_scraping_request, format_scraping_response, handle_scraping_exception
from db_pricing.auto_categorization_service import AutoCategorizationService
from .sentry_monitoring import (
    JuraganMaterialSentryMonitor,
    track_juragan_material_transaction,
    JuraganMaterialTaskMonitor
)
import logging
import uuid
import time

logger = logging.getLogger(__name__)

# Sentry breadcrumb categories
CATEGORY_DATABASE = "juragan_material.database"
CATEGORY_CATEGORIZATION = "juragan_material.categorization"
CATEGORY_SCRAPER = "juragan_material.scraper"
CATEGORY_ERROR = "juragan_material.error"


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
    
    # Add breadcrumb for database save operation
    JuraganMaterialSentryMonitor.add_breadcrumb(
        f"Starting database save for {len(products)} products",
        category=CATEGORY_DATABASE,
        level="info",
        data={"products_count": len(products)}
    )
    
    try:
        # Convert products to dict format if needed
        products_data = _convert_products_to_dict(products)
        
        # Save to database with price update
        save_start_time = time.time()
        db_service = JuraganMaterialDatabaseService()
        result = db_service.save_with_price_update(products_data)
        save_time = time.time() - save_start_time
        
        # Track database operation
        JuraganMaterialSentryMonitor.add_breadcrumb(
            f"Database save completed in {save_time:.2f}s",
            category=CATEGORY_DATABASE,
            level="info" if result.get('success') else "error",
            data={
                "duration": save_time,
                "inserted": result.get('inserted', 0),
                "updated": result.get('updated', 0)
            }
        )
        
        # Auto-categorize newly inserted products
        categorized_count = 0
        if result.get('success') and result.get('inserted', 0) > 0:
            try:
                from db_pricing.models import JuraganMaterialProduct
                
                # Get recently inserted products (ones without category)
                uncategorized_products = JuraganMaterialProduct.objects.filter(category='').order_by('-id')[:result['inserted']]
                product_ids = list(uncategorized_products.values_list('id', flat=True))
                
                if product_ids:
                    JuraganMaterialSentryMonitor.add_breadcrumb(
                        f"Starting auto-categorization for {len(product_ids)} products",
                        category=CATEGORY_CATEGORIZATION,
                        level="info"
                    )
                    
                    categorization_start = time.time()
                    categorization_service = AutoCategorizationService()
                    categorization_result = categorization_service.categorize_products('juragan_material', product_ids)
                    categorized_count = categorization_result.get('categorized', 0)
                    categorization_time = time.time() - categorization_start
                    
                    logger.info(f"Auto-categorized {categorized_count} out of {len(product_ids)} new Juragan Material products")
                    
                    JuraganMaterialSentryMonitor.add_breadcrumb(
                        f"Auto-categorization completed in {categorization_time:.2f}s",
                        category=CATEGORY_CATEGORIZATION,
                        level="info",
                        data={
                            "duration": categorization_time,
                            "categorized": categorized_count,
                            "total": len(product_ids)
                        }
                    )
            except Exception as cat_error:
                logger.warning(f"Auto-categorization failed: {str(cat_error)}")
                JuraganMaterialSentryMonitor.add_breadcrumb(
                    f"Auto-categorization failed: {str(cat_error)}",
                    category=CATEGORY_CATEGORIZATION,
                    level="warning"
                )
                # Don't fail the entire operation if categorization fails
        
        result['categorized'] = categorized_count
        
        # Track overall database operation result
        JuraganMaterialSentryMonitor.track_database_operation("save_products", result)
        
        return result
        
    except Exception as db_error:
        logger.error(f"Failed to save Juragan Material products to database: {str(db_error)}")
        JuraganMaterialSentryMonitor.add_breadcrumb(
            f"Database save failed: {str(db_error)}",
            category=CATEGORY_DATABASE,
            level="error"
        )
        return {'success': False, 'updated': 0, 'inserted': 0, 'anomalies': [], 'categorized': 0}


def _validate_sort_type(sort_type_param):
    """Validate and normalize sort_type parameter."""
    sort_type = (sort_type_param or 'cheapest').lower()
    if sort_type not in ('cheapest', 'popularity'):
        return None, JsonResponse(
            {'error': 'sort_type must be either "cheapest" or "popularity"'}, 
            status=400
        )
    return sort_type, None


def _pick_products(sort_type, products):
    """Return products per sort_type rule.
    
    Args:
        sort_type: 'cheapest' or 'popularity'
        products: List of products
        
    Returns:
        List of products (all for cheapest, top 5 for popularity)
    """
    if sort_type != 'popularity':
        return products
    # For popularity, return top 5 most relevant products
    return products[:5]


def _convert_products_to_dict(products):
    """Convert product objects to dictionary format"""
    return [
        {
            'name': product.name,
            'price': product.price,
            'url': product.url,
            'unit': product.unit,
            'location': product.location
        }
        for product in products
    ]


def _get_products_count(result):
    """Get product count from scraping result."""
    return len(result.products) if result.products else 0


def _add_database_info_to_response(response_data, db_save_result, save_to_db):
    """Add database save information to response data."""
    if db_save_result and isinstance(db_save_result, dict):
        response_data['database'] = {
            'saved': db_save_result.get('success', False),
            'inserted': db_save_result.get('inserted', 0),
            'updated': db_save_result.get('updated', 0),
            'categorized': db_save_result.get('categorized', 0),
            'anomalies': db_save_result.get('anomalies', [])
        }
    else:
        response_data['saved_to_database'] = db_save_result
    response_data['database_save_attempted'] = save_to_db


def _update_scraping_result_with_db_data(scraping_result, save_to_db, db_save_result):
    """Update scraping result with database operation data."""
    if save_to_db and db_save_result:
        scraping_result.update({
            'db_inserted': db_save_result.get('inserted', 0),
            'db_updated': db_save_result.get('updated', 0),
            'db_categorized': db_save_result.get('categorized', 0)
        })


@require_http_methods(["GET"])
def scrape_products(request):
    # Start Sentry transaction for monitoring
    with track_juragan_material_transaction("juragan_material_scrape_products"):
        try:
            # Validate request parameters
            keyword, sort_by_price, page, error_response = validate_scraping_request(request)
            if error_response:
                return error_response
            
            # Set scraping context for Sentry
            JuraganMaterialSentryMonitor.set_scraping_context(
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
            task = JuraganMaterialTaskMonitor(task_id=task_id, task_type="product_scraping")
            
            # Check if we should save to database
            save_to_db_param = request.GET.get('save_to_db', 'false').lower()
            save_to_db = save_to_db_param in ['true', '1', 'yes']
            
            # Track product scraping start
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Starting product scraping for keyword: {keyword}",
                category=CATEGORY_SCRAPER,
                level="info",
                data={
                    "keyword": keyword,
                    "page": page,
                    "sort_by_price": sort_by_price,
                    "save_to_db": save_to_db
                }
            )
            
            # Perform scraping
            scrape_start_time = time.time()
            scraper = create_juraganmaterial_scraper()
            result = scraper.scrape_products(
                keyword=keyword,
                sort_by_price=sort_by_price,
                page=page
            )
            scrape_time = time.time() - scrape_start_time
            products_count = _get_products_count(result)
            
            # Update task progress
            total_steps = 2 if save_to_db else 1
            task.record_progress(1, total_steps, f"Product scraping completed in {scrape_time:.2f}s")
            
            # Track scraping result
            scraping_result = {
                'products_count': products_count,
                'success': result.success,
                'errors_count': 0 if result.success else 1,
                'scrape_time': scrape_time
            }
            
            breadcrumb_level = "info" if result.success else "warning"
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Product scraping completed - Found: {products_count} products",
                category=CATEGORY_SCRAPER,
                level=breadcrumb_level,
                data={
                    "success": result.success,
                    "products_count": products_count,
                    "duration": scrape_time
                }
            )
            
            # Save to database if requested and scraping was successful
            db_save_result = None
            if save_to_db and result.success and result.products:
                db_save_result = _save_products_to_database(result.products)
                task.record_progress(2, 2, "Database save completed")
            
            # Format response
            response_data = format_scraping_response(result)
            
            # Add database save information to response
            _add_database_info_to_response(response_data, db_save_result, save_to_db)
            
            # Track overall scraping result
            _update_scraping_result_with_db_data(scraping_result, save_to_db, db_save_result)
            
            JuraganMaterialSentryMonitor.track_scraping_result(scraping_result)
            
            # Complete task
            task.complete(success=result.success, result_data=scraping_result)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Unexpected error in scraper: {type(e).__name__}")
            
            # Track error in Sentry
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_products: {str(e)}",
                category=CATEGORY_ERROR,
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return handle_scraping_exception(e, "Juragan Material scraper")


@require_http_methods(["GET"])
def scrape_and_save_products(request):
    """
    Scrape and save products to database.
    
    Query Parameters:
        - keyword: Search keyword (required)
        - sort_type: 'cheapest' (default) or 'popularity'
        - page: Page number (default: 0)
    
    Behavior:
        - sort_type='cheapest': Saves ALL products sorted by lowest price
        - sort_type='popularity': Saves top 5 most relevant products
    """
    # Start Sentry transaction for monitoring
    with track_juragan_material_transaction("juragan_material_scrape_and_save"):
        try:
            # Validate keyword
            keyword = request.GET.get('keyword', '').strip()
            if not keyword:
                return JsonResponse({'error': 'Keyword parameter is required'}, status=400)
            
            # Validate sort_type parameter
            sort_type, error = _validate_sort_type(request.GET.get('sort_type'))
            if error:
                return error
            
            # Determine sort_by_price based on sort_type
            sort_by_price = (sort_type == 'cheapest')
            
            # Parse page parameter
            page_param = request.GET.get('page', '0')
            try:
                page = int(page_param)
            except ValueError:
                return JsonResponse({'error': 'Page parameter must be a valid integer'}, status=400)
            
            # Set scraping context for Sentry
            JuraganMaterialSentryMonitor.set_scraping_context(
                keyword=keyword,
                page=page,
                additional_data={
                    'sort_type': sort_type,
                    'sort_by_price': sort_by_price,
                    'source': 'scrape_and_save_endpoint',
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Create task monitor
            task_id = f"scrape_save_{uuid.uuid4().hex[:8]}"
            task = JuraganMaterialTaskMonitor(task_id=task_id, task_type="scrape_and_save")
            
            # Track scraping start
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Starting scrape and save for keyword: {keyword}",
                category=CATEGORY_SCRAPER,
                level="info",
                data={
                    "keyword": keyword,
                    "page": page,
                    "sort_type": sort_type
                }
            )
            
            # Scrape products
            scrape_start_time = time.time()
            scraper = create_juraganmaterial_scraper()
            result = scraper.scrape_products(
                keyword=keyword,
                sort_by_price=sort_by_price,
                page=page
            )
            scrape_time = time.time() - scrape_start_time
            
            # Update task progress
            task.record_progress(1, 2, f"Scraping completed in {scrape_time:.2f}s")
            
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Scraping completed - Found: {len(result.products) if result.products else 0} products",
                category=CATEGORY_SCRAPER,
                level="info" if result.success else "warning",
                data={
                    "success": result.success,
                    "products_count": len(result.products) if result.products else 0,
                    "duration": scrape_time
                }
            )
            
            if not result.success:
                task.complete(success=False)
                return JsonResponse({
                    'success': False,
                    'error': result.error_message,
                    'saved': 0
                }, status=500)
            
            if not result.products:
                task.complete(success=True, result_data={'products_count': 0})
                return JsonResponse({
                    'success': True,
                    'message': 'No products found to save',
                    'saved': 0
                })
            
            # Pick products based on sort_type (all for cheapest, top 5 for popularity)
            chosen_products = _pick_products(sort_type, result.products)
            
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Selected {len(chosen_products)} products to save (sort_type: {sort_type})",
                category="juragan_material.selection",
                level="info"
            )
            
            # Save to database
            db_save_result = _save_products_to_database(chosen_products)
            
            # Update task progress
            task.record_progress(2, 2, "Database save completed")
            
            if not db_save_result or not db_save_result.get('success', False):
                task.complete(success=False)
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to save products to database',
                    'saved': 0
                }, status=500)
            
            # Track overall result
            overall_result = {
                'products_count': len(chosen_products),
                'success': True,
                'errors_count': 0,
                'scrape_time': scrape_time,
                'db_inserted': db_save_result.get('inserted', 0),
                'db_updated': db_save_result.get('updated', 0),
                'db_categorized': db_save_result.get('categorized', 0)
            }
            
            JuraganMaterialSentryMonitor.track_scraping_result(overall_result)
            task.complete(success=True, result_data=overall_result)
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully saved {len(chosen_products)} products',
                'saved': len(chosen_products),
                'inserted': db_save_result.get('inserted', 0),
                'updated': db_save_result.get('updated', 0),
                'categorized': db_save_result.get('categorized', 0),
                'anomalies': db_save_result.get('anomalies', []),
                'sort_type': sort_type,
                'url': result.url
            })
            
        except Exception as e:
            logger.error(f"Unexpected error in scrape_and_save: {str(e)}")
            
            # Track error in Sentry
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_and_save_products: {str(e)}",
                category=CATEGORY_ERROR,
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return handle_scraping_exception(e, "Juragan Material scrape-and-save")


@require_http_methods(["GET"])
def scrape_popularity(request):
    """
    Scrape products sorted by popularity (relevance) and return top 5 most relevant products.
    
    Query Parameters:
        - keyword: Search keyword (required)
        - page: Page number to scrape (default: 0)
        - top_n: Number of top products to return (default: 5)
    """
    # Start Sentry transaction for monitoring
    with track_juragan_material_transaction("juragan_material_scrape_popularity"):
        try:
            # Validate keyword
            keyword = request.GET.get('keyword', '').strip()
            if not keyword:
                return JsonResponse({'error': 'Keyword parameter is required'}, status=400)
            
            # Parse page parameter
            page_param = request.GET.get('page', '0')
            try:
                page = int(page_param)
            except ValueError:
                return JsonResponse({'error': 'Page parameter must be a valid integer'}, status=400)
            
            # Parse top_n parameter
            top_n_param = request.GET.get('top_n', '5')
            try:
                top_n = int(top_n_param)
                if top_n < 1:
                    top_n = 5
            except ValueError:
                return JsonResponse({'error': 'top_n parameter must be a valid positive integer'}, status=400)
            
            # Set scraping context for Sentry
            JuraganMaterialSentryMonitor.set_scraping_context(
                keyword=keyword,
                page=page,
                additional_data={
                    'sort_type': 'popularity',
                    'top_n': top_n,
                    'source': 'scrape_popularity_endpoint',
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Create task monitor
            task_id = f"scrape_pop_{uuid.uuid4().hex[:8]}"
            task = JuraganMaterialTaskMonitor(task_id=task_id, task_type="scrape_popularity")
            
            # Track scraping start
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Starting popularity scraping for keyword: {keyword} (top {top_n})",
                category=CATEGORY_SCRAPER,
                level="info",
                data={
                    "keyword": keyword,
                    "page": page,
                    "top_n": top_n
                }
            )
            
            # Scrape with popularity sorting
            scrape_start_time = time.time()
            scraper = create_juraganmaterial_scraper()
            result = scraper.scrape_popularity_products(
                keyword=keyword,
                page=page,
                top_n=top_n
            )
            scrape_time = time.time() - scrape_start_time
            
            # Update task progress
            task.record_progress(1, 1, f"Popularity scraping completed in {scrape_time:.2f}s")
            
            # Track scraping result
            scraping_result = {
                'products_count': len(result.products) if result.products else 0,
                'success': result.success,
                'errors_count': 0 if result.success else 1,
                'scrape_time': scrape_time,
                'top_n': top_n
            }
            
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Popularity scraping completed - Found: {len(result.products) if result.products else 0} products",
                category=CATEGORY_SCRAPER,
                level="info" if result.success else "warning",
                data={
                    "success": result.success,
                    "products_count": len(result.products) if result.products else 0,
                    "duration": scrape_time,
                    "top_n": top_n
                }
            )
            
            # Convert to dictionary format
            products_data = _convert_products_to_dict(result.products)
            
            response_data = {
                'success': result.success,
                'products': products_data,
                'error_message': result.error_message,
                'url': result.url,
                'total_products': len(products_data)
            }
            
            # Track overall result
            JuraganMaterialSentryMonitor.track_scraping_result(scraping_result)
            task.complete(success=result.success, result_data=scraping_result)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Unexpected error in scrape popularity: {str(e)}")
            
            # Track error in Sentry
            JuraganMaterialSentryMonitor.add_breadcrumb(
                f"Fatal error in scrape_popularity: {str(e)}",
                category=CATEGORY_ERROR,
                level="error"
            )
            
            if 'task' in locals():
                task.complete(success=False)
            
            return JsonResponse({'error': 'Internal server error occurred'}, status=500)