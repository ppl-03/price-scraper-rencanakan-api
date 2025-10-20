import logging
import json
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

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
    phone = payload.get('phone')
    job = payload.get('job')
    company_slug = payload.get('company_slug')

    # Validate required fields
    if not all([email, password, first_name, last_name, phone, job]):
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    # Email format
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'error': 'Invalid email'}, status=400)

    # Password strength (minimal)
    if not isinstance(password, str) or len(password) < 8:
        return JsonResponse({'error': 'Invalid password'}, status=400)

    # Unique constraints: email and phone
    if User.objects.filter(email__iexact=email).exists():
        existing = User.objects.filter(email__iexact=email).first()
        if existing.is_email_verified:
            return JsonResponse({'error': 'Email already registered'}, status=400)
        # otherwise unverified: allow re-registration (existing delete handled below)

    if User.objects.filter(phone=phone).exists():
        return JsonResponse({'error': 'Phone already registered'}, status=400)

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
