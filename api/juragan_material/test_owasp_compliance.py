"""
OWASP Compliance Test Suite for Juragan Material Module
Tests compliance with A01:2021 - Broken Access Control

This test suite simulates real-world attack scenarios and verifies that 
security controls are properly implemented according to OWASP guidelines.
"""
import unittest
import time
import os
from unittest.mock import Mock, patch
from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings

# Load test IP addresses from Django settings (configured from .env file)
# These are RFC 1918 private addresses for testing only
TEST_IP_ALLOWED = settings.TEST_IP_ALLOWED
TEST_IP_DENIED = settings.TEST_IP_DENIED
TEST_IP_ATTACKER = settings.TEST_IP_ATTACKER

from .security import (
    RateLimiter,
    AccessControlManager,
    require_api_token,
    enforce_resource_limits,
)


class TestA01BrokenAccessControl(TestCase):
    """
    Test suite for OWASP A01:2021 - Broken Access Control
    
    Tests:
    1. Access control is enforced server-side
    2. Deny by default
    3. Access control mechanisms are reusable
    4. Record ownership enforcement
    5. Rate limiting
    6. Access control failure logging
    """
    
    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()
    
    def test_deny_by_default_no_token(self):
        """Test that access is denied by default without token"""
        print("\n[A01] Test: Deny by default - No token provided")
        
        request = self.factory.get('/api/juragan_material/scrape/')
        is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
        
        self.assertFalse(is_valid, "Access should be denied without token")
        self.assertEqual(error_msg, 'API token required')
        self.assertIsNone(token_info)
        print("✓ Access denied without token")
    
    def test_deny_invalid_token(self):
        """Test that invalid tokens are rejected"""
        print("\n[A01] Test: Deny invalid token")
        
        request = self.factory.get(
            '/api/juragan_material/scrape/',
            HTTP_X_API_TOKEN='invalid-token-xyz'
        )
        is_valid, error_msg, _ = AccessControlManager.validate_token(request)
        
        self.assertFalse(is_valid, "Invalid token should be rejected")
        self.assertEqual(error_msg, 'Invalid API token')
        print("✓ Invalid token rejected")
    
    def test_valid_token_accepted(self):
        """Test that valid tokens are accepted"""
        print("\n[A01] Test: Valid token accepted")
        
        request = self.factory.get(
            '/api/juragan_material/scrape/',
            HTTP_X_API_TOKEN='dev-token-12345'
        )
        is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
        
        self.assertTrue(is_valid, "Valid token should be accepted")
        self.assertEqual(error_msg, '')
        self.assertIsNotNone(token_info)
        self.assertEqual(token_info['name'], 'Development Token')
        print("✓ Valid token accepted")
    
    def test_token_with_bearer_prefix(self):
        """Test that tokens with Bearer prefix are accepted"""
        print("\n[A01] Test: Token with Bearer prefix")
        
        request = self.factory.get(
            '/api/juragan_material/scrape/',
            HTTP_AUTHORIZATION='Bearer dev-token-12345'
        )
        is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
        
        self.assertTrue(is_valid, "Token with Bearer prefix should be accepted")
        self.assertEqual(token_info['name'], 'Development Token')
        print("✓ Bearer token accepted")
    
    def test_permission_enforcement_read(self):
        """Test that read permissions are enforced"""
        print("\n[A01] Test: Read permission enforcement")
        
        # Token with all permissions
        token_info = {
            'name': 'Development Token',
            'permissions': ['read', 'write', 'scrape']
        }
        
        has_read = AccessControlManager.check_permission(token_info, 'read')
        self.assertTrue(has_read, "Should have read permission")
        print("✓ Read permission granted")
    
    def test_permission_enforcement_write(self):
        """Test that write permissions are enforced (principle of least privilege)"""
        print("\n[A01] Test: Write permission enforcement")
        
        # Token with read-only permission
        token_info = {
            'name': 'Read Only Token',
            'permissions': ['read']
        }
        
        # Should have read permission
        has_read = AccessControlManager.check_permission(token_info, 'read')
        self.assertTrue(has_read, "Should have read permission")
        print("✓ Read permission granted")
        
        # Should NOT have write permission
        has_write = AccessControlManager.check_permission(token_info, 'write')
        self.assertFalse(has_write, "Should not have write permission")
        print("✓ Write permission denied (principle of least privilege)")
    
    def test_permission_enforcement_scrape(self):
        """Test that scrape permissions are enforced"""
        print("\n[A01] Test: Scrape permission enforcement")
        
        # Legacy token with limited permissions
        token_info = {
            'name': 'Legacy Client Token',
            'permissions': ['read', 'scrape']
        }
        
        has_scrape = AccessControlManager.check_permission(token_info, 'scrape')
        self.assertTrue(has_scrape, "Should have scrape permission")
        print("✓ Scrape permission granted")
        
        # Should NOT have write permission
        has_write = AccessControlManager.check_permission(token_info, 'write')
        self.assertFalse(has_write, "Should not have write permission")
        print("✓ Write permission denied for legacy token")
    
    def test_rate_limiting_enforcement(self):
        """Test that rate limiting prevents automated attacks"""
        print("\n[A01] Test: Rate limiting enforcement")
        
        rate_limiter = RateLimiter()
        client_id = "test_client_123"
        
        # Should allow first 10 requests
        for i in range(10):
            is_allowed, error = rate_limiter.check_rate_limit(
                client_id, max_requests=10, window_seconds=60
            )
            self.assertTrue(is_allowed, f"Request {i+1} should be allowed")
        
        print("✓ First 10 requests allowed")
        
        # 11th request should be blocked
        is_allowed, error = rate_limiter.check_rate_limit(
            client_id, max_requests=10, window_seconds=60
        )
        self.assertFalse(is_allowed, "11th request should be blocked")
        self.assertIn("Rate limit exceeded", error)
        print("✓ 11th request blocked (rate limit enforced)")
    
    def test_rate_limiting_blocks_client(self):
        """Test that repeated violations result in client blocking"""
        print("\n[A01] Test: Client blocking on rate limit violation")
        
        rate_limiter = RateLimiter()
        client_id = "attacker_ip_456"
        
        # Exceed rate limit to trigger block
        for _ in range(11):
            rate_limiter.check_rate_limit(
                client_id, max_requests=10, window_seconds=60, block_on_violation=True
            )
        
        # Verify client is blocked
        is_blocked = rate_limiter.is_blocked(client_id)
        self.assertTrue(is_blocked, "Client should be blocked after violation")
        print("✓ Client blocked after rate limit violation")
        
        # Verify blocked client cannot make requests
        is_allowed, error = rate_limiter.check_rate_limit(
            client_id, max_requests=10, window_seconds=60
        )
        self.assertFalse(is_allowed, "Blocked client should not be allowed")
        self.assertIn("Blocked for", error)
        print("✓ Blocked client cannot make requests")
    
    def test_rate_limiting_window_cleanup(self):
        """Test that old requests are cleaned up after time window"""
        print("\n[A01] Test: Rate limiting window cleanup")
        
        rate_limiter = RateLimiter()
        client_id = "test_client_window"
        
        # Add requests
        for _ in range(5):
            rate_limiter.check_rate_limit(client_id, max_requests=10, window_seconds=1)
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Clean old requests
        rate_limiter._clean_old_requests(client_id, 1)
        
        # Should have no requests in current window
        self.assertEqual(len(rate_limiter.requests[client_id]), 0)
        print("✓ Old requests cleaned up after time window")
    
    def test_access_logging_success(self):
        """Test that successful access attempts are logged"""
        print("\n[A01] Test: Access control logging - Success")
        
        request = self.factory.get(
            '/api/juragan_material/scrape/',
            REMOTE_ADDR=TEST_IP_ALLOWED
        )
        
        with self.assertLogs('api.juragan_material.security', level='INFO') as cm:
            AccessControlManager.log_access_attempt(request, True)
        
        # Verify log contains relevant information
        log_output = cm.output[0]
        self.assertIn(TEST_IP_ALLOWED, log_output)
        self.assertIn('Access granted', log_output)
        print("✓ Successful access logged")
    
    def test_access_logging_failure(self):
        """Test that failed access attempts are logged"""
        print("\n[A01] Test: Access control logging - Failure")
        
        request = self.factory.get(
            '/api/juragan_material/scrape/',
            REMOTE_ADDR=TEST_IP_DENIED
        )
        
        with self.assertLogs('api.juragan_material.security', level='WARNING') as cm:
            AccessControlManager.log_access_attempt(
                request, False, 'Invalid token'
            )
        
        # Verify log contains relevant information
        log_output = cm.output[0]
        self.assertIn(TEST_IP_DENIED, log_output)
        self.assertIn('Access denied', log_output)
        print("✓ Failed access logged")
    
    def test_ip_whitelist_enforcement(self):
        """Test that IP whitelisting is enforced"""
        print("\n[A01] Test: IP whitelist enforcement")
        
        # Create token with IP whitelist using environment variables
        AccessControlManager.API_TOKENS['restricted-token'] = {
            'name': 'Restricted Token',
            'permissions': ['read'],
            'allowed_ips': [TEST_IP_ALLOWED],  # Test whitelist entry from env
            'rate_limit': {'requests': 100, 'window': 60}
        }
        
        # Request from allowed IP
        request_allowed = self.factory.get(
            '/api/juragan_material/scrape/',
            HTTP_X_API_TOKEN='restricted-token',
            REMOTE_ADDR=TEST_IP_ALLOWED  # Whitelisted IP from env
        )
        is_valid, error_msg, _ = AccessControlManager.validate_token(request_allowed)
        self.assertTrue(is_valid, "Request from whitelisted IP should be allowed")
        print("✓ Whitelisted IP allowed")
        
        # Request from non-allowed IP
        request_denied = self.factory.get(
            '/api/juragan_material/scrape/',
            HTTP_X_API_TOKEN='restricted-token',
            REMOTE_ADDR=TEST_IP_DENIED  # Non-whitelisted IP from env
        )
        is_valid, error_msg, _ = AccessControlManager.validate_token(request_denied)
        self.assertFalse(is_valid, "Request from non-whitelisted IP should be denied")
        self.assertIn('not authorized', error_msg)
        print("✓ Non-whitelisted IP denied")
    
    def test_ip_whitelist_empty_allows_all(self):
        """Test that empty IP whitelist allows all IPs"""
        print("\n[A01] Test: Empty IP whitelist allows all")
        
        # Dev token has empty allowed_ips
        request = self.factory.get(
            '/api/juragan_material/scrape/',
            HTTP_X_API_TOKEN='dev-token-12345',
            REMOTE_ADDR='192.168.1.100'
        )
        is_valid, _, _ = AccessControlManager.validate_token(request)
        self.assertTrue(is_valid, "Empty whitelist should allow all IPs")
        print("✓ Empty whitelist allows all IPs")


