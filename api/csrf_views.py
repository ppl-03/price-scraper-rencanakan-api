"""
CSRF token endpoint for API clients.
This allows API clients to obtain a CSRF token before making POST requests.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Get a CSRF token for API requests.
    
    Usage:
        1. Call GET /api/csrf-token/ to get the token
        2. Include the token in subsequent POST requests via:
           - Header: X-CSRFToken: <token>
           - OR Cookie: csrftoken=<token>
    
    Returns:
        JSON response with the CSRF token
    """
    token = get_token(request)
    return JsonResponse({
        'csrfToken': token,
        'message': 'Include this token in X-CSRFToken header for POST requests'
    })
