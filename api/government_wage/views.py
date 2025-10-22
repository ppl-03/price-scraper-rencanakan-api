"""
Government Wage Scraper API Views

This module provides API endpoints for scraping government wage data from various regions in Central Java.

Available endpoints:
1. /api/government_wage/scrape/ - Scrape wage data for a specific region
2. /api/government_wage/search/ - Search wage data by work code
3. /api/government_wage/regions/ - Get list of available regions
4. /api/government_wage/scrape-all/ - Scrape data from all regions (use with caution)

Example usage:
- GET /api/government_wage/scrape/?region=Kab. Cilacap
- GET /api/government_wage/search/?work_code=6.1.1&region=Kab. Cilacap
- GET /api/government_wage/regions/
- GET /api/government_wage/scrape-all/?max_regions=5
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .factory import create_government_wage_scraper
import logging

logger = logging.getLogger(__name__)


def _create_error_response(message, status=400):
    """Helper function to create error responses"""
    return JsonResponse({'error': message}, status=status)


@require_http_methods(["GET"])
def scrape_region_data(request):
    """
    Scrape government wage data for a specific region.
    
    Parameters:
    - region: The region to scrape (optional, defaults to "Kab. Cilacap")
    
    Returns:
    - JSON response with scraped wage data
    """
    try:
        region = request.GET.get('region', 'Kab. Cilacap')
        
        if not region.strip():
            return _create_error_response('Region parameter cannot be empty')
        
        region = region.strip()
        
        # Create scraper and scrape region data
        scraper = create_government_wage_scraper()
        
        with scraper:
            items = scraper.scrape_region_data(region)
        
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
            'error_message': None
        }
        
        logger.info(f"Government wage scraping successful for region '{region}': {len(items)} items found")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Government Wage API (region scraping): {str(e)}", exc_info=True)
        return _create_error_response('Internal server error occurred', 500)


@require_http_methods(["GET"])
def search_by_work_code(request):
    """
    Search government wage data by work code.
    
    Parameters:
    - work_code: The work code to search for (required)
    - region: The region to search in (optional)
    
    Returns:
    - JSON response with matching wage data
    """
    try:
        work_code = request.GET.get('work_code')
        if not work_code or not work_code.strip():
            return _create_error_response('Work code parameter is required')
        
        work_code = work_code.strip()
        region = request.GET.get('region')  # Optional parameter
        
        # Create scraper and search by work code
        scraper = create_government_wage_scraper()
        
        with scraper:
            items = scraper.search_by_work_code(work_code, region)
        
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
            'work_code': work_code,
            'region': region,
            'data': wage_data,
            'count': len(wage_data),
            'error_message': None
        }
        
        logger.info(f"Government wage search successful for work code '{work_code}' in region '{region}': {len(items)} items found")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Government Wage API (work code search): {str(e)}", exc_info=True)
        return _create_error_response('Internal server error occurred', 500)


@require_http_methods(["GET"])
def get_available_regions(request):
    """
    Get list of available regions for government wage data.
    
    Returns:
    - JSON response with list of available regions
    """
    try:
        scraper = create_government_wage_scraper()
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
        return _create_error_response('Internal server error occurred', 500)


@require_http_methods(["GET"])
def scrape_all_regions(request):
    """
    Scrape government wage data for all available regions.
    
    Parameters:
    - max_regions: Maximum number of regions to scrape (optional)
    
    Returns:
    - JSON response with wage data from all regions
    
    Warning: This endpoint may take a long time to complete as it scrapes all regions.
    """
    try:
        max_regions_param = request.GET.get('max_regions')
        max_regions = None
        
        if max_regions_param:
            try:
                max_regions = int(max_regions_param)
                if max_regions <= 0:
                    return _create_error_response('Max regions parameter must be a positive integer')
            except ValueError:
                return _create_error_response('Max regions parameter must be a valid integer')
        
        # Create scraper and scrape all regions
        scraper = create_government_wage_scraper()
        
        with scraper:
            items = scraper.scrape_all_regions(max_regions)
        
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
        
        logger.info(f"Government wage scraping successful for all regions: {len(items)} total items from {len(regions_data)} regions")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Government Wage API (scrape all regions): {str(e)}", exc_info=True)
        return _create_error_response('Internal server error occurred', 500)