from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_juraganmaterial_scraper
from .database_service import JuraganMaterialDatabaseService
from .security import (
    require_api_token,
    enforce_resource_limits,
    InputValidator,
)
from api.views_utils import validate_scraping_request, format_scraping_response, handle_scraping_exception
from db_pricing.auto_categorization_service import AutoCategorizationService
import logging

logger = logging.getLogger(__name__)


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
        
        # Save to database with price update
        db_service = JuraganMaterialDatabaseService()
        result = db_service.save_with_price_update(products_data)
        
        # Auto-categorize newly inserted products
        categorized_count = 0
        if result.get('success') and result.get('inserted', 0) > 0:
            try:
                from db_pricing.models import JuraganMaterialProduct
                
                # Get recently inserted products (ones without category)
                uncategorized_products = JuraganMaterialProduct.objects.filter(category='').order_by('-id')[:result['inserted']]
                product_ids = list(uncategorized_products.values_list('id', flat=True))
                
                if product_ids:
                    categorization_service = AutoCategorizationService()
                    categorization_result = categorization_service.categorize_products('juragan_material', product_ids)
                    categorized_count = categorization_result.get('categorized', 0)
                    logger.info(f"Auto-categorized {categorized_count} out of {len(product_ids)} new Juragan Material products")
            except Exception as cat_error:
                logger.warning(f"Auto-categorization failed: {str(cat_error)}")
                # Don't fail the entire operation if categorization fails
        
        result['categorized'] = categorized_count
        return result
        
    except Exception as db_error:
        logger.error(f"Failed to save Juragan Material products to database: {str(db_error)}")
        return {'success': False, 'updated': 0, 'inserted': 0, 'anomalies': [], 'categorized': 0}


def _perform_scraping_and_save(keyword, sort_by_price, page, save_to_db=False):
    """
    Helper function to perform scraping and optionally save to database.
    
    Args:
        keyword: Search keyword
        sort_by_price: Whether to sort by price
        page: Page number
        save_to_db: Whether to save results to database
        
    Returns:
        tuple: (response_data, db_save_result, db_save_attempted)
    """
    # Perform scraping
    scraper = create_juraganmaterial_scraper()
    result = scraper.scrape_products(
        keyword=keyword,
        sort_by_price=sort_by_price,
        page=page
    )
    
    # Save to database if requested and scraping was successful
    db_save_result = None
    if save_to_db and result.success and result.products:
        db_save_result = _save_products_to_database(result.products)
    
    # Format response
    response_data = format_scraping_response(result)
    
    # Add database save information to response
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
    
    return response_data, db_save_result, save_to_db


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


@require_http_methods(["GET"])
@require_api_token(required_permission='read')
@enforce_resource_limits
def scrape_products(request):
    """
    Scrape products from Juragan Material.
    
    Security (OWASP A03:2021 - Injection Prevention):
    - Validates and sanitizes all user input
    - Uses whitelist validation for parameters
    - Prevents SQL injection, command injection, and XSS
    """
    try:
        # SECURITY: Validate keyword parameter to prevent injection
        keyword_raw = request.GET.get('keyword', '').strip()
        is_valid, error_msg, keyword = InputValidator.validate_keyword(keyword_raw)
        
        if not is_valid:
            logger.warning(f"Invalid keyword rejected: {InputValidator.sanitize_for_logging(keyword_raw)}")
            return JsonResponse({'error': error_msg or 'Invalid keyword'}, status=400)
        
        # SECURITY: Validate page parameter (integer validation)
        page_raw = request.GET.get('page', '0')
        is_valid, page, error_msg = InputValidator.validate_integer_param(
            page_raw, 'page', min_val=None, max_val=100
        )
        
        if not is_valid:
            logger.warning(f"Invalid page parameter: {InputValidator.sanitize_for_logging(page_raw)}")
            return JsonResponse({'error': error_msg or 'Invalid page'}, status=400)
        
        # SECURITY: Validate sort_by_price parameter (boolean validation)
        sort_raw = request.GET.get('sort_by_price', 'true')
        is_valid, sort_by_price, error_msg = InputValidator.validate_boolean_param(sort_raw, 'sort_by_price')
        
        if not is_valid:
            logger.warning(f"Invalid sort_by_price parameter: {InputValidator.sanitize_for_logging(sort_raw)}")
            return JsonResponse({'error': error_msg or 'Invalid sort_by_price'}, status=400)
        
        # SECURITY: Validate save_to_db parameter (boolean validation)
        save_raw = request.GET.get('save_to_db', 'false')
        is_valid, save_to_db, error_msg = InputValidator.validate_boolean_param(save_raw, 'save_to_db')
        
        if not is_valid:
            logger.warning(f"Invalid save_to_db parameter: {InputValidator.sanitize_for_logging(save_raw)}")
            return JsonResponse({'error': error_msg or 'Invalid save_to_db'}, status=400)
        
        logger.info(f"Scraping request validated: keyword={InputValidator.sanitize_for_logging(keyword)}, page={page}")
        
        # Perform scraping and optional saving
        response_data, _, _ = _perform_scraping_and_save(keyword, sort_by_price, page, save_to_db)
            
        return JsonResponse(response_data)
        
    except Exception as e:
        return handle_scraping_exception(e, "Juragan Material scraper")


