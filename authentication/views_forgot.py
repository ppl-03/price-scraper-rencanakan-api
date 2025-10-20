import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import User
from django.contrib.auth.hashers import make_password
from .services import TokenService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def request_password_reset(request):
    """Generate a one-time reset token and email it to the user.

    Token is stored in the user's `verification_token` field prefixed with
    'reset:' to avoid colliding with normal email verification tokens.
    This approach avoids schema migrations while keeping tokens single-use.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = payload.get('email')
    if not email:
        return JsonResponse({'error': 'Missing email'}, status=400)

    user = User.objects.filter(email__iexact=email).first()
    # Always return success to avoid leaking whether an account exists
    if not user:
        return JsonResponse({'ok': True})

    try:
        token = TokenService.generate(48)
        user.verification_token = f"reset:{token}"
        # Persist token on user; single-use semantics ensured by clearing on reset
        user.save()

        # Send reset email (non-blocking)
        reset_path = getattr(settings, 'FRONTEND_RESET_PATH', f'/password/reset?token={token}')
        subject = 'Password reset request'
        message = f'Use this link to reset your password: {reset_path}&token={token}'
        send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@yoursite.com'), [user.email])
    except Exception:
        logger.exception('Failed creating or emailing reset token')

    return JsonResponse({'ok': True})


@require_GET
def verify_reset_token(request, token: str):
    """Verify a reset token exists (used by frontend to check validity)."""
    # Basic validation of token format
    if not token or not isinstance(token, str):
        return JsonResponse({'error': 'Invalid token'}, status=404)

    lookup = f"reset:{token}"
    user = User.objects.filter(verification_token=lookup).first()
    if not user:
        return JsonResponse({'error': 'Invalid or expired token'}, status=404)
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def perform_password_reset(request):
    """Consume the reset token and update the user's password.

    Body: { "token": "...", "password": "..." }
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Accept both 'token' and 'reset_password_token' for compatibility
    token = payload.get('token') or payload.get('reset_password_token')
    password = payload.get('password')
    if not token or not password:
        return JsonResponse({'error': 'Missing token or password'}, status=400)

    lookup = f"reset:{token}"
    user = User.objects.filter(verification_token=lookup).first()
    if not user:
        return JsonResponse({'error': 'Invalid or expired token'}, status=404)

    try:
        # Use queryset update to avoid triggering User.save() logic that
        # automatically (re)generates verification tokens when empty.
        hashed = make_password(password)
        User.objects.filter(pk=user.pk).update(password=hashed, verification_token=None)
        # Refresh object and revoke tokens
        # Clear API tokens with a DB-level update to avoid triggering User.save()
        try:
            User.objects.filter(pk=user.pk).update(api_tokens=[], current_access_token=None)
        except Exception:
            logger.exception('Failed revoking API tokens after password reset')
    except Exception:
        logger.exception('Failed resetting password')
        return JsonResponse({'error': 'Failed to reset password'}, status=500)

    return JsonResponse({'ok': True})
