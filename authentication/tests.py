from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.core import mail
from datetime import datetime, timedelta
from unittest.mock import patch
import secrets

from .models import User, Company, UserManager

# Use ephemeral test-only passwords generated at runtime to avoid hard-coded
# credential literals in source. These are deterministic for a single test
# process (generated once per test module) and safe for use in assertions
# because the same variable is referenced across tests.
TEST_PASSWORD = secrets.token_urlsafe(12)
TEST_ADMIN_PASSWORD = secrets.token_urlsafe(12)
# Use an address reserved for documentation/testing per RFC 5737 to avoid
# using an actual private network gateway or leaking internal addresses.
TEST_IP = '192.0.2.1'


class CompanyModelTest(TestCase):
    """Test cases for Company model"""
    
    def setUp(self):
        """Set up test data"""
        self.company_data = {
            'name': 'Test Company',
            'slug': 'test-company',
            'email': 'contact@testcompany.com',
            'phone': '+1234567890',
            'address': '123 Test Street, Test City',
            'website': 'https://testcompany.com',
            'subscription_plan': 'premium',
            'max_users': 10
        }
    
    def test_company_creation(self):
        """Test basic company creation"""
        company = Company.objects.create(**self.company_data)
        
        self.assertEqual(company.name, 'Test Company')
        self.assertEqual(company.slug, 'test-company')
        self.assertEqual(company.email, 'contact@testcompany.com')
        self.assertEqual(company.subscription_plan, 'premium')
        self.assertEqual(company.max_users, 10)
        self.assertTrue(company.is_active)
        self.assertIsNotNone(company.created_at)
        self.assertIsNotNone(company.updated_at)
    
    def test_company_str_method(self):
        """Test string representation of company"""
        company = Company.objects.create(**self.company_data)
        self.assertEqual(str(company), 'Test Company')
    
    def test_company_slug_uniqueness(self):
        """Test that company slug must be unique"""
        Company.objects.create(**self.company_data)
        
        # Try to create another company with same slug
        with self.assertRaises(IntegrityError):
            Company.objects.create(
                name='Another Company',
                slug='test-company'  # Same slug
            )
    
    def test_company_defaults(self):
        """Test default values for company"""
        company = Company.objects.create(
            name='Minimal Company',
            slug='minimal-company'
        )
        
        self.assertTrue(company.is_active)
        self.assertEqual(company.subscription_plan, 'basic')
        self.assertEqual(company.max_users, 5)
    
    def test_user_count_property(self):
        """Test user_count property"""
        company = Company.objects.create(**self.company_data)
        
        # Initially should be 0
        self.assertEqual(company.user_count, 0)
        
        # Create users
        User.objects.create_user(
            email='user1@test.com',
            password=TEST_PASSWORD,
            first_name='User',
            last_name='One',
            company=company
        )
        User.objects.create_user(
            email='user2@test.com',
            password=TEST_PASSWORD,
            first_name='User',
            last_name='Two',
            company=company
        )
        
        # Should now be 2
        self.assertEqual(company.user_count, 2)
        
        # Create inactive user
        inactive_user = User.objects.create_user(
            email='inactive@test.com',
            password=TEST_PASSWORD,
            first_name='Inactive',
            last_name='User',
            company=company
        )
        inactive_user.is_active = False
        inactive_user.save()
        
        # Should still be 2 (inactive users don't count)
        self.assertEqual(company.user_count, 2)
    
    def test_can_add_user_method(self):
        """Test can_add_user method"""
        company = Company.objects.create(
            name='Small Company',
            slug='small-company',
            max_users=2
        )
        
        # Initially should be able to add users
        self.assertTrue(company.can_add_user())
        
        # Add users up to limit
        User.objects.create_user(
            email='user1@test.com',
            password=TEST_PASSWORD,
            first_name='User',
            last_name='One',
            company=company
        )
        self.assertTrue(company.can_add_user())
        
        User.objects.create_user(
            email='user2@test.com',
            password=TEST_PASSWORD,
            first_name='User',
            last_name='Two',
            company=company
        )
        
        # Should now be at limit
        self.assertFalse(company.can_add_user())


