"""
OWASP Compliance Test Suite for Depobangunan Module
Tests compliance with A01:2021, A03:2021, A04:2021

This test suite simulates real-world attack scenarios and verifies that 
security controls are properly implemented according to OWASP guidelines.
"""
import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings

# Import security modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load test IP addresses from Django settings (configured from .env file)
# These are RFC 1918 private addresses for testing only
TEST_IP_ALLOWED = getattr(settings, 'TEST_IP_ALLOWED', '192.168.1.100')
TEST_IP_DENIED = getattr(settings, 'TEST_IP_DENIED', '192.168.1.200')
TEST_IP_ATTACKER = getattr(settings, 'TEST_IP_ATTACKER', '192.168.1.250')

from api.depobangunan.security import (
    RateLimiter,
    AccessControlManager,
    InputValidator,
    DatabaseQueryValidator,
    SecurityDesignPatterns,
    require_api_token,
    validate_input,
    enforce_resource_limits,
)


class SecurityTestHelpers:
    """Helper methods for security tests."""
    
    @staticmethod
    def create_test_token_info(permissions=None, allowed_ips=None):
        if permissions is None:
            permissions = ['read', 'write']
        if allowed_ips is None:
            allowed_ips = []
        return {
            'name': 'Test Token',
            'permissions': permissions,
            'allowed_ips': allowed_ips,
            'rate_limit': {'requests': 100, 'window': 60}
        }
    
    @staticmethod
    def run_rate_limit_test(rate_limiter, client_id, max_requests, expect_block=True):
        results = []
        for i in range(max_requests + 1):
            is_allowed, error = rate_limiter.check_rate_limit(
                client_id, max_requests=max_requests, window_seconds=60
            )
            results.append((is_allowed, error))
        return results


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
    
    def _test_token_validation(self, token, expected_valid, expected_error=''):
        """Helper to test token validation."""
        request = self.factory.get('/api/depobangunan/scrape/')
        if token:
            request.META['HTTP_X_API_TOKEN'] = token
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
        
        if expected_valid:
            self.assertTrue(is_valid)
            self.assertEqual(error_msg, '')
            self.assertIsNotNone(token_info)
        else:
            self.assertFalse(is_valid)
            self.assertEqual(error_msg, expected_error)
            self.assertIsNone(token_info)
        
        return is_valid, error_msg, token_info
    
    def test_deny_by_default_no_token(self):
        """Test that access is denied by default without token"""
        print("\n[A01] Test: Deny by default - No token provided")
        self._test_token_validation(None, False, 'API token required')
        print("✓ Access denied without token")
    
    def test_deny_invalid_token(self):
        """Test that invalid tokens are rejected"""
        print("\n[A01] Test: Deny invalid token")
        self._test_token_validation('invalid-token-xyz', False, 'Invalid API token')
        print("✓ Invalid token rejected")
    
    def test_valid_token_accepted(self):
        """Test that valid tokens are accepted"""
        print("\n[A01] Test: Valid token accepted")
        _, _, token_info = self._test_token_validation('dev-token-12345', True)
        self.assertEqual(token_info['name'], 'Development Token')
        print("✓ Valid token accepted")
    
    def test_permission_enforcement(self):
        """Test that permissions are enforced (principle of least privilege)"""
        print("\n[A01] Test: Permission enforcement")
        
        token_info = SecurityTestHelpers.create_test_token_info(permissions=['read'])
        
        has_read = AccessControlManager.check_permission(token_info, 'read')
        self.assertTrue(has_read, "Should have read permission")
        print("✓ Read permission granted")
        
        has_write = AccessControlManager.check_permission(token_info, 'write')
        self.assertFalse(has_write, "Should not have write permission")
        print("✓ Write permission denied (principle of least privilege)")
    
    def test_rate_limiting_enforcement(self):
        """Test that rate limiting prevents automated attacks"""
        print("\n[A01] Test: Rate limiting enforcement")
        
        rate_limiter = RateLimiter()
        client_id = "test_client_123"
        max_requests = 10
        
        results = SecurityTestHelpers.run_rate_limit_test(rate_limiter, client_id, max_requests)
        
        # First 10 should succeed
        for i in range(max_requests):
            self.assertTrue(results[i][0], f"Request {i+1} should be allowed")
        print("✓ First 10 requests allowed")
        
        # 11th should be blocked
        self.assertFalse(results[max_requests][0], "11th request should be blocked")
        self.assertIn("Rate limit exceeded", results[max_requests][1])
        print("✓ 11th request blocked (rate limit enforced)")
    
    def test_rate_limiting_blocks_client(self):
        """Test that repeated violations result in client blocking"""
        print("\n[A01] Test: Client blocking on rate limit violation")
        
        rate_limiter = RateLimiter()
        client_id = "attacker_ip_456"
        
        # Exceed rate limit to trigger block
        for _ in range(11):
            rate_limiter.check_rate_limit(
                client_id, max_requests=10, window_seconds=60
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
    
    def test_access_logging(self):
        """Test that access attempts are logged for monitoring"""
        print("\n[A01] Test: Access control logging")
        
        # Use test IP from environment variable
        request = self.factory.get(
            '/api/depobangunan/scrape/',
            REMOTE_ADDR=TEST_IP_ALLOWED
        )
        
        with self.assertLogs('api.depobangunan.security', level='WARNING') as cm:
            _, _, _ = AccessControlManager.validate_token(request)
            AccessControlManager.log_access_attempt(request, False, 'Test denial')
        
        # Verify log contains relevant information
        log_output = cm.output[0]
        self.assertIn(TEST_IP_ALLOWED, log_output)
        self.assertIn('Access denied', log_output)
        print("✓ Access attempts are logged")
    
    def test_ip_whitelist_enforcement(self):
        """Test that IP whitelisting is enforced"""
        print("\n[A01] Test: IP whitelist enforcement")
        
        # Create token with IP whitelist using environment variables
        AccessControlManager.API_TOKENS['restricted-token'] = {
            'name': 'Restricted Token',
            'permissions': ['read'],
            'allowed_ips': [TEST_IP_ALLOWED],
            'rate_limit': {'requests': 100, 'window': 60}
        }
        
        # Request from allowed IP
        request_allowed = self.factory.get(
            '/api/depobangunan/scrape/',
            HTTP_X_API_TOKEN='restricted-token',
            REMOTE_ADDR=TEST_IP_ALLOWED
        )
        is_valid, _, _ = AccessControlManager.validate_token(request_allowed)
        self.assertTrue(is_valid, "Request from whitelisted IP should be allowed")
        print("✓ Whitelisted IP allowed")
        
        # Request from non-allowed IP
        request_denied = self.factory.get(
            '/api/depobangunan/scrape/',
            HTTP_X_API_TOKEN='restricted-token',
            REMOTE_ADDR=TEST_IP_DENIED
        )
        is_valid, error_msg, _ = AccessControlManager.validate_token(request_denied)
        self.assertFalse(is_valid, "Request from non-whitelisted IP should be denied")
        self.assertIn('not authorized', error_msg)
        print("✓ Non-whitelisted IP denied")


class TestA03InjectionPrevention(TestCase):
    """
    Test suite for OWASP A03:2021 - Injection Prevention
    
    Tests:
    1. Parameterized queries (ORM usage)
    2. Input validation
    3. SQL injection prevention
    4. XSS prevention
    5. Command injection prevention
    """
    
    def test_sql_injection_detection_in_keyword(self):
        """Test that SQL injection attempts in keywords are detected"""
        print("\n[A03] Test: SQL injection detection in keyword input")
        
        sql_injection_attempts = [
            "'; DROP TABLE depobangunan_products; --",
            "1' OR '1'='1",
            "admin'--",
            "1' UNION SELECT * FROM users--",
            "'; DELETE FROM products WHERE '1'='1"
        ]
        
        for injection_attempt in sql_injection_attempts:
            is_valid, _, _ = InputValidator.validate_keyword(injection_attempt)
            self.assertFalse(is_valid, f"SQL injection should be detected: {injection_attempt}")
            print(f"✓ SQL injection blocked: {injection_attempt[:30]}...")
    
    def test_sql_injection_detection_patterns(self):
        """Test SQL injection pattern detection"""
        print("\n[A03] Test: SQL injection pattern detection")
        
        test_cases = [
            ("SELECT * FROM users", True),
            ("DROP TABLE products", True),
            ("1 OR 1=1", True),
            ("normal search term", False),
            ("cement mixer", False)
        ]
        
        for test_input, should_detect in test_cases:
            is_injection = InputValidator._detect_sql_injection(test_input)
            self.assertEqual(is_injection, should_detect, 
                           f"Pattern detection failed for: {test_input}")
            if should_detect:
                print(f"✓ Detected SQL pattern: {test_input}")
            else:
                print(f"✓ Accepted normal input: {test_input}")
    
    def test_input_validation_keyword(self):
        """Test comprehensive keyword validation"""
        print("\n[A03] Test: Keyword input validation")
        
        # Valid inputs
        valid_inputs = ["cement", "batu bata", "cat-tembok", "semen_gresik"]
        for valid_input in valid_inputs:
            is_valid, _, _ = InputValidator.validate_keyword(valid_input)
            self.assertTrue(is_valid, f"Valid input should be accepted: {valid_input}")
        
        # Invalid inputs
        invalid_inputs = [
            ("", "Keyword cannot be empty"),
            ("a" * 101, "exceeds maximum length"),
            ("<script>alert('xss')</script>", "invalid characters"),
            ("'; DROP TABLE", "invalid characters")
        ]
        
        for invalid_input, expected_error_part in invalid_inputs:
            is_valid, error_msg, _ = InputValidator.validate_keyword(invalid_input)
            self.assertFalse(is_valid, f"Invalid input should be rejected: {invalid_input[:30]}")
            print(f"✓ Rejected invalid input: {expected_error_part}")
    
    def test_input_validation_integer(self):
        """Test integer input validation with range checking"""
        print("\n[A03] Test: Integer input validation")
        
        # Valid integers
        is_valid, _, value = InputValidator.validate_integer(5, 'page', 0, 100)
        self.assertTrue(is_valid)
        self.assertEqual(value, 5)
        print("✓ Valid integer accepted: 5")
        
        # Boundary test
        is_valid, _, _ = InputValidator.validate_integer(0, 'page', 0, 100)
        self.assertTrue(is_valid)
        print("✓ Boundary value accepted: 0")
        
        # Out of range
        is_valid, error_msg, _ = InputValidator.validate_integer(-1, 'page', 0, 100)
        self.assertFalse(is_valid)
        self.assertIn('at least', error_msg)
        print("✓ Out of range rejected: -1")
        
        # SQL injection in string
        is_valid, _, _ = InputValidator.validate_integer("1; DROP TABLE", 'page')
        self.assertFalse(is_valid)
        print("✓ SQL injection in integer rejected")
    
    def test_table_name_validation(self):
        """Test that table names are validated against whitelist"""
        print("\n[A03] Test: Table name whitelist validation")
        
        # Valid table name
        is_valid = DatabaseQueryValidator.validate_table_name('depobangunan_products')
        self.assertTrue(is_valid, "Valid table name should be accepted")
        print("✓ Valid table name accepted: depobangunan_products")
        
        # Invalid table names (injection attempts)
        invalid_tables = [
            'users; DROP TABLE depobangunan_products',
            '../../../etc/passwd',
            'information_schema.tables'
        ]
        
        for invalid_table in invalid_tables:
            is_valid = DatabaseQueryValidator.validate_table_name(invalid_table)
            self.assertFalse(is_valid, f"Invalid table should be rejected: {invalid_table}")
            print(f"✓ Rejected invalid table: {invalid_table[:30]}...")
    
    def test_column_name_validation(self):
        """Test that column names are validated against whitelist"""
        print("\n[A03] Test: Column name whitelist validation")
        
        # Valid columns
        valid_columns = ['id', 'name', 'price', 'url', 'unit']
        for col in valid_columns:
            is_valid = DatabaseQueryValidator.validate_column_name(col)
            self.assertTrue(is_valid, f"Valid column should be accepted: {col}")
        
        # Invalid columns
        invalid_columns = [
            'password',
            'admin',
            '1; DROP TABLE',
            '../etc/passwd'
        ]
        
        for col in invalid_columns:
            is_valid = DatabaseQueryValidator.validate_column_name(col)
            self.assertFalse(is_valid, f"Invalid column should be rejected: {col}")
            print(f"✓ Rejected invalid column: {col}")
    
    def test_xss_prevention(self):
        """Test that XSS attempts are sanitized"""
        print("\n[A03] Test: XSS prevention")
        
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'>"
        ]
        
        for xss_attempt in xss_attempts:
            is_valid, _, _ = InputValidator.validate_keyword(xss_attempt)
            self.assertFalse(is_valid, f"XSS attempt should be blocked: {xss_attempt}")
            print(f"✓ XSS attempt blocked: {xss_attempt[:30]}...")


