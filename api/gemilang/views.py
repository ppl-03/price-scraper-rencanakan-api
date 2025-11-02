from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import logging

from .factory import create_gemilang_scraper, create_gemilang_location_scraper
from .database_service import GemilangDatabaseService
from .security import (
    require_api_token,
    validate_input,
    enforce_resource_limits,
    InputValidator,
    SecurityDesignPatterns,
)

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@enforce_resource_limits
@validate_input({
    'keyword': lambda x: InputValidator.validate_keyword(x or '', max_length=100),
    'page': lambda x: InputValidator.validate_integer(
        int(x) if x else 0, 
        'page', 
        min_value=0, 
        max_value=100
    ),
    'sort_by_price': lambda x: InputValidator.validate_boolean(x, 'sort_by_price')
})
def scrape_products(request):
    try:
        validated_data = request.validated_data
        keyword = validated_data.get('keyword')
        sort_by_price = validated_data.get('sort_by_price', True)
        page = validated_data.get('page', 0)
        
        scraper = create_gemilang_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        products_data = [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url,
                'unit': product.unit
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
        logger.error(f"Unexpected error in scraper: {type(e).__name__}")
        return JsonResponse({
            'error': 'Internal server error occurred'
        }, status=500)


@require_http_methods(["GET"])
@validate_input({
    'timeout': lambda x: InputValidator.validate_integer(
        int(x) if x else 30,
        'timeout',
        min_value=0,
        max_value=120
    )
})
def gemilang_locations_view(request):
    try:
        validated_data = request.validated_data
        timeout = validated_data.get('timeout', 30)
        
        scraper = create_gemilang_location_scraper()
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
        logger.error(f"Unexpected error in locations endpoint: {type(e).__name__}")
        return JsonResponse({
            'error': 'Internal server error occurred'
        }, status=500)


@require_http_methods(["POST"])
@require_api_token(required_permission='write')
@enforce_resource_limits
def scrape_and_save(request):
    try:
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        keyword = body.get('keyword')
        is_valid, error_msg, sanitized_keyword = InputValidator.validate_keyword(
            keyword or '', max_length=100
        )
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)
        
        page = body.get('page', 0)
        is_valid, error_msg, validated_page = InputValidator.validate_integer(
            page, 'page', min_value=0, max_value=100
        )
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)
        
        sort_by_price = body.get('sort_by_price', True)
        is_valid, error_msg, validated_sort = InputValidator.validate_boolean(
            sort_by_price, 'sort_by_price'
        )
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)
        
        use_price_update = body.get('use_price_update', False)
        is_valid, error_msg, validated_update = InputValidator.validate_boolean(
            use_price_update, 'use_price_update'
        )
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)
        
        scraper = create_gemilang_scraper()
        result = scraper.scrape_products(
            keyword=sanitized_keyword,
            sort_by_price=validated_sort,
            page=validated_page
        )
        
        if not result.success:
            return JsonResponse({
                'success': False,
                'error': result.error_message,
                'saved': 0,
                'updated': 0,
                'inserted': 0,
                'anomalies': []
            }, status=500)
        
        products_data = [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url,
                'unit': product.unit
            }
            for product in result.products
        ]
        
        if not products_data:
            return JsonResponse({
                'success': True,
                'message': 'No products found to save',
                'saved': 0,
                'updated': 0,
                'inserted': 0,
                'anomalies': []
            })
        
        for idx, product in enumerate(products_data):
            is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(product)
            if not is_valid:
                return JsonResponse({
                    'error': f'Product {idx}: {error_msg}'
                }, status=400)
        
        db_service = GemilangDatabaseService()
        
        if validated_update:
            save_result = db_service.save_with_price_update(products_data)
            
            if not save_result.get('success', False):
                return JsonResponse({
                    'success': False,
                    'error': save_result.get('error', 'Failed to save products'),
                    'saved': 0,
                    'updated': 0,
                    'inserted': 0,
                    'anomalies': []
                }, status=500)
            
            return JsonResponse({
                'success': True,
                'message': f"Updated {save_result['updated']} products, inserted {save_result['inserted']} new products",
                'saved': save_result['updated'] + save_result['inserted'],
                'updated': save_result['updated'],
                'inserted': save_result['inserted'],
                'anomalies': save_result.get('anomalies', []),
                'anomaly_count': len(save_result.get('anomalies', []))
            })
        else:
            save_result = db_service.save(products_data)
            
            if isinstance(save_result, tuple):
                save_success, error_msg = save_result
            else:
                save_success = save_result
                error_msg = 'Failed to save products to database'
            
            if save_success:
                return JsonResponse({
                    'success': True,
                    'message': f"Successfully saved {len(products_data)} products",
                    'saved': len(products_data),
                    'updated': 0,
                    'inserted': len(products_data),
                    'anomalies': []
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': error_msg,
                    'saved': 0,
                    'updated': 0,
                    'inserted': 0,
                    'anomalies': []
                }, status=500)
        
    except Exception as e:
        logger.error(f"Unexpected error in scrape_and_save: {type(e).__name__}")
        return JsonResponse({
            'error': 'Internal server error occurred'
        }, status=500)
