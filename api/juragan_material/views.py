from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_juraganmaterial_scraper
from .database_service import JuraganMaterialDatabaseService
from api.views_utils import validate_scraping_request, format_scraping_response, handle_scraping_exception
import logging

logger = logging.getLogger(__name__)


def _save_products_to_database(products):
    """
    Helper function to save products to database.
    
    Args:
        products: List of product objects from scraping result
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    if not products:
        return False
    
    try:
        # Save to database
        db_service = JuraganMaterialDatabaseService()
        result = db_service.save(products)
        
        if result:
            logger.info(f"Juragan Material: Saved {len(products)} products to database")
        else:
            logger.error("Juragan Material: Failed to save products to database")
        
        return result
        
    except Exception as db_error:
        logger.error(f"Failed to save Juragan Material products to database: {str(db_error)}")
        return False


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
def scrape_products(request):
    try:
        # Validate request parameters
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        if error_response:
            return error_response
        
        # Check if we should save to database
        save_to_db_param = request.GET.get('save_to_db', 'false').lower()
        save_to_db = save_to_db_param in ['true', '1', 'yes']
        
        # Perform scraping and optional saving
        response_data, _, _ = _perform_scraping_and_save(keyword, sort_by_price, page, save_to_db)
            
        return JsonResponse(response_data)
        
    except Exception as e:
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
        
        if not db_save_result:
            return JsonResponse({
                'success': False,
                'error': 'Failed to save products to database',
                'saved': 0
            }, status=500)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully saved {len(chosen_products)} products',
            'saved': len(chosen_products),
            'sort_type': sort_type,
            'url': result.url
        })
        
    except Exception as e:
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