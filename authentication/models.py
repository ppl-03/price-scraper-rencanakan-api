from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.core.mail import send_mail
import hashlib
import secrets
import string


class Company(models.Model):
    """
    Company model representing organizational accounts
    Links users to companies and affects permissions/access scope
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Company settings
    is_active = models.BooleanField(default=True)
    subscription_plan = models.CharField(max_length=50, default='basic')
    max_users = models.PositiveIntegerField(default=5)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def user_count(self):
        """Get the number of users in this company"""
        return self.users.filter(is_active=True).count()
    
    def can_add_user(self):
        """Check if company can add more users based on subscription"""
        return self.user_count < self.max_users


class UserManager(BaseUserManager):
    """Custom manager for User model"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with email and password"""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with enhanced authentication features
    
    Key Traits:
    - HasApiTokens: Sanctum-like token management
    - HasHashid: Obfuscated ID generation
    - Notifiable: Email notification support
    """
    
    # Remove username field, use email instead
    username = None
    email = models.EmailField(unique=True)
    
    # Personal Information
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Company relationship (optional)
    company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users'
    )
    
    # Authentication & Security
    email_verified_at = models.DateTimeField(null=True, blank=True)
    verification_token = models.CharField(max_length=255, blank=True, null=True)
    
    # API Token fields (Sanctum-like)
    api_tokens = models.JSONField(default=list, blank=True)
    current_access_token = models.CharField(max_length=255, blank=True, null=True)
    
    # Session tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['company']),
            models.Index(fields=['is_active']),
            models.Index(fields=['email_verified_at']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def save(self, *args, **kwargs):
        """Override save to generate verification token if needed"""
        if not self.verification_token and not self.email_verified_at:
            self.verification_token = self.generate_token()
        super().save(*args, **kwargs)
    
    # HasHashid functionality
    @property
    def hashid(self):
        """Generate obfuscated ID using hash of pk and secret"""
        if not self.pk:
            return None
        secret = "your-secret-key-here"  # Should be in settings
        raw_string = f"{self.pk}-{secret}"
        return hashlib.sha256(raw_string.encode()).hexdigest()[:16]
    
    @classmethod
    def get_by_hashid(cls, hashid):
        """Get user by hashid"""
        for user in cls.objects.all():
            if user.hashid == hashid:
                return user
        return None
    
    # HasApiTokens functionality
    def create_api_token(self, name="default", expires_at=None):
        """Create a new API token for the user"""
        token = self.generate_token(length=64)
        token_data = {
            'name': name,
            'token': token,
            'created_at': timezone.now().isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'last_used_at': None
        }
        
        if not isinstance(self.api_tokens, list):
            self.api_tokens = []
        
        self.api_tokens.append(token_data)
        self.current_access_token = token
        self.save()
        return token
    
    def revoke_api_token(self, token):
        """Revoke a specific API token"""
        if isinstance(self.api_tokens, list):
            self.api_tokens = [t for t in self.api_tokens if t.get('token') != token]
            if self.current_access_token == token:
                self.current_access_token = None
            self.save()
    
    def revoke_all_tokens(self):
        """Revoke all API tokens"""
        self.api_tokens = []
        self.current_access_token = None
        self.save()
    
    def validate_api_token(self, token):
        """Validate if API token exists and is not expired"""
        if not isinstance(self.api_tokens, list):
            return False
        
        for token_data in self.api_tokens:
            if token_data.get('token') == token:
                expires_at = token_data.get('expires_at')
                if expires_at:
                    from datetime import datetime
                    expiry = datetime.fromisoformat(expires_at)
                    if timezone.now() > expiry:
                        return False
                
                # Update last used
                token_data['last_used_at'] = timezone.now().isoformat()
                self.save()
                return True
        return False
    
    # Email verification
    def send_verification_email(self):
        """Send email verification"""
        if not self.verification_token:
            self.verification_token = self.generate_token()
            self.save()
        
        # Send email with verification link
        subject = 'Verify your email address'
        message = f'Please verify your email by clicking this link: /verify-email/{self.verification_token}'
        send_mail(subject, message, 'noreply@yoursite.com', [self.email])
    
    def verify_email(self, token):
        """Verify email with token"""
        if self.verification_token == token:
            self.email_verified_at = timezone.now()
            self.verification_token = None
            self.save()
            return True
        return False
    
    # Security features
    def set_password(self, raw_password):
        """Set password with bcrypt hashing"""
        self.password = make_password(raw_password)
    
    # Company-related methods
    def can_access_company(self, company):
        """Check if user can access specific company"""
        return self.company == company or self.is_superuser
    
    # Utility methods
    @staticmethod
    def generate_token(length=32):
        """Generate secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def get_full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return short name"""
        return self.first_name
    
    def update_last_activity(self, ip_address=None):
        """Update last activity timestamp and IP"""
        self.last_activity_at = timezone.now()
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['last_activity_at', 'last_login_ip'])
    
    @property
    def is_email_verified(self):
        """Check if email is verified"""
        return self.email_verified_at is not None
    
    @property
    def initials(self):
        """Get user initials"""
        return f"{self.first_name[0] if self.first_name else ''}{self.last_name[0] if self.last_name else ''}".upper()