@require_http_methods(["GET"])
@require_api_token(required_permission='write')
@enforce_resource_limits
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
    
    Security (OWASP A03:2021 - Injection Prevention):
    - Validates and sanitizes all user input
    - Uses whitelist validation for sort_type
    - Prevents injection attacks through comprehensive input validation
    """
    try:
        # SECURITY: Validate keyword parameter
        keyword_raw = request.GET.get('keyword', '').strip()
        is_valid, error_msg, keyword = InputValidator.validate_keyword(keyword_raw)
        
        if not is_valid:
            logger.warning(f"Invalid keyword in scrape_and_save: {InputValidator.sanitize_for_logging(keyword_raw)}")
            return JsonResponse({'error': error_msg or 'Invalid keyword'}, status=400)
        
        # SECURITY: Validate sort_type using whitelist approach
        sort_type_raw = request.GET.get('sort_type', 'cheapest')
        is_valid, sort_type, error_msg = InputValidator.validate_sort_type(sort_type_raw)
        
        if not is_valid:
            logger.warning(f"Invalid sort_type: {InputValidator.sanitize_for_logging(sort_type_raw)}")
            return JsonResponse({'error': error_msg or 'Invalid sort_type'}, status=400)
        
        # Determine sort_by_price based on validated sort_type
        sort_by_price = (sort_type == 'cheapest')
        
        # SECURITY: Validate page parameter
        page_raw = request.GET.get('page', '0')
        is_valid, page, error_msg = InputValidator.validate_integer_param(
            page_raw, 'page', min_val=0, max_val=100
        )
        
        if not is_valid:
            logger.warning(f"Invalid page parameter in scrape_and_save: {InputValidator.sanitize_for_logging(page_raw)}")
            return JsonResponse({'error': error_msg or 'Invalid page'}, status=400)
        
        logger.info(f"Validated scrape_and_save request: keyword={InputValidator.sanitize_for_logging(keyword)}, sort_type={sort_type}, page={page}")
        
        # Scrape products
        scraper = create_juraganmaterial_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        if not result.success:
            return JsonResponse({
                'success': False,
                'error': result.error_message,
                'saved': 0
            }, status=500)
        
        if not result.products:
            return JsonResponse({
                'success': True,
                'message': 'No products found to save',
                'saved': 0
            })
        
        # Pick products based on sort_type (all for cheapest, top 5 for popularity)
        chosen_products = _pick_products(sort_type, result.products)
        
        # Save to database
        db_save_result = _save_products_to_database(chosen_products)
        
        if not db_save_result or not db_save_result.get('success', False):
            return JsonResponse({
                'success': False,
                'error': 'Failed to save products to database',
                'saved': 0
            }, status=500)
        
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
        return handle_scraping_exception(e, "Juragan Material scrape-and-save")


@require_http_methods(["GET"])
@require_api_token(required_permission='read')
@enforce_resource_limits
def scrape_popularity(request):
    """
    Scrape products sorted by popularity (relevance) and return top 5 most relevant products.
    
    Query Parameters:
        - keyword: Search keyword (required)
        - page: Page number to scrape (default: 0)
        - top_n: Number of top products to return (default: 5)
    """
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
        
        # Scrape with popularity sorting
        scraper = create_juraganmaterial_scraper()
        result = scraper.scrape_popularity_products(
            keyword=keyword,
            page=page,
            top_n=top_n
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
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in scrape popularity: {str(e)}")
        return JsonResponse({'error': 'Internal server error occurred'}, status=500)