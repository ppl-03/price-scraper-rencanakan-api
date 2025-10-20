import logging
from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings

from .models import User

logger = logging.getLogger(__name__)


def confirm_email(request, token):
    """Confirm email flow:
    - Decrypt/validate token
    - Mark user as verified
    - Redirect to configured frontend callback
    """
    # Find user by token
    user = User.objects.filter(verification_token=token).first()
    if not user:
        # Redirect to failure page or show a simple message
        failure_url = getattr(settings, 'FRONTEND_VERIFY_FAIL', '/verify-fail')
        return redirect(failure_url)

    if user.is_email_verified:
        success_url = getattr(settings, 'FRONTEND_VERIFY_SUCCESS', '/verify-success')
        return redirect(success_url)

    try:
        user.verify_email(token)
    except Exception:
        logger.exception('Error verifying email for token: %s', token)
        return redirect(getattr(settings, 'FRONTEND_VERIFY_FAIL', '/verify-fail'))

    return redirect(getattr(settings, 'FRONTEND_VERIFY_SUCCESS', '/verify-success'))