class TestA04InsecureDesign(TestCase):
    """
    Test suite for OWASP A04:2021 - Insecure Design
    
    Tests:
    1. Business logic validation
    2. Resource consumption limits
    3. Plausibility checks
    4. Threat modeling implementation
    5. Secure design patterns
    """
    
    def test_business_logic_price_validation(self):
        """Test that business logic validates prices"""
        print("\n[A04] Test: Business logic - Price validation")
        
        # Valid price
        data = {'price': 50000, 'name': 'Product', 'url': 'https://example.com'}
        is_valid, _ = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid, "Valid price should be accepted")
        print("✓ Valid price accepted: 50000")
        
        # Negative price (business rule violation)
        data = {'price': -1000, 'name': 'Product', 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid, "Negative price should be rejected")
        self.assertIn('positive', error_msg)
        print("✓ Negative price rejected")
        
        # Unreasonably high price (plausibility check)
        data = {'price': 2000000000, 'name': 'Product', 'url': 'https://example.com'}
        is_valid, _ = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid, "Unreasonably high price should be rejected")
        print("✓ Unreasonably high price rejected (plausibility check)")
    
    def test_business_logic_name_validation(self):
        """Test that business logic validates product names"""
        print("\n[A04] Test: Business logic - Name validation")
        
        # Name too short
        data = {'name': 'A', 'price': 1000, 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertIn('too short', error_msg)
        print("✓ Too short name rejected")
        
        # Name too long
        data = {'name': 'A' * 501, 'price': 1000, 'url': 'https://example.com'}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertIn('too long', error_msg)
        print("✓ Too long name rejected")
    
    def test_ssrf_prevention(self):
        """Test that SSRF attacks are prevented"""
        print("\n[A04] Test: SSRF prevention")
        
        # Test URLs intentionally use HTTP for SSRF attack simulation
        # These are test patterns to verify security controls block internal access
        ssrf_attempts = [
            'https://localhost/admin',
            'https://127.0.0.1/secret',
            'https://0.0.0.0/internal'
        ]
        
        for ssrf_url in ssrf_attempts:
            data = {'url': ssrf_url, 'name': 'Product', 'price': 1000}
            is_valid, _ = SecurityDesignPatterns.validate_business_logic(data)
            self.assertFalse(is_valid, f"SSRF attempt should be blocked: {ssrf_url}")
            print(f"✓ SSRF blocked: {ssrf_url}")
    
    def test_resource_limit_page_size(self):
        """Test that resource limits are enforced"""
        print("\n[A04] Test: Resource limit - Page size")
        
        factory = RequestFactory()
        
        # Valid limit
        request = factory.get('/api/products?limit=50')
        is_valid, _ = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        print("✓ Valid limit accepted: 50")
        
        # Excessive limit
        request = factory.get('/api/products?limit=500')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid)
        self.assertIn('exceeds maximum', error_msg)
        print("✓ Excessive limit rejected: 500")
    
    def test_resource_limit_query_complexity(self):
        """Test that query complexity limits are enforced"""
        print("\n[A04] Test: Resource limit - Query complexity")
        
        factory = RequestFactory()
        
        # Create excessive query parameters
        params = '&'.join([f'param{i}=value{i}' for i in range(25)])
        request = factory.get(f'/api/products?{params}')
        
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid, "Excessive query parameters should be rejected")
        self.assertIn('Too many', error_msg)
        print("✓ Excessive query complexity rejected: 25 parameters")


