import logging
import json
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.models import Group

from .models import User, Company

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def register(request):
    """Handle user registration.

    Expected JSON body: {email, password, first_name, last_name, company_slug (optional)}
    Behavior:
    - Validate required fields
    - If an unverified user exists with same email, delete it
    - If verified user exists, return error
    - Create user, assign "owner" group, send verification email
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    email = payload.get('email')
    password = payload.get('password')
    first_name = payload.get('first_name')
    last_name = payload.get('last_name')
    company_slug = payload.get('company_slug')

    if not all([email, password, first_name, last_name]):
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    existing = User.objects.filter(email=email).first()
    if existing:
        if not existing.is_email_verified:
            # Remove unverified account and allow re-registration
            existing.delete()
        else:
            return JsonResponse({'error': 'Email already registered'}, status=400)

    # Optionally link to a company
    company = None
    if company_slug:
        company = Company.objects.filter(slug=company_slug).first()

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        company=company,
    )

    # Assign default 'owner' role via Group
    try:
        owner_group, _ = Group.objects.get_or_create(name='owner')
        user.groups.add(owner_group)
        user.save()
    except Exception:
        logger.exception('Failed to assign owner group')

    # Send verification email but do not fail registration if email sending fails
    try:
        user.send_verification_email()
    except Exception:
        logger.exception('Failed to send verification email for %s', email)

    return JsonResponse({'ok': True, 'email': user.email, 'hashid': user.hashid})
