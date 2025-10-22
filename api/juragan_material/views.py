from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_juraganmaterial_scraper
from .database_service import JuraganMaterialDatabaseService
from api.views_utils import validate_scraping_request, format_scraping_response, handle_scraping_exception
import logging

logger = logging.getLogger(__name__)


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
            try:
                # Format products for database saving
                products_data = [
                    {
                        'name': product.name,
                        'price': product.price,
                        'url': product.url,
                        'unit': product.unit if product.unit else ''
                    }
                    for product in result.products
                ]
                
                # Save to database
                db_service = JuraganMaterialDatabaseService()
                db_save_result = db_service.save(products_data)
                
                logger.info(f"Juragan Material: Saved {len(products_data)} products to database")
                
            except Exception as db_error:
                logger.error(f"Failed to save Juragan Material products to database: {str(db_error)}")
                db_save_result = False
        
        # Format and return response
        response_data = format_scraping_response(result)
        
        # Add database save information to response
        if save_to_db:
            response_data['saved_to_database'] = db_save_result
            response_data['database_save_attempted'] = True
        else:
            response_data['saved_to_database'] = False
            response_data['database_save_attempted'] = False
            
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
        
        # Perform scraping
        scraper = create_juraganmaterial_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        # Save to database if scraping was successful
        db_save_result = None
        if result.success and result.products:
            try:
                # Format products for database saving
                products_data = [
                    {
                        'name': product.name,
                        'price': product.price,
                        'url': product.url,
                        'unit': product.unit if product.unit else ''
                    }
                    for product in result.products
                ]
                
                # Save to database
                db_service = JuraganMaterialDatabaseService()
                db_save_result = db_service.save(products_data)
                
                logger.info(f"Juragan Material: Saved {len(products_data)} products to database")
                
            except Exception as db_error:
                logger.error(f"Failed to save Juragan Material products to database: {str(db_error)}")
                db_save_result = False
        
        # Format and return response
        response_data = format_scraping_response(result)
        
        # Add database save information to response
        response_data['saved_to_database'] = db_save_result
        response_data['database_save_attempted'] = True
            
        return JsonResponse(response_data)
        
    except Exception as e:
        return handle_scraping_exception(e, "Juragan Material scrape-and-save")