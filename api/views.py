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

def get_scraper_info_and_url(cleaned_data):
    """
    Helper function to get scraper info and generate URL
    Returns: (scraper_info, scraping_url)
    """
    try:
        scraper = get_scraper_factory(cleaned_data['vendor'])
        scraper_info = {
            'class_name': scraper.__class__.__name__,
            'available': True
        }
        
        # Generate URL
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
            
        return scraper_info, scraping_url
        
    except ValueError as e:
        scraper_info = {
            'available': False,
            'error': str(e)
        }
        return scraper_info, None

def validate_and_process_request(data, log_prefix=""):
    """
    Helper function to validate request data and get scraper info
    Returns: (validation_result, cleaned_data, scraper_info, scraping_url)
    """
    # Validate input using validation system
    validation_result = InputValidator.validate_scraping_request(data)
    
    if not validation_result.is_valid:
        return validation_result, None, None, None
    
    # Get cleaned data
    cleaned_data = validation_result.cleaned_data
    
    # Log the validated request
    logger.info(f"{log_prefix}validation successful: {cleaned_data}")
    
    # Get scraper info and URL
    scraper_info, scraping_url = get_scraper_info_and_url(cleaned_data)
    
    return validation_result, cleaned_data, scraper_info, scraping_url

def create_validation_success_response(cleaned_data, scraper_info, scraping_url, message, note):
    """
    Helper function to create success response for validation endpoints
    """
    return {
        'success': True,
        'message': message,
        'validated_data': {
            'keyword': cleaned_data['keyword'],
            'vendor': cleaned_data['vendor'],
            'page': cleaned_data['page'],
            'sort_by_price': cleaned_data['sort_by_price']
        },
        'scraper_info': scraper_info,
        'would_scrape_url': scraping_url,
        'note': note
    }

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
        
        # Validate and process request
        validation_result, cleaned_data, scraper_info, scraping_url = validate_and_process_request(
            data, "GET input "
        )
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': 'Input validation failed',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Create success response
        response_data = create_validation_success_response(
            cleaned_data, scraper_info, scraping_url,
            'Input validation successful - parameters valid for scraping',
            'This is input validation only - no actual scraping performed'
        )
        
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
        
        # Validate and process request
        validation_result, cleaned_data, scraper_info, scraping_url = validate_and_process_request(
            data, "JSON input "
        )
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': 'Input validation failed',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Create success response
        response_data = create_validation_success_response(
            cleaned_data, scraper_info, scraping_url,
            'JSON input validation successful - parameters valid for scraping',
            'This is JSON input validation only - no actual scraping performed'
        )
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=500)


@require_http_methods(["POST"])
def validate_scraper_input_api(request):
    """
    Secure API endpoint for external services with CSRF protection
    
    For API clients, you have two options:
    1. Include X-CSRFToken header with token obtained from /api/csrf-token/ endpoint
    2. Use Django's built-in API token authentication
    
    This endpoint provides additional security checks for API access patterns.
    For web applications, use validate_scraper_input_json endpoint instead.
    """
    try:
        # Additional security: Validate API access patterns
        content_type = request.content_type
        if not content_type or 'application/json' not in content_type:
            return JsonResponse({
                'success': False,
                'error': 'Content-Type must be application/json for API access',
                'code': 'INVALID_CONTENT_TYPE',
                'help': 'Set Content-Type header to application/json'
            }, status=400)
        
        # Check for proper API headers (additional security layer)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if not user_agent or 'browser' in user_agent.lower():
            logger.warning(f"Potential browser access to API endpoint from {request.META.get('REMOTE_ADDR', 'unknown')}")
        
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format',
                'code': 'INVALID_JSON'
            }, status=400)
        
        # Validate and process request with enhanced logging
        validation_result, cleaned_data, scraper_info, scraping_url = validate_and_process_request(
            data, f"Secure API validation from {request.META.get('REMOTE_ADDR', 'unknown')}: "
        )
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': 'Input validation failed',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Create success response
        response_data = create_validation_success_response(
            cleaned_data, scraper_info, scraping_url,
            'Secure API validation successful - parameters valid for scraping',
            'This is secure API validation only - no actual scraping performed'
        )
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in validate_scraper_input_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def validate_scraper_input_legacy_api(request):
    try:
        # Enhanced security logging
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
        
        logger.warning(f"CSRF-exempt API access from IP: {client_ip}, User-Agent: {user_agent}")
        
        # Strict Content-Type validation
        content_type = request.content_type
        if not content_type or 'application/json' not in content_type:
            logger.warning(f"Invalid Content-Type '{content_type}' from {client_ip}")
            return JsonResponse({
                'success': False,
                'error': 'Content-Type must be application/json for API access',
                'code': 'INVALID_CONTENT_TYPE',
                'help': 'Set Content-Type header to application/json'
            }, status=400)
        
        # Validate User-Agent (basic bot/browser detection)
        suspicious_agents = ['curl', 'wget', 'python-requests', 'postman']
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            logger.info(f"Development/testing tool detected: {user_agent} from {client_ip}")
        
        # Block obvious browser requests
        browser_indicators = ['mozilla', 'chrome', 'safari', 'edge', 'firefox']
        if any(browser in user_agent.lower() for browser in browser_indicators):
            logger.warning(f"Browser request to CSRF-exempt endpoint from {client_ip}")
            return JsonResponse({
                'success': False,
                'error': 'Browser requests not allowed on this endpoint',
                'code': 'BROWSER_REQUEST_BLOCKED',
                'help': 'Use /api/validate-input-json/ for browser requests'
            }, status=403)
        
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format',
                'code': 'INVALID_JSON'
            }, status=400)
        
        # Enhanced request validation and logging
        validation_result, cleaned_data, scraper_info, scraping_url = validate_and_process_request(
            data, f"LEGACY API (CSRF-exempt) from {client_ip}: "
        )
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': 'Input validation failed',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Create success response with security notice
        response_data = create_validation_success_response(
            cleaned_data, scraper_info, scraping_url,
            'Legacy API validation successful - parameters valid for scraping',
            'WARNING: This endpoint bypasses CSRF protection. Consider migrating to /api/validate-input-api/'
        )
        
        # Add security headers to response
        response = JsonResponse(response_data)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        return response
        
    except Exception as e:
        logger.error(f"Error in validate_scraper_input_legacy_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=500)


@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Endpoint to obtain CSRF token for API clients
    
    Usage:
    1. GET /api/csrf-token/ to obtain token
    2. Include X-CSRFToken header in subsequent POST requests
    """
    from django.middleware.csrf import get_token
    
    csrf_token = get_token(request)
    return JsonResponse({
        'success': True,
        'csrf_token': csrf_token,
        'usage': 'Include this token in X-CSRFToken header for POST requests',
        'example': {
            'header': 'X-CSRFToken',
            'value': csrf_token
        }
    })


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
        
        # Validate and process request
        validation_result, cleaned_data, scraper_info, scraping_url = validate_and_process_request(
            data, f"Vendor {vendor} "
        )
        
        if not validation_result.is_valid:
            errors_dict = get_validation_errors_dict(validation_result)
            return JsonResponse({
                'success': False,
                'error': f'Input validation failed for {vendor}',
                'validation_errors': errors_dict,
                'code': 'VALIDATION_ERROR'
            }, status=400)
        
        # Create vendor-specific success response
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
            'scraper_info': scraper_info,
            'would_scrape_url': scraping_url,
            'note': f'Validation successful - {vendor} ready for scraping'
        })
            
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