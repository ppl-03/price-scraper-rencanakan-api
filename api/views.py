from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
import json
import logging
from .interfaces import IPriceScraper, ScrapingResult
from .depobangunan.factory import create_depo_scraper
from .gemilang.factory import create_gemilang_scraper
from .juragan_material.factory import create_juraganmaterial_scraper
from .mitra10.factory import create_mitra10_scraper

from .validation import (
    InputValidator, 
    validate_scraping_params, 
    get_validation_errors_dict,
    ValidationResult
)

# Configure logging
logger = logging.getLogger(__name__)

def get_scraper_factory(vendor: str) -> IPriceScraper:
    """
    Factory function to get the appropriate scraper based on vendor
    """
    scrapers = {
        'depobangunan': create_depo_scraper,
        'gemilang': create_gemilang_scraper,
        'juragan_material': create_juraganmaterial_scraper,
        'mitra10': create_mitra10_scraper,
    }
    
    if vendor not in scrapers:
        raise ValueError(f"Unsupported vendor: {vendor}")
    
    return scrapers[vendor]()

@require_http_methods(["GET"])
def health_check(request):
    """
    API health check endpoint
    """
    return JsonResponse({
        'status': 'healthy',
        'api_version': '1.0',
        'validation_enabled': True
    })


@require_http_methods(["GET"])
def validate_scraper_input(request):
    """
    GET endpoint for scraper input validation only 
    """
    try:
        # Get request data from query parameters
        data = {
            'keyword': request.GET.get('keyword', ''),
            'vendor': request.GET.get('vendor', ''),
            'page': request.GET.get('page', 0),
            'sort_by_price': request.GET.get('sort_by_price', 'true')
        }
        
        # Validate input using validation system
        validation_result = InputValidator.validate_scraping_request(data)
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': 'Input validation failed',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Get cleaned data
        cleaned_data = validation_result.cleaned_data
        
        # Log the validated request
        logger.info(f"Input validation successful: {cleaned_data}")
        
        # Cek apakah scraper untuk vendor tersebut tersedia
        try:
            scraper = get_scraper_factory(cleaned_data['vendor'])
            scraper_available = True
            scraper_info = {
                'class_name': scraper.__class__.__name__,
                'available': True
            }
        except ValueError as e:
            scraper_available = False
            scraper_info = {
                'available': False,
                'error': str(e)
            }
        
        if scraper_available:
            try:
                url_builder = scraper._url_builder if hasattr(scraper, '_url_builder') else None
                if url_builder:
                    scraping_url = url_builder.build_search_url(
                        keyword=cleaned_data['keyword'],
                        sort_by_price=cleaned_data['sort_by_price'], 
                        page=cleaned_data['page']
                    )
                else:
                    scraping_url = f"URL will be generated for vendor {cleaned_data['vendor']}"
            except Exception as e:
                scraping_url = f"Error generating URL: {str(e)}"
        else:
            scraping_url = None
        
        # Success response with validation information
        response_data = {
            'success': True,
            'message': 'Input validation successful - parameters valid for scraping',
            'validated_data': {
                'keyword': cleaned_data['keyword'],
                'vendor': cleaned_data['vendor'],
                'page': cleaned_data['page'],
                'sort_by_price': cleaned_data['sort_by_price']
            },
            'scraper_info': scraper_info,
            'would_scrape_url': scraping_url,
            'note': 'This is input validation only - no actual scraping performed'
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in validate_scraper_input: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=500)