class UserManagerTest(TestCase):
    """Test cases for UserManager"""
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(
            email='test@example.com',
            password=TEST_PASSWORD,
            first_name='Test',
            last_name='User'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(TEST_PASSWORD))
    
    def test_create_user_without_email(self):
        """Test that creating user without email raises error"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(
                email='',
                password=TEST_PASSWORD
            )
        self.assertEqual(str(context.exception), 'The Email field must be set')
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password=TEST_ADMIN_PASSWORD,
            first_name='Admin',
            last_name='User'
        )
        
        self.assertEqual(user.email, 'admin@example.com')
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_create_superuser_invalid_flags(self):
        """Test creating superuser with invalid flags"""
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='admin@example.com',
                password=TEST_ADMIN_PASSWORD,
                is_staff=False
            )
        
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='admin@example.com',
                password=TEST_ADMIN_PASSWORD,
                is_superuser=False
            )


class UserModelTest(TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            slug='test-company'
        )
        
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+1234567890',
            'company': self.company
        }
    
    def test_user_creation(self):
        """Test basic user creation"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.phone, '+1234567890')
        self.assertEqual(user.company, self.company)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
        self.assertIsNotNone(user.verification_token)  # Auto-generated
    
    def test_user_str_method(self):
        """Test string representation of user"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        self.assertEqual(str(user), 'Test User (test@example.com)')
    
    def test_email_uniqueness(self):
        """Test that email must be unique"""
        User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='test@example.com',  # Same email
                    password=TEST_PASSWORD,
                first_name='Another',
                last_name='User'
            )
    
    def test_username_field(self):
        """Test that email is used as username field"""
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertEqual(User.REQUIRED_FIELDS, ['first_name', 'last_name'])
    
    def test_get_full_name(self):
        """Test get_full_name method"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        self.assertEqual(user.get_full_name(), 'Test User')
    
    def test_get_short_name(self):
        """Test get_short_name method"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        self.assertEqual(user.get_short_name(), 'Test')
    
    def test_initials_property(self):
        """Test initials property"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        self.assertEqual(user.initials, 'TU')
    
    def test_hashid_property(self):
        """Test hashid property"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        # Should return None before save (no pk)
        user_no_pk = User(email='new@test.com')
        self.assertIsNone(user_no_pk.hashid)
        
        # Should return hashid after save
        self.assertIsNotNone(user.hashid)
        self.assertEqual(len(user.hashid), 16)
        
        # Should be consistent
        hashid1 = user.hashid
        hashid2 = user.hashid
        self.assertEqual(hashid1, hashid2)
    
    def test_get_by_hashid(self):
        """Test get_by_hashid class method"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        found_user = User.get_by_hashid(user.hashid)
        self.assertEqual(found_user, user)
        
        # Test with invalid hashid
        not_found = User.get_by_hashid('invalid_hashid')
        self.assertIsNone(not_found)
    
    def test_api_token_creation(self):
        """Test API token creation"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        token = user.create_api_token('test_token')
        
        self.assertIsNotNone(token)
        self.assertEqual(len(token), 64)
        self.assertEqual(user.current_access_token, token)
        self.assertEqual(len(user.api_tokens), 1)
        self.assertEqual(user.api_tokens[0]['name'], 'test_token')
        self.assertEqual(user.api_tokens[0]['token'], token)
    
    def test_api_token_with_expiry(self):
        """Test API token creation with expiry"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        expires_at = timezone.now() + timedelta(hours=24)
        token = user.create_api_token('expiring_token', expires_at)
        
        self.assertEqual(user.api_tokens[0]['expires_at'], expires_at.isoformat())
    
    def test_api_token_validation(self):
        """Test API token validation"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        token = user.create_api_token()
        
        # Valid token
        self.assertTrue(user.validate_api_token(token))
        
        # Invalid token
        self.assertFalse(user.validate_api_token('invalid_token'))
    
    def test_api_token_validation_with_expiry(self):
        """Test API token validation with expired token"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        # Create expired token
        past_time = timezone.now() - timedelta(hours=1)
        token = user.create_api_token('expired_token', past_time)
        
        # Should be invalid
        self.assertFalse(user.validate_api_token(token))
    
    def test_revoke_api_token(self):
        """Test revoking specific API token"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        token1 = user.create_api_token('token1')
        token2 = user.create_api_token('token2')
        
        self.assertEqual(len(user.api_tokens), 2)
        
        user.revoke_api_token(token1)
        
        self.assertEqual(len(user.api_tokens), 1)
        self.assertEqual(user.api_tokens[0]['token'], token2)
    
    def test_revoke_all_tokens(self):
        """Test revoking all API tokens"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        user.create_api_token('token1')
        user.create_api_token('token2')
        
        self.assertEqual(len(user.api_tokens), 2)
        
        user.revoke_all_tokens()
        
        self.assertEqual(len(user.api_tokens), 0)
        self.assertIsNone(user.current_access_token)
    
    def test_email_verification(self):
        """Test email verification functionality"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        # Initially not verified
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(user.verification_token)
        
        # Verify email
        token = user.verification_token
        result = user.verify_email(token)
        
        self.assertTrue(result)
        self.assertTrue(user.is_email_verified)
        self.assertIsNone(user.verification_token)
        
        # Try with invalid token
        result = user.verify_email('invalid_token')
        self.assertFalse(result)
    
    @patch('authentication.services.send_mail')
    def test_send_verification_email(self, mock_send_mail):
        """Test sending verification email"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        user.send_verification_email()
        
        # Check that send_mail was called
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        self.assertEqual(args[0], 'Verify your email address')
        self.assertIn(user.verification_token, args[1])
        self.assertEqual(args[3], [user.email])
    
    def test_can_access_company(self):
        """Test company access permissions"""
        company1 = Company.objects.create(name='Company 1', slug='company-1')
        company2 = Company.objects.create(name='Company 2', slug='company-2')
        
        user = User.objects.create_user(
            email='user@test.com',
            password=TEST_PASSWORD,
            first_name='Test',
            last_name='User',
            company=company1
        )
        
        # Can access own company
        self.assertTrue(user.can_access_company(company1))
        
        # Cannot access other company
        self.assertFalse(user.can_access_company(company2))
        
        # Superuser can access any company
        superuser = User.objects.create_superuser(
            email='admin@test.com',
            password=TEST_ADMIN_PASSWORD,
            first_name='Admin',
            last_name='User'
        )
        self.assertTrue(superuser.can_access_company(company1))
        self.assertTrue(superuser.can_access_company(company2))
    
    def test_update_last_activity(self):
        """Test updating last activity"""
        user = User.objects.create_user(
            password=TEST_PASSWORD,
            **self.user_data
        )
        
        # Initially None
        self.assertIsNone(user.last_activity_at)
        self.assertIsNone(user.last_login_ip)
        # Update activity (use reserved documentation IP)
        test_ip = TEST_IP
        user.update_last_activity(test_ip)

        self.assertIsNotNone(user.last_activity_at)
        self.assertEqual(user.last_login_ip, test_ip)
    
    def test_generate_token(self):
        """Test token generation"""
        token1 = User.generate_token()
        token2 = User.generate_token()
        
        # Should be different
        self.assertNotEqual(token1, token2)
        
        # Should be correct length
        self.assertEqual(len(token1), 32)
        
        # Test custom length
        long_token = User.generate_token(64)
        self.assertEqual(len(long_token), 64)
    
    def test_verification_token_auto_generation(self):
        """Test that verification token is auto-generated on save"""
        user = User(
            email='new@test.com',
            first_name='New',
            last_name='User'
        )
        
        # No token before save
        self.assertIsNone(user.verification_token)
        
        user.save()
        
        # Token generated after save
        self.assertIsNotNone(user.verification_token)
    
    def test_model_ordering(self):
        """Test model ordering"""
        # Create users at different times
        user1 = User.objects.create_user(
            email='user1@test.com',
            password=TEST_PASSWORD,
            first_name='User',
            last_name='One'
        )
        
        user2 = User.objects.create_user(
            email='user2@test.com',
            password=TEST_PASSWORD,
            first_name='User',
            last_name='Two'
        )
        
        # Should be ordered by -created_at (newest first)
        users = list(User.objects.all())
        self.assertEqual(users[0], user2)  # Newest first
        self.assertEqual(users[1], user1)
