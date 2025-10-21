import functools
from typing import Callable

from django.http import JsonResponse, HttpResponseForbidden


def _is_api_request(request) -> bool:
    """Heuristic to decide if request is an API call.

    Checks common signals: path prefix `/api/`, Accept header containing JSON,
    or content type being JSON. This is intentionally permissive so it works
    for typical JSON API endpoints.
    """
    accept = request.META.get('HTTP_ACCEPT', '') or ''
    content_type = getattr(request, 'content_type', '') or ''
    path = getattr(request, 'path', '') or ''

    if path.startswith('/api/'):
        return True
    if 'application/json' in accept.lower():
        return True
    if 'application/json' in content_type.lower():
        return True
    return False


# --- Decorators to mark views ---
def require_auth(view_func: Callable) -> Callable:
    """Decorator to mark a view as requiring authentication."""

    @functools.wraps(view_func)
    def _wrapped(*args, **kwargs):
        return view_func(*args, **kwargs)

    setattr(_wrapped, 'require_auth', True)
    return _wrapped


def ensure_user_dont_have_company(view_func: Callable) -> Callable:
    """Mark a view to prevent users who already belong to a company from
    calling it (e.g. company creation endpoints).
    """

    @functools.wraps(view_func)
    def _wrapped(*args, **kwargs):
        return view_func(*args, **kwargs)

    setattr(_wrapped, 'ensure_user_dont_have_company', True)
    return _wrapped


def ensure_user_have_company(view_func: Callable) -> Callable:
    """Mark a view that requires the user to belong to a company.
    """

    @functools.wraps(view_func)
    def _wrapped(*args, **kwargs):
        return view_func(*args, **kwargs)

    setattr(_wrapped, 'ensure_user_have_company', True)
    return _wrapped


def ensure_demo_eligibility(view_func: Callable) -> Callable:

    @functools.wraps(view_func)
    def _wrapped(*args, **kwargs):
        return view_func(*args, **kwargs)

    setattr(_wrapped, 'ensure_demo_eligibility', True)
    return _wrapped


# --- Middleware classes ---
class AuthenticateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(view_func, 'require_auth', False):
            return None

        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            return None

        if _is_api_request(request):
            return JsonResponse({
                'status': 'fail',
                'message': 'You must authenticated first before accessing this route!'
            }, status=401)

        return HttpResponseForbidden('You are not authenticated yet!')


class CompanyMiddleware:
    """Middleware for company related checks.

    It looks for `ensure_user_dont_have_company` and `ensure_user_have_company`
    attributes on the view and enforces the respective rules.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, 'user', None)

        # Prevent users who already belong to a company from calling certain
        # endpoints (e.g. create company)
        if getattr(view_func, 'ensure_user_dont_have_company', False):
            if user and getattr(user, 'is_authenticated', False) and getattr(user, 'company', None):
                if _is_api_request(request):
                    return JsonResponse({'status': 'fail', 'message': 'You already belong to a company'}, status=403)
                return HttpResponseForbidden('You already belong to a company')

        # Ensure user belongs to a company for certain endpoints
        if getattr(view_func, 'ensure_user_have_company', False):
            if not (user and getattr(user, 'is_authenticated', False) and getattr(user, 'company', None)):
                if _is_api_request(request):
                    return JsonResponse({'status': 'fail', 'message': 'You must belong to a company to access this resource'}, status=403)
                return HttpResponseForbidden('You must belong to a company')

        return None


class EnsureDemoEligibilityMiddleware:
    """Checks a user's demo quota before allowing access to demo features.

    Usage: mark views with `@ensure_demo_eligibility`. The middleware will look
    for an integer attribute `demo_quota` on `request.user`. If present and
    <= 0 the request is denied. If absent, the middleware assumes eligibility.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(view_func, 'ensure_demo_eligibility', False):
            return None

        user = getattr(request, 'user', None)
        # If user not authenticated, let AuthenticateMiddleware handle it first
        if not (user and getattr(user, 'is_authenticated', False)):
            return None

        quota = getattr(user, 'demo_quota', None)
        if quota is None:
            # No quota field -> assume eligible
            return None

        try:
            if int(quota) <= 0:
                if _is_api_request(request):
                    return JsonResponse({'status': 'fail', 'message': 'Demo quota exceeded'}, status=403)
                return HttpResponseForbidden('Demo quota exceeded')
        except Exception:
            # If quota is malformed, be conservative and allow access; alternately
            # you can deny, but allowing avoids accidental lockout.
            return None

        return None