@require_http_methods(["POST"])
def validate_scraper_input_json(request):
    """
    POST endpoint for JSON-based scraper input validation
    """
    try:
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format',
                'code': 'INVALID_JSON'
            }, status=400)
        
        # Validate input using validation system
        validation_result = InputValidator.validate_scraping_request(data)
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': 'Input validation failed',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Get cleaned data
        cleaned_data = validation_result.cleaned_data
        
        # Log the validated request
        logger.info(f"JSON input validation successful: {cleaned_data}")
        
        # Check scraper availability
        try:
            scraper = get_scraper_factory(cleaned_data['vendor'])
            scraper_available = True
            scraper_info = {
                'class_name': scraper.__class__.__name__,
                'available': True
            }
        except ValueError as e:
            scraper_available = False
            scraper_info = {
                'available': False,
                'error': str(e)
            }
     
        if scraper_available:
            try:
                url_builder = scraper._url_builder if hasattr(scraper, '_url_builder') else None
                if url_builder:
                    scraping_url = url_builder.build_search_url(
                        keyword=cleaned_data['keyword'],
                        sort_by_price=cleaned_data['sort_by_price'], 
                        page=cleaned_data['page']
                    )
                else:
                    scraping_url = f"URL will be generated for vendor {cleaned_data['vendor']}"
            except Exception as e:
                scraping_url = f"Error generating URL: {str(e)}"
        else:
            scraping_url = None
        
        # Success response
        response_data = {
            'success': True,
            'message': 'JSON input validation successful - parameters valid for scraping',
            'validated_data': {
                'keyword': cleaned_data['keyword'],
                'vendor': cleaned_data['vendor'],
                'page': cleaned_data['page'],
                'sort_by_price': cleaned_data['sort_by_price']
            },
            'scraper_info': scraper_info,
            'would_scrape_url': scraping_url,
            'note': 'This is JSON input validation only - no actual scraping performed'
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def validate_scraper_input_api(request):
    """
    API endpoint for external services - CSRF exempt but with additional security
    This endpoint is specifically for API clients that cannot handle CSRF tokens
    Use validate_scraper_input_json for web applications
    """
    try:
        # Additional security: Check for API usage patterns
        content_type = request.content_type
        if not content_type or 'application/json' not in content_type:
            return JsonResponse({
                'success': False,
                'error': 'Content-Type must be application/json for API access',
                'code': 'INVALID_CONTENT_TYPE'
            }, status=400)
        
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format',
                'code': 'INVALID_JSON'
            }, status=400)
        
        # Validate input using validation system
        validation_result = InputValidator.validate_scraping_request(data)
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': 'Input validation failed',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Get cleaned data
        cleaned_data = validation_result.cleaned_data
        
        # Log the validated request (for security monitoring)
        logger.info(f"API validation successful from {request.META.get('REMOTE_ADDR', 'unknown')}: {cleaned_data}")
        
        # Check scraper availability
        try:
            scraper = get_scraper_factory(cleaned_data['vendor'])
            scraper_available = True
            scraper_info = {
                'class_name': scraper.__class__.__name__,
                'available': True
            }
        except ValueError as e:
            scraper_available = False
            scraper_info = {
                'available': False,
                'error': str(e)
            }
        
        # Build URL for scraping (without making request)
        if scraper_available:
            try:
                url_builder = scraper._url_builder if hasattr(scraper, '_url_builder') else None
                if url_builder:
                    scraping_url = url_builder.build_search_url(
                        keyword=cleaned_data['keyword'],
                        sort_by_price=cleaned_data['sort_by_price'], 
                        page=cleaned_data['page']
                    )
                else:
                    scraping_url = f"URL will be generated for vendor {cleaned_data['vendor']}"
            except Exception as e:
                scraping_url = f"Error generating URL: {str(e)}"
        else:
            scraping_url = None
        
        # Success response
        response_data = {
            'success': True,
            'message': 'API validation successful - parameters valid for scraping',
            'validated_data': {
                'keyword': cleaned_data['keyword'],
                'vendor': cleaned_data['vendor'],
                'page': cleaned_data['page'],
                'sort_by_price': cleaned_data['sort_by_price']
            },
            'scraper_info': scraper_info,
            'would_scrape_url': scraping_url,
            'note': 'This is API validation only - no actual scraping performed'
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in validate_scraper_input_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=500)