class TestResourceLimitEnforcement(TestCase):
    """
    Test suite for resource limit enforcement
    """
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_enforce_resource_limits_normal(self):
        """Test that normal requests pass resource limits"""
        print("\n[RESOURCE] Test: Normal request passes limits")
        
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'status': 'ok'})
        
        request = self.factory.get('/api/test', {'keyword': 'cement', 'page': '0'})
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        print("✓ Normal request passes resource limits")
    
    def test_enforce_resource_limits_excessive_limit(self):
        """Test that excessive limit parameter is rejected"""
        print("\n[RESOURCE] Test: Excessive limit rejected")
        
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'status': 'ok'})
        
        request = self.factory.get('/api/test', {'limit': '1000'})
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
        import json
        data = json.loads(response.content)
        self.assertIn('exceeds maximum', data['error'])
        print("✓ Excessive limit rejected")
    
    def test_enforce_resource_limits_invalid_limit(self):
        """Test that invalid limit parameter is rejected"""
        print("\n[RESOURCE] Test: Invalid limit rejected")
        
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'status': 'ok'})
        
        request = self.factory.get('/api/test', {'limit': 'invalid'})
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
        import json
        data = json.loads(response.content)
        self.assertIn('Invalid limit', data['error'])
        print("✓ Invalid limit rejected")
    
    def test_enforce_resource_limits_too_many_params(self):
        """Test that too many query parameters are rejected"""
        print("\n[RESOURCE] Test: Too many parameters rejected")
        
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'status': 'ok'})
        
        # Create request with 25 parameters
        params = {f'param{i}': f'value{i}' for i in range(25)}
        request = self.factory.get('/api/test', params)
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
        import json
        data = json.loads(response.content)
        self.assertIn('Too many', data['error'])
        print("✓ Excessive parameters rejected")