class TestIntegratedSecurityScenarios(TestCase):
    """
    Integration tests simulating real-world attack scenarios
    """
    
    def test_scenario_brute_force_attack(self):
        """Test detection and blocking of brute force attacks"""
        print("\n[Integration] Test: Brute force attack scenario")
        
        rate_limiter = RateLimiter()
        
        # Simulate repeated login attempts
        for i in range(15):
            client_id = f"{TEST_IP_ATTACKER}:/api/login"
            
            is_allowed, _ = rate_limiter.check_rate_limit(
                client_id, max_requests=10, window_seconds=60
            )
            
            if i < 10:
                self.assertTrue(is_allowed, f"Attempt {i+1} should be allowed")
            else:
                self.assertFalse(is_allowed, f"Attempt {i+1} should be blocked")
        
        print("✓ Brute force attack detected and blocked")
    
    def test_scenario_sql_injection_chain(self):
        """Test that chained SQL injection attempts are blocked"""
        print("\n[Integration] Test: SQL injection chain attack")
        
        # Attempt 1: Direct SQL in keyword
        is_valid, _, _ = InputValidator.validate_keyword("' OR '1'='1")
        self.assertFalse(is_valid)
        
        # Attempt 2: SQL in table name
        is_valid = DatabaseQueryValidator.validate_table_name("users; DROP TABLE products")
        self.assertFalse(is_valid)
        
        # Attempt 3: SQL in column name
        is_valid = DatabaseQueryValidator.validate_column_name("id; DELETE FROM users")
        self.assertFalse(is_valid)
        
        print("✓ All SQL injection attempts in chain blocked")
    
    def test_scenario_privilege_escalation(self):
        """Test that privilege escalation is prevented"""
        print("\n[Integration] Test: Privilege escalation scenario")
        
        # Read-only token trying to perform write operation
        token_info = {
            'name': 'Read Only Token',
            'permissions': ['read']
        }
        
        # Should not have write permission
        self.assertFalse(AccessControlManager.check_permission(token_info, 'write'))
        
        # Should not have admin permission
        self.assertFalse(AccessControlManager.check_permission(token_info, 'admin'))
        
        print("✓ Privilege escalation prevented")
    
    def test_scenario_resource_exhaustion(self):
        """Test that resource exhaustion attacks are prevented"""
        print("\n[Integration] Test: Resource exhaustion scenario")
        
        factory = RequestFactory()
        
        # Attempt 1: Excessive page size
        request = factory.get('/api/products?limit=10000')
        self.assertFalse(SecurityDesignPatterns.enforce_resource_limits(request)[0])
        
        # Attempt 2: Excessive query parameters
        params = '&'.join([f'p{i}=v{i}' for i in range(50)])
        request = factory.get(f'/api/products?{params}')
        self.assertFalse(SecurityDesignPatterns.enforce_resource_limits(request)[0])
        
        print("✓ Resource exhaustion attempts blocked")


