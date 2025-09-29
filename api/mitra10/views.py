from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .factory import create_mitra10_scraper
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        query = request.GET.get('q')
        if query is None:
            return JsonResponse({
                'success': False,
                'products': [],
                'error_message': 'Query parameter is required',
                'url': ''
            }, status=400)
        
        if not query.strip():
            return JsonResponse({
                'success': False,
                'products': [],
                'error_message': 'Query parameter cannot be empty',
                'url': ''
            }, status=400)
        
        query = query.strip()
        
        # Parse sort_by_price parameter
        sort_by_price_param = request.GET.get('sort_by_price', 'true').lower()
        sort_by_price = sort_by_price_param in ['true', '1', 'yes']
        
        # Parse page parameter
        page_param = request.GET.get('page', '0')
        try:
            page = int(page_param)
        except ValueError:
            return JsonResponse({
                'success': False,
                'products': [],
                'error_message': 'Page parameter must be a valid integer',
                'url': ''
            }, status=400)
        
        # Create scraper and scrape products
        scraper = create_mitra10_scraper()
        result = scraper.scrape_products(
            keyword=query,
            sort_by_price=sort_by_price,
            page=page
        )
        
        # Format products data
        products_data = [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url
            }
            for product in result.products
        ]
        
        response_data = {
            'success': result.success,
            'products': products_data,
            'error_message': result.error_message,
            'url': result.url
        }
        
        logger.info(f"Mitra10 scraping successful for query '{query}': {len(result.products)} products found")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Mitra10 API: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'Internal server error occurred'
        }, status=500)