class TestIntegratedSecurityScenarios(TestCase):
    """
    Integration tests simulating real-world attack scenarios
    """
    
    def setUp(self):
        cache.clear()
    
    def test_scenario_brute_force_attack(self):
        """Simulate brute force attack with invalid tokens"""
        print("\n[INTEGRATION] Scenario: Brute force attack simulation")
        
        rate_limiter = RateLimiter()
        # Use attacker IP from environment variable
        attacker_ip = TEST_IP_ATTACKER
        
        # Simulate rapid invalid token attempts
        for attempt in range(15):
            client_id = f"{attacker_ip}:/api/juragan_material/scrape/"
            is_allowed, error = rate_limiter.check_rate_limit(
                client_id, max_requests=10, window_seconds=60
            )
            
            if not is_allowed:
                print(f"✓ Attack blocked at attempt {attempt + 1}")
                self.assertIn("Rate limit exceeded", error)
                break
        
        # Verify attacker is blocked
        is_blocked = rate_limiter.is_blocked(client_id)
        self.assertTrue(is_blocked, "Attacker should be blocked")
        print("✓ Brute force attack successfully mitigated")
    
    def test_scenario_privilege_escalation(self):
        """Simulate privilege escalation attempt"""
        print("\n[INTEGRATION] Scenario: Privilege escalation attempt")
        
        # Attacker has read-only token
        read_only_token = {
            'name': 'Read Only Token',
            'permissions': ['read']
        }
        
        # Try to perform write operation
        can_write = AccessControlManager.check_permission(read_only_token, 'write')
        self.assertFalse(can_write, "Write permission should be denied")
        print("✓ Write operation denied for read-only token")
        
        # Try to perform admin operation
        can_admin = AccessControlManager.check_permission(read_only_token, 'admin')
        self.assertFalse(can_admin, "Admin permission should be denied")
        print("✓ Admin operation denied for read-only token")
        
        print("✓ Privilege escalation successfully prevented")
    
    def test_scenario_resource_exhaustion(self):
        """Simulate resource exhaustion attack"""
        print("\n[INTEGRATION] Scenario: Resource exhaustion attack")
        
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'status': 'ok'})
        
        factory = RequestFactory()
        
        # Attempt to request excessive data
        request = factory.get('/api/test', {'limit': '999999'})
        response = test_view(request)
        self.assertEqual(response.status_code, 400)
        print("✓ Excessive data request blocked")
        
        # Attempt to send excessive parameters (parameter pollution)
        params = {f'param{i}': 'x' * 1000 for i in range(50)}
        request = factory.get('/api/test', params)
        response = test_view(request)
        self.assertEqual(response.status_code, 400)
        print("✓ Parameter pollution blocked")
        
        print("✓ Resource exhaustion attack successfully mitigated")
    
    def test_scenario_token_permissions_matrix(self):
        """Test complete permission matrix for all tokens"""
        print("\n[INTEGRATION] Scenario: Token permission matrix")
        
        test_cases = [
            ('dev-token-12345', 'read', True),
            ('dev-token-12345', 'write', True),
            ('dev-token-12345', 'scrape', True),
            ('legacy-api-token-67890', 'read', True),
            ('legacy-api-token-67890', 'write', False),
            ('legacy-api-token-67890', 'scrape', True),
            ('read-only-token', 'read', True),
            ('read-only-token', 'write', False),
            ('read-only-token', 'scrape', False),
        ]
        
        for token_name, permission, expected in test_cases:
            token_info = AccessControlManager.API_TOKENS[token_name]
            has_permission = AccessControlManager.check_permission(token_info, permission)
            self.assertEqual(
                has_permission, expected,
                f"{token_name} permission '{permission}' should be {expected}"
            )
            print(f"✓ {token_info['name']}: {permission} = {expected}")
        
        print("✓ Token permission matrix verified")


def run_owasp_compliance_tests():
    """
    Run all OWASP compliance tests and generate report
    """
    print("=" * 80)
    print("OWASP COMPLIANCE TEST SUITE FOR JURAGAN MATERIAL MODULE")
    print("=" * 80)
    print("\nTesting compliance with:")
    print("- A01:2021 – Broken Access Control")
    print("=" * 80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestA01BrokenAccessControl))
    suite.addTests(loader.loadTestsFromTestCase(TestResourceLimitEnforcement))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegratedSecurityScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ ALL OWASP COMPLIANCE TESTS PASSED")
        print("✓ Juragan Material module meets OWASP A01 standards")
    else:
        print("\n✗ SOME TESTS FAILED")
        print("✗ Review failures and fix security issues")
    
    print("=" * 80)
    
    return result


if __name__ == '__main__':
    run_owasp_compliance_tests()