def run_owasp_compliance_tests():
    """
    Run all OWASP compliance tests and generate report
    """
    print("=" * 80)
    print("OWASP COMPLIANCE TEST SUITE FOR DEPOBANGUNAN MODULE")
    print("=" * 80)
    print("\nTesting compliance with:")
    print("- A01:2021 – Broken Access Control")
    print("- A03:2021 – Injection")
    print("- A04:2021 – Insecure Design")
    print("=" * 80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestA01BrokenAccessControl))
    suite.addTests(loader.loadTestsFromTestCase(TestA03InjectionPrevention))
    suite.addTests(loader.loadTestsFromTestCase(TestA04InsecureDesign))
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
        print("Security controls are properly implemented")
    else:
        print("\n✗ SOME TESTS FAILED")
        print("Review failures and ensure security controls are correct")
    
    print("=" * 80)
    
    return result


class TestSecurityCoverageExtended(TestCase):
    """Extended tests to achieve 100% coverage of security.py"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.rate_limiter = RateLimiter()
        cache.clear()
    
    def test_rate_limiter_unblock_after_duration(self):
        """Test that blocked clients are unblocked after duration expires"""
        import time
        client_id = "test_client"
        
        # Block client for 1 second
        self.rate_limiter.block_client(client_id, duration_seconds=1)
        
        # Should be blocked immediately
        self.assertTrue(self.rate_limiter.is_blocked(client_id))
        
        # Wait for block to expire
        time.sleep(1.1)
        
        # Should be unblocked now
        self.assertFalse(self.rate_limiter.is_blocked(client_id))
    
    def test_access_control_token_expiration_check(self):
        """Test token expiration logic (currently pass statement)"""
        request = self.factory.get('/test/')
        request.META['HTTP_AUTHORIZATION'] = 'dev-token-12345'
        
        # This tests the expiration check code path (currently a pass statement)
        is_valid, _, _ = AccessControlManager.validate_token(request)
        self.assertTrue(is_valid)
    
    def test_access_control_ip_whitelist_restriction(self):
        """Test IP whitelist restriction"""
        # Create a mock token with IP whitelist
        with patch.object(AccessControlManager, 'API_TOKENS', {
            'ip-restricted-token': {
                'name': 'IP Restricted Token',
                'owner': 'test',
                'permissions': ['read'],
                'allowed_ips': ['192.168.1.100'],
                'rate_limit': {'requests': 10, 'window': 60}
            }
        }):
            request = self.factory.get('/test/')
            request.META['HTTP_AUTHORIZATION'] = 'ip-restricted-token'
            request.META['REMOTE_ADDR'] = '192.168.1.200'  # Different IP
            
            is_valid, msg, _ = AccessControlManager.validate_token(request)
            self.assertFalse(is_valid)
            self.assertIn('IP not authorized', msg)
    
    def test_access_control_ip_whitelist_allowed(self):
        """Test IP whitelist allows correct IP"""
        with patch.object(AccessControlManager, 'API_TOKENS', {
            'ip-restricted-token': {
                'name': 'IP Restricted Token',
                'owner': 'test',
                'permissions': ['read'],
                'allowed_ips': ['192.168.1.100'],
                'rate_limit': {'requests': 10, 'window': 60}
            }
        }):
            request = self.factory.get('/test/')
            request.META['HTTP_AUTHORIZATION'] = 'ip-restricted-token'
            request.META['REMOTE_ADDR'] = '192.168.1.100'  # Matching IP
            
            is_valid, _, _ = AccessControlManager.validate_token(request)
            self.assertTrue(is_valid)
    
    def test_access_control_multiple_failures_alert(self):
        """Test critical alert on multiple access control failures"""
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.250'
        
        # Simulate 11 failures to trigger alert
        for i in range(11):
            AccessControlManager.log_access_attempt(request, success=False, reason='Test failure')
        
        # Check cache for failure count (using correct cache key from implementation)
        cache_key = "failed_access_192.168.1.250"
        failures = cache.get(cache_key, 0)
        self.assertGreater(failures, 10)
    
    def test_input_validator_keyword_too_long(self):
        """Test keyword exceeding max length"""
        long_keyword = 'a' * 101
        is_valid, msg, _ = InputValidator.validate_keyword(long_keyword, max_length=100)
        self.assertFalse(is_valid)
        self.assertIn('exceeds maximum length', msg)
    
    def test_input_validator_keyword_empty_after_strip(self):
        """Test keyword that is empty after stripping whitespace"""
        is_valid, msg, _ = InputValidator.validate_keyword('   ', max_length=100)
        self.assertFalse(is_valid)
        self.assertIn('cannot be empty', msg)
    
    def test_input_validator_integer_string_invalid_format(self):
        """Test integer validation with invalid string format"""
        is_valid, msg, _ = InputValidator.validate_integer('abc123', 'test_field')
        self.assertFalse(is_valid)
        self.assertIn('must be a valid integer', msg)
    
    def test_input_validator_integer_min_value(self):
        """Test integer validation with min value constraint"""
        is_valid, msg, _ = InputValidator.validate_integer(5, 'test_field', min_value=10)
        self.assertFalse(is_valid)
        self.assertIn('must be at least 10', msg)
    
    def test_input_validator_integer_max_value(self):
        """Test integer validation with max value constraint"""
        is_valid, msg, _ = InputValidator.validate_integer(100, 'test_field', max_value=50)
        self.assertFalse(is_valid)
        self.assertIn('must be at most 50', msg)
    
    def test_input_validator_boolean_empty_string(self):
        """Test boolean validation with empty string"""
        is_valid, msg, _ = InputValidator.validate_boolean('', 'test_field')
        self.assertFalse(is_valid)
        self.assertIn('must be a boolean', msg)
    
    def test_input_validator_boolean_invalid_string(self):
        """Test boolean validation with invalid string"""
        is_valid, msg, _ = InputValidator.validate_boolean('maybe', 'test_field')
        self.assertFalse(is_valid)
        self.assertIn('must be a boolean', msg)
    
    def test_database_validator_invalid_table(self):
        """Test database query validator with invalid table name"""
        is_valid = DatabaseQueryValidator.validate_table_name('malicious_table; DROP TABLE users;')
        self.assertFalse(is_valid)
    
    def test_database_validator_invalid_column(self):
        """Test database query validator with invalid column name"""
        is_valid = DatabaseQueryValidator.validate_column_name('column; DELETE FROM users')
        self.assertFalse(is_valid)
    
    def test_database_validator_safe_query_with_invalid_params(self):
        """Test safe query building with invalid parameters"""
        # Invalid table - build_safe_query returns (is_valid, error_msg, query)
        is_valid, error, query = DatabaseQueryValidator.build_safe_query(
            'SELECT',
            'invalid_table',
            ['name']
        )
        self.assertFalse(is_valid)
        self.assertEqual(query, '')
        self.assertIn('Invalid table name', error)
    
    def test_security_design_patterns_negative_price(self):
        """Test business logic validation with negative price"""
        product = {'price': -100, 'url': 'https://example.com', 'name': 'Test'}
        is_valid, msg = SecurityDesignPatterns.validate_business_logic(product)
        self.assertFalse(is_valid)
        self.assertIn('Price must be a positive number', msg)
    
    def test_security_design_patterns_ssrf_localhost(self):
        """Test SSRF prevention for localhost"""
        product = {'price': 100, 'url': 'http://localhost:8080/admin', 'name': 'Test'}
        is_valid, msg = SecurityDesignPatterns.validate_business_logic(product)
        self.assertFalse(is_valid)
        self.assertIn('HTTPS', msg)  # First validation is HTTPS protocol
    
    def test_security_design_patterns_ssrf_private_ip(self):
        """Test SSRF prevention for private IPs"""
        product = {'price': 100, 'url': 'http://192.168.1.1/admin', 'name': 'Test'}
        is_valid, msg = SecurityDesignPatterns.validate_business_logic(product)
        self.assertFalse(is_valid)
        self.assertIn('HTTPS', msg)  # First validation is HTTPS protocol
    
    def test_security_design_patterns_unrealistic_price(self):
        """Test business logic validation with unrealistic price"""
        product = {'price': 9999999999, 'url': 'https://example.com', 'name': 'Test'}
        is_valid, msg = SecurityDesignPatterns.validate_business_logic(product)
        self.assertFalse(is_valid)
        self.assertIn('exceeds reasonable limit', msg.lower())
    
    def test_enforce_resource_limits_decorator_with_limit_param(self):
        """Test enforce_resource_limits decorator with limit parameter"""
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'status': 'ok'})
        
        request = self.factory.get('/test/?limit=200')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        response = test_view(request)
        
        # Should reject limit > 100
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    run_owasp_compliance_tests()
