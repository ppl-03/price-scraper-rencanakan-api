from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

import hashlib
import secrets
import string
from typing import Optional, List, Dict, Any


class HashidService:
    """Encapsulates hashid generation and lookup logic."""

    @staticmethod
    def generate(pk: int) -> Optional[str]:
        if not pk:
            return None
        secret = getattr(settings, 'SECRET_KEY', None)
        raw_string = f"{pk}-{secret}"
        return hashlib.sha256(raw_string.encode()).hexdigest()[:16]

    @staticmethod
    def find_by_hashid(queryset, hashid: str):
        for obj in queryset:
            if HashidService.generate(obj.pk) == hashid:
                return obj
        return None


class TokenService:
    """Encapsulates API token creation, validation and revocation."""

    @staticmethod
    def generate(length: int = 32) -> str:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def create_api_token(user, name: str = "default", expires_at=None) -> str:
        token = TokenService.generate(64)
        token_data = {
            'name': name,
            'token': token,
            'created_at': timezone.now().isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'last_used_at': None
        }

        if not isinstance(user.api_tokens, list):
            user.api_tokens = []

        user.api_tokens.append(token_data)
        user.current_access_token = token
        user.save()
        return token

    @staticmethod
    def revoke_api_token(user, token: str) -> None:
        if isinstance(user.api_tokens, list):
            user.api_tokens = [t for t in user.api_tokens if t.get('token') != token]
            if user.current_access_token == token:
                user.current_access_token = None
            user.save()

    @staticmethod
    def revoke_all_tokens(user) -> None:
        user.api_tokens = []
        user.current_access_token = None
        user.save()

    @staticmethod
    def validate_api_token(user, token: str) -> bool:
        if not isinstance(user.api_tokens, list):
            return False

        for token_data in user.api_tokens:
            if token_data.get('token') == token:
                expires_at = token_data.get('expires_at')
                if expires_at:
                    from datetime import datetime
                    expiry = datetime.fromisoformat(expires_at)
                    if timezone.now() > expiry:
                        return False

                token_data['last_used_at'] = timezone.now().isoformat()
                user.save()
                return True
        return False


class VerificationService:
    """Handles verification token generation and email sending."""

    @staticmethod
    def ensure_token(user) -> str:
        if not user.verification_token and not user.email_verified_at:
            user.verification_token = TokenService.generate(32)
            user.save()
        return user.verification_token

    @staticmethod
    def send_verification_email(user) -> None:
        token = VerificationService.ensure_token(user)
        subject = 'Verify your email address'
        message = f'Please verify your email by clicking this link: /verify-email/{token}'
        send_mail(subject, message, 'noreply@yoursite.com', [user.email])

    @staticmethod
    def verify_email(user, token: str) -> bool:
        if user.verification_token == token:
            user.email_verified_at = timezone.now()
            user.verification_token = None
            user.save()
            return True
        return False
