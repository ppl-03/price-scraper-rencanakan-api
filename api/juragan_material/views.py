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
        # Format products for database saving
        # products_data = [
        #     {
        #         'name': product.name,
        #         'price': product.price,
        #         'url': product.url,
        #         'unit': product.unit,
        #         'location': product.location
        #     }
        #     for product in products
        # ]
        
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
    try:
        # Validate request parameters
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        if error_response:
            return error_response
        
        # Perform scraping and force saving to database
        response_data, _, _ = _perform_scraping_and_save(keyword, sort_by_price, page, save_to_db=True)
        
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return handle_scraping_exception(e, "Juragan Material scrape-and-save")