"""
Custom authentication decorator for API endpoints.
This allows API token authentication to bypass CSRF checks in a secure way.
"""
from functools import wraps
from django.http import JsonResponse
from .logging_utils import get_gemilang_logger

logger = get_gemilang_logger("decorators")


def api_token_required(view_func):
    """
    Decorator that validates API token and exempts the view from CSRF only if a valid token is present.
    This is more secure than blanket csrf_exempt as it requires authentication.
    
    Usage:
        @api_token_required
        @require_http_methods(["POST"])
        def my_api_view(request):
            # Your view code
            pass
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Import here to avoid circular dependency
        from .views import _validate_api_token
        
        is_valid, error_message = _validate_api_token(request)
        if not is_valid:
            logger.warning("API token validation failed: %s", error_message)
            return JsonResponse({'error': error_message}, status=401)
        
        # Token is valid, proceed with the view
        return view_func(request, *args, **kwargs)
    
    return wrapped_view
