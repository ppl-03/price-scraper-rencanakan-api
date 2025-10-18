from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_tokopedia_scraper


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        # Get and validate query parameter
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
        
        # Perform scraping
        scraper = create_tokopedia_scraper()
        result = scraper.scrape_products(
            keyword=query,
            sort_by_price=sort_by_price,
            page=page
        )
        
        # Format and return response
        return JsonResponse({
            'success': result.success,
            'products': [
                {
                    'name': product.name,
                    'price': product.price,
                    'url': product.url
                }
                for product in result.products
            ],
            'url': result.url,
            'error_message': result.error_message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'products': [],
            'error_message': f"Tokopedia scraper error: {str(e)}",
            'url': ''
        }, status=500)


@require_http_methods(["GET"])
def scrape_products_with_filters(request):
    try:
        # Get and validate query parameter
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
        
        # Parse additional filter parameters
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        location = request.GET.get('location')
        
        # Convert price parameters to integers if provided
        if min_price is not None:
            try:
                min_price = int(min_price)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'products': [],
                    'error_message': 'min_price must be a valid integer',
                    'url': ''
                }, status=400)
        
        if max_price is not None:
            try:
                max_price = int(max_price)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'products': [],
                    'error_message': 'max_price must be a valid integer',
                    'url': ''
                }, status=400)
        
        # Perform scraping with filters
        scraper = create_tokopedia_scraper()
        result = scraper.scrape_products_with_filters(
            keyword=query,
            sort_by_price=sort_by_price,
            page=page,
            min_price=min_price,
            max_price=max_price,
            location=location
        )
        
        # Format and return response
        return JsonResponse({
            'success': result.success,
            'products': [
                {
                    'name': product.name,
                    'price': product.price,
                    'url': product.url
                }
                for product in result.products
            ],
            'url': result.url,
            'error_message': result.error_message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'products': [],
            'error_message': f"Tokopedia scraper with filters error: {str(e)}",
            'url': ''
        }, status=500)