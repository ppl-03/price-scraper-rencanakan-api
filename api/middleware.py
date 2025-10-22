class DisableCSRFForAPIMiddleware:
    """
    Middleware to disable CSRF protection for API endpoints.
    This allows token-based authentication for /api/* paths.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
