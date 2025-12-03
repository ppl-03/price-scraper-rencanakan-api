from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .scraper import get_cached_or_scrape
import logging
import time

logger = logging.getLogger(__name__)

# Error message constants
INTERNAL_SERVER_ERROR_MSG = 'Internal server error occurred'


def _create_error_response(message, status=400):
    """Helper function to create error responses"""
    return JsonResponse({'error': message}, status=status)


@require_http_methods(["GET"])
def scrape_region_data(request):
    try:
        region = request.GET.get('region', 'Kab. Cilacap')
        
        if not region.strip():
            return _create_error_response('Region parameter cannot be empty')
        
        region = region.strip()
        year = request.GET.get('year', '2025')
        
        # Validate inputs to prevent path traversal attacks
        from .scraper import _validate_region, _validate_year
        try:
            region = _validate_region(region)
            year = _validate_year(year)
        except ValueError as ve:
            return _create_error_response(str(ve))
        force_refresh = request.GET.get('force_refresh', 'false').lower() == 'true'
        
        # Get data from cache or scrape if needed
        start_time = time.time()
        items = get_cached_or_scrape(region, year, force_refresh)
        data_load_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Format wage data
        wage_data = [
            {
                'item_number': item.item_number,
                'work_code': item.work_code,
                'work_description': item.work_description,
                'unit': item.unit,
                'unit_price_idr': item.unit_price_idr,
                'region': item.region,
                'edition': item.edition,
                'year': item.year,
                'sector': item.sector
            }
            for item in items
        ]
        
        response_data = {
            'success': True,
            'region': region,
            'data': wage_data,
            'count': len(wage_data),
            'error_message': None,
            'data_load_time_ms': round(data_load_time, 2),  # Show cache performance
        }
        
        logger.info(f"Government wage data retrieved for region '{region}': {len(items)} items (load time: {data_load_time:.2f}ms)")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Government Wage API (region scraping): {str(e)}", exc_info=True)
        return _create_error_response(INTERNAL_SERVER_ERROR_MSG, 500)


@require_http_methods(["GET"])
def search_by_work_code(request):
    try:
        work_code = request.GET.get('work_code')
        if not work_code or not work_code.strip():
            return _create_error_response('Work code parameter is required')
        
        work_code = work_code.strip()
        region = request.GET.get('region', 'Kab. Cilacap')  # Default to Cilacap
        year = request.GET.get('year', '2025')
        
        # Validate inputs to prevent path traversal attacks
        from .scraper import _validate_region, _validate_year
        try:
            region = _validate_region(region)
            year = _validate_year(year)
        except ValueError as ve:
            return _create_error_response(str(ve))
        
        # Get cached data for the region
        items = get_cached_or_scrape(region, year, force_refresh=False)
        
        # Filter by work code (case-insensitive partial match)
        filtered_items = [
            item for item in items 
            if work_code.lower() in item.work_code.lower()
        ]
        
        # Format wage data
        wage_data = [
            {
                'item_number': item.item_number,
                'work_code': item.work_code,
                'work_description': item.work_description,
                'unit': item.unit,
                'unit_price_idr': item.unit_price_idr,
                'region': item.region,
                'edition': item.edition,
                'year': item.year,
                'sector': item.sector
            }
            for item in filtered_items
        ]
        
        response_data = {
            'success': True,
            'work_code': work_code,
            'region': region,
            'data': wage_data,
            'count': len(wage_data),
            'error_message': None,
        }
        
        logger.info(f"Government wage search successful for work code '{work_code}' in region '{region}': {len(filtered_items)} items found")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Government Wage API (work code search): {str(e)}", exc_info=True)
        return _create_error_response(INTERNAL_SERVER_ERROR_MSG, 500)


@require_http_methods(["GET"])
def get_available_regions(request):
    try:
        from .scraper import GovernmentWageScraper
        
        # Just return the static list, no need to scrape
        scraper = GovernmentWageScraper()
        regions = scraper.get_available_regions()
        
        response_data = {
            'success': True,
            'regions': regions,
            'count': len(regions),
            'error_message': None
        }
        
        logger.info(f"Retrieved {len(regions)} available regions")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Government Wage API (get regions): {str(e)}", exc_info=True)
        return _create_error_response(INTERNAL_SERVER_ERROR_MSG, 500)


@require_http_methods(["GET"])
def scrape_all_regions(request):
    try:
        from .scraper import GovernmentWageScraper, scrape_and_cache
        
        max_regions_param = request.GET.get('max_regions')
        year = request.GET.get('year', '2025')
        
        # Validate year to prevent path traversal attacks
        from .scraper import _validate_year
        try:
            year = _validate_year(year)
        except ValueError as ve:
            return _create_error_response(str(ve))
        
        max_regions = None
        
        if max_regions_param:
            try:
                max_regions = int(max_regions_param)
                if max_regions <= 0:
                    return _create_error_response('Max regions parameter must be a positive integer')
            except ValueError:
                return _create_error_response('Max regions parameter must be a valid integer')
        
        # Get list of regions
        scraper = GovernmentWageScraper()
        regions_to_scrape = scraper.get_available_regions()
        if max_regions:
            regions_to_scrape = regions_to_scrape[:max_regions]
        
        # Scrape and cache each region
        all_items = []
        for region in regions_to_scrape:
            items = scrape_and_cache(region, year)
            all_items.extend(items)
        
        # Format wage data
        wage_data = [
            {
                'item_number': item.item_number,
                'work_code': item.work_code,
                'work_description': item.work_description,
                'unit': item.unit,
                'unit_price_idr': item.unit_price_idr,
                'region': item.region,
                'edition': item.edition,
                'year': item.year,
                'sector': item.sector
            }
            for item in all_items
        ]
        
        # Group data by region for better organization
        regions_data = {}
        for item_data in wage_data:
            region = item_data['region']
            if region not in regions_data:
                regions_data[region] = []
            regions_data[region].append(item_data)
        
        response_data = {
            'success': True,
            'total_items': len(wage_data),
            'total_regions': len(regions_data),
            'max_regions_requested': max_regions,
            'data': wage_data,
            'regions_data': regions_data,
            'error_message': None
        }
        
        logger.info(f"Government wage scraping successful for all regions: {len(all_items)} total items from {len(regions_data)} regions")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Government Wage API (scrape all regions): {str(e)}", exc_info=True)
        return _create_error_response(INTERNAL_SERVER_ERROR_MSG, 500)