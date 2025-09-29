from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .factory import create_gemilang_scraper
from api.views_utils import validate_scraping_request, format_scraping_response, handle_scraping_exception


@require_http_methods(["GET"])
def scrape_products(request):
    try:
        # Validate request parameters
        keyword, sort_by_price, page, error_response = validate_scraping_request(request)
        if error_response:
            return error_response
        
        # Perform scraping
        scraper = create_gemilang_scraper()
        result = scraper.scrape_products(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        # Format and return response
        response_data = format_scraping_response(result)
        return JsonResponse(response_data)
        
    except Exception as e:
        return handle_scraping_exception(e, "Gemilang scraper")