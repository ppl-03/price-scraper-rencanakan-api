import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .models import User
from .services import TokenService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def login(request):
    """Authenticate user and return API token"""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = payload.get('email')
    password = payload.get('password')

    # Basic validation: required fields and email format
    if not email or not password:
        return JsonResponse({'error': 'Missing credentials'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        # Keep error generic to avoid leaking account existence
        return JsonResponse({'error': 'Invalid credentials'}, status=401)

    user = authenticate(request, email=email, password=password)
    if user is None:
        # Generic error for security
        return JsonResponse({'error': 'Invalid credentials'}, status=401)

    if not user.is_email_verified:
        # Resend verification and block login
        try:
            user.send_verification_email()
        except Exception:
            logger.exception('Failed resending verification')
        return JsonResponse({'error': 'Email not verified. Verification resent.'}, status=403)

    # Update last activity
    user.update_last_activity(request.META.get('REMOTE_ADDR'))

    # Create API token (sanctum-like)
    token = user.create_api_token(name='login')

    # Build response context
    context = {
        'token': token,
        'user': {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'hashid': user.hashid,
        },
        'company': None
    }

    if user.company:
        context['company'] = {
            'name': user.company.name,
            'slug': user.company.slug,
        }

    return JsonResponse(context)


@require_GET
def verify_token(request):
    """Validate bearer token and return user context"""
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return JsonResponse({'error': 'Missing token'}, status=401)
    token = auth.split(' ', 1)[1]

    user = User.objects.filter(current_access_token=token).first()
    if not user:
        # Token might be in api_tokens list
        user = None
        for u in User.objects.all():
            if u.validate_api_token(token):
                user = u
                break

    if not user:
        return JsonResponse({'error': 'Invalid or expired token'}, status=401)

    # Return minimal user context and permissions (placeholder)
    return JsonResponse({
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'company': {'name': user.company.name, 'slug': user.company.slug} if user.company else None,
    })


@csrf_exempt
@require_POST
def logout(request):
    """Revoke current access token"""
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return JsonResponse({'ok': True})
    token = auth.split(' ', 1)[1]

    # Find user and revoke token
    for u in User.objects.all():
        if u.current_access_token == token:
            u.revoke_api_token(token)
            return JsonResponse({'ok': True})

    return JsonResponse({'ok': True})
