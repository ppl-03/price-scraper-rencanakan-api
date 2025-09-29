from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .factory import create_juraganmaterial_scraper
import json
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        keyword = request.GET.get('keyword')
        if not keyword or not keyword.strip():
            return JsonResponse({
                'error': 'Keyword parameter is required'
            }, status=400)
        
        keyword = keyword.strip()
        
        sort_by_price_param = request.GET.get('sort_by_price', 'true').lower()
        sort_by_price = sort_by_price_param in ['true', '1', 'yes']
        
        page_param = request.GET.get('page', '0')
        try:
            page = int(page_param)
        except ValueError:
            return JsonResponse({
                'error': 'Page parameter must be a valid integer'
            }, status=400)
        
        scraper = create_juraganmaterial_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
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
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in Juragan Material scraper: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error occurred'
        }, status=500)