@require_http_methods(["POST"])
def validate_scraping_params_endpoint(request):
    """
    Endpoint to validate scraping parameters without actually scraping
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON format',
            'code': 'INVALID_JSON'
        }, status=400)
    
    validation_result = InputValidator.validate_scraping_request(data)
    
    if validation_result.is_valid:
        return JsonResponse({
            'success': True,
            'message': 'All parameters are valid',
            'cleaned_data': validation_result.cleaned_data
        })
    else:
        errors_dict = get_validation_errors_dict(validation_result)
        return JsonResponse({
            'success': False,
            'message': 'Validation failed',
            'validation_errors': errors_dict
        }, status=400)


@require_http_methods(["GET"])
def get_validation_rules(request):
    """
    Endpoint to get validation rules and constraints
    """
    rules = {
        'keyword': {
            'required': True,
            'min_length': InputValidator.MIN_KEYWORD_LENGTH,
            'max_length': InputValidator.MAX_KEYWORD_LENGTH,
            'forbidden_patterns': [
                'HTML/XML tags',
                'JavaScript code',
                'SQL injection attempts',
                'Event handlers'
            ]
        },
        'vendor': {
            'required': True,
            'allowed_values': InputValidator.ALLOWED_VENDORS
        },
        'page': {
            'required': False,
            'type': 'integer',
            'min_value': InputValidator.MIN_PAGE_NUMBER,
            'max_value': InputValidator.MAX_PAGE_NUMBER,
            'default': 0
        },
        'sort_by_price': {
            'required': False,
            'type': 'boolean',
            'default': True
        }
    }
    
    return JsonResponse({
        'success': True,
        'validation_rules': rules
    })


@require_http_methods(["GET"])
def get_supported_vendors(request):
    """
    Endpoint to get list of supported vendors with their availability status
    """
    vendors_status = {}
    
    for vendor in InputValidator.ALLOWED_VENDORS:
        try:
            scraper = get_scraper_factory(vendor)
            vendors_status[vendor] = {
                'available': True,
                'scraper_type': scraper.__class__.__name__
            }
        except Exception as e:
            vendors_status[vendor] = {
                'available': False,
                'error': str(e)
            }
    
    return JsonResponse({
        'success': True,
        'supported_vendors': InputValidator.ALLOWED_VENDORS,
        'total_vendors': len(InputValidator.ALLOWED_VENDORS),
        'vendors_status': vendors_status
    })


@require_http_methods(["POST"])
def validate_vendor_input(request, vendor):
    """
    Endpoint for input validation for specific vendor
    """
    try:
        data = json.loads(request.body)
        
        # Add vendor from URL to data
        data['vendor'] = vendor
        
        # Basic validation for vendor
        if vendor not in InputValidator.ALLOWED_VENDORS:
            return JsonResponse({
                'success': False,
                'error': f'Vendor not supported. Available vendors: {InputValidator.ALLOWED_VENDORS}',
                'code': 'INVALID_VENDOR'
            }, status=400)
        
        # Validate menggunakan validation system
        validation_result = InputValidator.validate_scraping_request(data)
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': f'Input validation failed for {vendor}',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Get cleaned data
        cleaned_data = validation_result.cleaned_data
        
        # Test scraper availability
        try:
            scraper = get_scraper_factory(vendor)
            
            # Generate URL yang akan di-scrape (tanpa melakukan request)
            url_builder = getattr(scraper, '_url_builder', None)
            if url_builder:
                would_scrape_url = url_builder.build_search_url(
                    keyword=cleaned_data['keyword'],
                    sort_by_price=cleaned_data['sort_by_price'],
                    page=cleaned_data['page']
                )
            else:
                would_scrape_url = f"URL for {vendor} will be generated during scraping"
                
            return JsonResponse({
                'success': True,
                'vendor': vendor,
                'message': f'Input validation successful for {vendor}',
                'validated_input': {
                    'keyword': cleaned_data['keyword'],
                    'vendor': cleaned_data['vendor'],
                    'page': cleaned_data['page'],
                    'sort_by_price': cleaned_data['sort_by_price']
                },
                'scraper_info': {
                    'class_name': scraper.__class__.__name__,
                    'available': True
                },
                'would_scrape_url': would_scrape_url,
                'note': f'Validation successful - {vendor} ready for scraping'
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'vendor': vendor,
                'error': str(e),
                'code': 'SCRAPER_UNAVAILABLE'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON format',
            'code': 'INVALID_JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'code': 'INTERNAL_ERROR'
        }, status=500)