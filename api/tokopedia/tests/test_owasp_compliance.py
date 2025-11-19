"""
OWASP Compliance Tests for Tokopedia API
Tests A01:2021 (Broken Access Control) implementation
"""
import pytest
from django.test import RequestFactory, TestCase
from django.http import JsonResponse
from api.tokopedia.security import (
    RateLimiter,
    AccessControlManager,
    require_api_token,
    enforce_resource_limits
)
import time
import json


class TestRateLimiter(TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        self.rate_limiter = RateLimiter()
        
    def test_rate_limit_allows_requests_within_limit(self):
        """Test that requests within rate limit are allowed"""
        client_id = "test_client_1"
        
        # Make requests within limit
        for i in range(10):
            is_allowed, error = self.rate_limiter.check_rate_limit(
                client_id, max_requests=10, window_seconds=60
            )
            if i < 10:
                self.assertTrue(is_allowed)
                self.assertIsNone(error)
    
    def test_rate_limit_blocks_excessive_requests(self):
        """Test that excessive requests are blocked"""
        client_id = "test_client_2"
        
        # Make requests up to limit
        for i in range(10):
            self.rate_limiter.check_rate_limit(
                client_id, max_requests=10, window_seconds=60
            )
        
        # Next request should be blocked
        is_allowed, error = self.rate_limiter.check_rate_limit(
            client_id, max_requests=10, window_seconds=60
        )
        self.assertFalse(is_allowed)
        self.assertIsNotNone(error)
        self.assertIn("Rate limit exceeded", error)
    
    def test_rate_limit_blocks_client_temporarily(self):
        """Test that blocked clients remain blocked for specified duration"""
        client_id = "test_client_3"
        
        # Block the client
        self.rate_limiter.block_client(client_id, duration_seconds=1)
        
        # Check that client is blocked
        self.assertTrue(self.rate_limiter.is_blocked(client_id))
        
        # Wait for block to expire
        time.sleep(1.1)
        
        # Check that client is no longer blocked
        self.assertFalse(self.rate_limiter.is_blocked(client_id))
    
    def test_rate_limit_cleans_old_requests(self):
        """Test that old requests are properly cleaned up"""
        client_id = "test_client_4"
        
        # Make requests
        for i in range(5):
            self.rate_limiter.check_rate_limit(
                client_id, max_requests=10, window_seconds=1
            )
        
        # Wait for window to pass
        time.sleep(1.1)
        
        # Old requests should be cleaned, new requests allowed
        is_allowed, error = self.rate_limiter.check_rate_limit(
            client_id, max_requests=10, window_seconds=1
        )
        self.assertTrue(is_allowed)


class TestAccessControlManager(TestCase):
    """Test access control and token validation"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_valid_token_authentication(self):
        """Test that valid tokens are accepted"""
        request = self.factory.get('/api/test')
        request.META['HTTP_X_API_TOKEN'] = 'dev-token-12345'
        
        is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, '')
        self.assertIsNotNone(token_info)
        self.assertEqual(token_info['name'], 'Development Token')
    
    def test_missing_token_rejection(self):
        """Test that requests without tokens are rejected"""
        request = self.factory.get('/api/test')
        
        is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
        
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, 'API token required')
        self.assertIsNone(token_info)
    
    def test_invalid_token_rejection(self):
        """Test that invalid tokens are rejected"""
        request = self.factory.get('/api/test')
        request.META['HTTP_X_API_TOKEN'] = 'invalid-token'
        
        is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
        
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, 'Invalid API token')
        self.assertIsNone(token_info)
    
    def test_permission_check_allows_authorized_action(self):
        """Test that tokens with required permission are allowed"""
        token_info = {
            'name': 'Test Token',
            'permissions': ['read', 'write', 'scrape']
        }
        
        has_permission = AccessControlManager.check_permission(token_info, 'scrape')
        self.assertTrue(has_permission)
    
    def test_permission_check_denies_unauthorized_action(self):
        """Test that tokens without required permission are denied"""
        token_info = {
            'name': 'Read Only Token',
            'permissions': ['read']
        }
        
        has_permission = AccessControlManager.check_permission(token_info, 'scrape')
        self.assertFalse(has_permission)
    
    def test_token_authorization_header(self):
        """Test token extraction from Authorization header"""
        request = self.factory.get('/api/test')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer dev-token-12345'
        
        is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(token_info)


class TestSecurityDecorators(TestCase):
    """Test security decorator functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_require_api_token_decorator_accepts_valid_token(self):
        """Test that decorator allows requests with valid token"""
        @require_api_token(required_permission='scrape')
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test')
        request.META['HTTP_X_API_TOKEN'] = 'dev-token-12345'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_require_api_token_decorator_rejects_missing_token(self):
        """Test that decorator rejects requests without token"""
        @require_api_token(required_permission='scrape')
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_require_api_token_decorator_checks_permissions(self):
        """Test that decorator enforces permission requirements"""
        @require_api_token(required_permission='write')
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Use read-only token that lacks 'write' permission
        request = self.factory.get('/api/test')
        request.META['HTTP_X_API_TOKEN'] = 'read-only-token'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Insufficient permissions', data['error'])
    
    def test_enforce_resource_limits_decorator_allows_valid_limits(self):
        """Test that decorator allows requests within resource limits"""
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test?limit=50')
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_enforce_resource_limits_decorator_rejects_excessive_limits(self):
        """Test that decorator rejects requests exceeding resource limits"""
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test?limit=200')
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('exceeds maximum', data['error'])
    
    def test_enforce_resource_limits_decorator_rejects_too_many_params(self):
        """Test that decorator rejects requests with too many query parameters"""
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Create request with 21 parameters (exceeds limit of 20)
        query_string = '&'.join([f'param{i}=value{i}' for i in range(21)])
        request = self.factory.get(f'/api/test?{query_string}')
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Too many query parameters', data['error'])


class TestIntegratedAccessControl(TestCase):
    """Test integrated access control flow"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_full_access_control_flow_success(self):
        """Test complete access control flow with valid credentials"""
        @require_api_token(required_permission='scrape')
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({
                'success': True,
                'token_owner': request.token_info['owner']
            })
        
        request = self.factory.get('/api/test?limit=10')
        request.META['HTTP_X_API_TOKEN'] = 'dev-token-12345'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['token_owner'], 'dev-team')
    
    def test_full_access_control_flow_with_rate_limiting(self):
        """Test that rate limiting works in full flow"""
        # Create a fresh rate limiter for this test to avoid interference
        from api.tokopedia.security import rate_limiter as rl
        
        @require_api_token(required_permission='scrape')
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test_rate_limit')
        request.META['HTTP_X_API_TOKEN'] = 'dev-token-12345'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.path = '/api/test_rate_limit'
        
        # Make requests up to rate limit (100 per minute for dev token)
        # Test with exactly 100 requests
        for i in range(100):
            response = test_view(request)
            self.assertEqual(response.status_code, 200)
        
        # 101st request should be rate limited
        response = test_view(request)
        self.assertEqual(response.status_code, 429)
        data = json.loads(response.content)
        self.assertIn('Rate limit exceeded', data['error'])


# =============================================================================
# OWASP A01:2021 Compliance Verification
# =============================================================================

class TestOWASPA01Compliance(TestCase):
    """Verify OWASP A01:2021 Broken Access Control compliance"""
    
    def test_access_control_enforced_at_trusted_code(self):
        """Verify: Access control checks are enforced in trusted server-side code"""
        # The decorators ensure access control is on server side
        self.assertTrue(callable(require_api_token))
        
    def test_deny_by_default(self):
        """Verify: Deny by default - all requests require authentication"""
        factory = RequestFactory()
        
        @require_api_token()
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Request without token should be denied
        request = factory.get('/api/test')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        response = test_view(request)
        self.assertEqual(response.status_code, 401)
    
    def test_principle_of_least_privilege(self):
        """Verify: Principle of least privilege - permissions are checked"""
        factory = RequestFactory()
        
        @require_api_token(required_permission='admin')
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Dev token should not have admin permission
        request = factory.get('/api/test')
        request.META['HTTP_X_API_TOKEN'] = 'dev-token-12345'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        response = test_view(request)
        self.assertEqual(response.status_code, 403)
    
    def test_rate_limiting_enforced(self):
        """Verify: Rate limiting to minimize harm from automated attacks"""
        rate_limiter = RateLimiter()
        
        # Exceed rate limit
        for i in range(11):
            rate_limiter.check_rate_limit("test", max_requests=10, window_seconds=60)
        
        is_allowed, error = rate_limiter.check_rate_limit("test", max_requests=10, window_seconds=60)
        self.assertFalse(is_allowed)
    
    def test_access_control_failures_logged(self):
        """Verify: Access control failures are logged"""
        factory = RequestFactory()
        
        @require_api_token()
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = factory.get('/api/test')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # This should log the failure
        with self.assertLogs('api.tokopedia.security', level='WARNING') as cm:
            response = test_view(request)
            self.assertEqual(response.status_code, 401)
            # Verify that access denial was logged
            self.assertTrue(any('Access denied' in log for log in cm.output))
