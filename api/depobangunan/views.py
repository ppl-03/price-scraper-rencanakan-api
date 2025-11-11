from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_depo_scraper, create_depo_location_scraper
from .database_service import DepoBangunanDatabaseService
import logging

logger = logging.getLogger(__name__)

# Error message constants
ERROR_KEYWORD_REQUIRED = 'Keyword parameter is required'
ERROR_PAGE_INVALID = 'Page parameter must be a valid integer'
ERROR_INTERNAL_SERVER = 'Internal server error occurred'


def _create_error_response(message, status=400):
    return JsonResponse({'error': message}, status=status)


def _validate_and_parse_keyword(keyword):
    """Validate and parse keyword parameter"""
    if not keyword or not keyword.strip():
        return None, _create_error_response(ERROR_KEYWORD_REQUIRED)
    return keyword.strip(), None


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


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        # Validate and parse parameters
        keyword, error = _validate_and_parse_keyword(request.GET.get('keyword'))
        if error:
            return error
        
        # Handle both sort_type and sort_by_price parameters
        sort_type = request.GET.get('sort_type', '').lower()
        sort_by_price_param = request.GET.get('sort_by_price', 'true')
        
        # Validate sort_type if provided
        if sort_type and sort_type not in ['cheapest', 'popularity']:
            return _create_error_response('Invalid sort_type. Must be either "cheapest" or "popularity"')
        
        # Determine sort_by_price based on sort_type or sort_by_price parameter
        if sort_type:
            sort_by_price = (sort_type == 'cheapest')
            final_sort_type = sort_type
        else:
            sort_by_price = _parse_sort_by_price(sort_by_price_param)
            final_sort_type = 'cheapest' if sort_by_price else 'popularity'
        
        page, error = _parse_page(request.GET.get('page', '0'))
        if error:
            return error
        
        scraper = create_depo_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        # Scrape locations and get location names
        try:
            location_scraper = create_depo_location_scraper()
            loc_result = location_scraper.scrape_locations(timeout=30)
            if loc_result.success and loc_result.locations:
                # Join location names into a single string
                run_location_value = ', '.join([location.name for location in loc_result.locations])
            else:
                run_location_value = ''
        except Exception as e:
            logger.warning(f"Failed to scrape locations; continuing without locations: {e}")
            run_location_value = ''
        
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
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Depo Bangunan scraper: {str(e)}")
        return _create_error_response(ERROR_INTERNAL_SERVER, 500)


@require_http_methods(["GET"])
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
def scrape_and_save_products(request):
    try:
        # Validate and parse parameters
        keyword, error = _validate_and_parse_keyword(request.POST.get('keyword'))
        if error:
            return error
        
        # Parse sort_type parameter ('cheapest' or 'popularity')
        sort_type = request.POST.get('sort_type', '').lower()
        
        # Validate sort_type if provided
        if sort_type and sort_type not in ['cheapest', 'popularity']:
            return _create_error_response('Invalid sort_type. Must be either "cheapest" or "popularity"')
        
        # Handle backward compatibility with sort_by_price
        sort_by_price_param = request.POST.get('sort_by_price', 'true')
        sort_by_price = _parse_sort_by_price(sort_by_price_param)
        
        # Determine final sort_type
        if not sort_type:
            sort_type = 'cheapest' if sort_by_price else 'popularity'
        
        page, error = _parse_page(request.POST.get('page', '0'))
        if error:
            return error
        
        # Check if price update mode is requested
        use_price_update = request.POST.get('use_price_update', 'false').lower() in ['true', '1', 'yes']
        
        scraper = create_depo_scraper()
        
        # Choose scraping method based on sort_type
        if sort_type == 'popularity':
            result = scraper.scrape_popularity_products(
                keyword=keyword,
                top_n=5,
                page=page
            )
            # Sort products by sold_count in descending order
            if result.success and result.products:
                products_with_sold_count = [p for p in result.products if hasattr(p, 'sold_count') and p.sold_count is not None]
                products_without_sold_count = [p for p in result.products if not hasattr(p, 'sold_count') or p.sold_count is None]
                
                # Sort products with sold_count
                products_with_sold_count.sort(key=lambda p: p.sold_count, reverse=True)
                
                # Take top 5 products with sold_count, or all if less than 5
                result.products = products_with_sold_count[:5] + products_without_sold_count[:max(0, 5-len(products_with_sold_count))]
        else:
            # Default to scrape_products (cheapest)
            result = scraper.scrape_products(
                keyword=keyword,
                sort_by_price=sort_by_price,
                page=page
            )
        
        if not result.success:
            return _create_error_response(result.error_message, 500)
        
        if not result.products:
            return JsonResponse({
                'success': True,
                'message': 'No products found to save',
                'saved': 0,
                'inserted': 0,
                'updated': 0,
                'anomalies': []
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
        
        if use_price_update:
            # Use price update mode
            save_result = db_service.save_with_price_update(products_data)
            
            if not save_result.get('success'):
                return _create_error_response('Failed to save products to database', 500)
            
            response_data = {
                'success': True,
                'message': 'Products scraped and saved with price update',
                'saved': save_result.get('updated_count', 0) + save_result.get('new_count', 0),
                'inserted': save_result.get('new_count', 0),
                'updated': save_result.get('updated_count', 0),
                'anomalies': save_result.get('anomalies', []),
                'url': result.url
            }
        else:
            # Regular save mode
            save_result = db_service.save(products_data)
            
            if not save_result:
                return _create_error_response('Failed to save products to database', 500)
            
            response_data = {
                'success': True,
                'message': f'Successfully saved {len(products_data)} products',
                'saved': len(products_data),
                'inserted': len(products_data),
                'updated': 0,
                'anomalies': [],
                'url': result.url
            }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in scrape and save: {str(e)}")
        return _create_error_response(ERROR_INTERNAL_SERVER, 500)


@require_http_methods(["GET"])
def scrape_popularity(request):
    """Scrape products sorted by popularity and return top N best sellers."""
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
        
        # Create scraper and scrape top N products by popularity
        scraper = create_depo_scraper()
        result = scraper.scrape_popularity_products(
            keyword=keyword,
            top_n=top_n,
            page=page
        )
        
        # Scrape locations and get location names
        run_location_value = _scrape_location_names()
        
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
        
        response_data = {
            'success': result.success,
            'products': products_data,
            'total_products': len(products_data),
            'error_message': result.error_message,
            'url': result.url
        }
        
        logger.info(f"DepoBangunan popularity scraping successful for keyword '{keyword}': {len(result.products)} best sellers found")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in scrape_popularity: {str(e)}", exc_info=True)
        return _create_error_response(ERROR_INTERNAL_SERVER, 500)


@require_http_methods(["POST"])
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
            return _create_error_response('Failed to save products to database', 500)
        
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
