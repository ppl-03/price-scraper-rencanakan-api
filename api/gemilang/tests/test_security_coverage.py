"""
Tests for security.py to achieve 100% coverage
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from django.http import HttpRequest, JsonResponse
from django.test import TestCase
import time


class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter class"""
    
    def setUp(self):
        """Set up test fixtures"""
        from api.gemilang.security import RateLimiter
        self.limiter = RateLimiter()
    
    def test_clean_old_requests(self):
        """Test _clean_old_requests removes old requests"""
        client_id = "test_client"
        current_time = time.time()
        
        # Add old and new requests
        self.limiter.requests[client_id] = [
            current_time - 100,  # Old
            current_time - 10,   # Recent
            current_time         # Current
        ]
        
        self.limiter._clean_old_requests(client_id, 60)
        
        # Only recent requests should remain
        self.assertEqual(len(self.limiter.requests[client_id]), 2)
    
    def test_is_blocked_returns_true_when_blocked(self):
        """Test is_blocked returns True for blocked clients"""
        client_id = "blocked_client"
        self.limiter.block_client(client_id, 300)
        
        self.assertTrue(self.limiter.is_blocked(client_id))
    
    def test_is_blocked_removes_expired_blocks(self):
        """Test is_blocked removes expired blocks"""
        client_id = "expired_block"
        self.limiter.blocked_ips[client_id] = time.time() - 10  # Expired
        
        self.assertFalse(self.limiter.is_blocked(client_id))
        self.assertNotIn(client_id, self.limiter.blocked_ips)
    
    def test_check_rate_limit_allows_under_limit(self):
        """Test check_rate_limit allows requests under limit"""
        is_allowed, msg = self.limiter.check_rate_limit("client1", max_requests=10, window_seconds=60)
        
        self.assertTrue(is_allowed)
        self.assertIsNone(msg)
    
    def test_check_rate_limit_blocks_over_limit(self):
        """Test check_rate_limit blocks requests over limit"""
        client_id = "spammer"
        
        # Make max_requests
        for _ in range(5):
            self.limiter.check_rate_limit(client_id, max_requests=5, window_seconds=60)
        
        # Next request should be blocked
        is_allowed, msg = self.limiter.check_rate_limit(client_id, max_requests=5, window_seconds=60)
        
        self.assertFalse(is_allowed)
        self.assertIn("Rate limit exceeded", msg)
    
    def test_check_rate_limit_without_blocking(self):
        """Test check_rate_limit without auto-blocking"""
        client_id = "no_block_test"
        
        # Make max_requests
        for _ in range(5):
            self.limiter.check_rate_limit(client_id, max_requests=5, window_seconds=60, block_on_violation=False)
        
        # Should return False but not block
        is_allowed, msg = self.limiter.check_rate_limit(client_id, max_requests=5, window_seconds=60, block_on_violation=False)
        
        self.assertFalse(is_allowed)
        self.assertFalse(self.limiter.is_blocked(client_id))


class TestAccessControlManager(TestCase):
    """Test AccessControlManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        from api.gemilang.security import AccessControlManager
        self.manager = AccessControlManager
        self.request = Mock(spec=HttpRequest)
        self.request.META = {'REMOTE_ADDR': '127.0.0.1'}
    
    def test_validate_token_missing(self):
        """Test validate_token with missing token"""
        self.request.headers = {}
        
        is_valid, msg, token_info = self.manager.validate_token(self.request)
        
        self.assertFalse(is_valid)
        self.assertEqual(msg, 'API token required')
        self.assertIsNone(token_info)
    
    def test_validate_token_invalid(self):
        """Test validate_token with invalid token"""
        self.request.headers = {'X-API-Token': 'invalid-token'}
        
        is_valid, msg, token_info = self.manager.validate_token(self.request)
        
        self.assertFalse(is_valid)
        self.assertEqual(msg, 'Invalid API token')
        self.assertIsNone(token_info)
    
    def test_validate_token_valid(self):
        """Test validate_token with valid token"""
        self.request.headers = {'X-API-Token': 'dev-token-12345'}
        
        is_valid, msg, token_info = self.manager.validate_token(self.request)
        
        self.assertTrue(is_valid)
        self.assertEqual(msg, '')
        self.assertIsNotNone(token_info)
    
    def test_validate_token_from_authorization_header(self):
        """Test validate_token extracts token from Authorization header"""
        self.request.headers = {'Authorization': 'Bearer dev-token-12345'}
        
        is_valid, msg, token_info = self.manager.validate_token(self.request)
        
        self.assertTrue(is_valid)
    
    def test_validate_token_with_ip_restriction(self):
        """Test validate_token with IP restriction"""
        # Temporarily modify token to have IP restriction
        from api.gemilang.security import AccessControlManager
        original_allowed_ips = AccessControlManager.API_TOKENS['dev-token-12345']['allowed_ips']
        AccessControlManager.API_TOKENS['dev-token-12345']['allowed_ips'] = ['192.168.1.1']
        
        self.request.headers = {'X-API-Token': 'dev-token-12345'}
        self.request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        is_valid, msg, token_info = self.manager.validate_token(self.request)
        
        self.assertFalse(is_valid)
        self.assertEqual(msg, 'IP not authorized for this token')
        
        # Restore original
        AccessControlManager.API_TOKENS['dev-token-12345']['allowed_ips'] = original_allowed_ips
    
    def test_check_permission_with_permission(self):
        """Test check_permission with valid permission"""
        token_info = {'name': 'Test Token', 'permissions': ['read', 'write']}
        
        has_permission = self.manager.check_permission(token_info, 'read')
        
        self.assertTrue(has_permission)
    
    def test_check_permission_without_permission(self):
        """Test check_permission without required permission"""
        token_info = {'name': 'Test Token', 'permissions': ['read']}
        
        has_permission = self.manager.check_permission(token_info, 'write')
        
        self.assertFalse(has_permission)


class TestInputValidator(unittest.TestCase):
    """Test InputValidator class"""
    
    def test_validate_keyword_valid(self):
        """Test validate_keyword with valid input"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, sanitized = InputValidator.validate_keyword('test-keyword_123')
        
        self.assertTrue(is_valid)
        self.assertEqual(msg, '')
        self.assertIsNotNone(sanitized)
    
    def test_validate_keyword_empty(self):
        """Test validate_keyword with empty string"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, sanitized = InputValidator.validate_keyword('')
        
        self.assertFalse(is_valid)
        self.assertIn('required', msg)
    
    def test_validate_keyword_too_long(self):
        """Test validate_keyword with too long input"""
        from api.gemilang.security import InputValidator
        
        long_keyword = 'a' * 101
        is_valid, msg, sanitized = InputValidator.validate_keyword(long_keyword, max_length=100)
        
        self.assertFalse(is_valid)
        self.assertIn('maximum length', msg)
    
    def test_validate_keyword_invalid_chars(self):
        """Test validate_keyword with invalid characters"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, sanitized = InputValidator.validate_keyword('test<script>')
        
        self.assertFalse(is_valid)
        self.assertIn('invalid characters', msg)
    
    def test_validate_keyword_sql_injection(self):
        """Test validate_keyword detects SQL injection"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, sanitized = InputValidator.validate_keyword("'; DROP TABLE users; --")
        
        self.assertFalse(is_valid)
    
    def test_validate_integer_valid(self):
        """Test validate_integer with valid input"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer(42, 'test_field')
        
        self.assertTrue(is_valid)
        self.assertEqual(value, 42)
    
    def test_validate_integer_string_input(self):
        """Test validate_integer with string input"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer('42', 'test_field')
        
        self.assertTrue(is_valid)
        self.assertEqual(value, 42)
    
    def test_validate_integer_invalid_string(self):
        """Test validate_integer with invalid string"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer('abc', 'test_field')
        
        self.assertFalse(is_valid)
        self.assertIn('valid integer', msg)
    
    def test_validate_integer_with_min_max(self):
        """Test validate_integer with range validation"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer(50, 'test_field', min_value=1, max_value=100)
        
        self.assertTrue(is_valid)
        self.assertEqual(value, 50)
    
    def test_validate_integer_below_min(self):
        """Test validate_integer below minimum"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer(0, 'test_field', min_value=1)
        
        self.assertFalse(is_valid)
        self.assertIn('at least', msg)
    
    def test_validate_integer_above_max(self):
        """Test validate_integer above maximum"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer(101, 'test_field', max_value=100)
        
        self.assertFalse(is_valid)
        self.assertIn('at most', msg)
    
    def test_validate_boolean_true_values(self):
        """Test validate_boolean with true values"""
        from api.gemilang.security import InputValidator
        
        for val in [True, 'true', '1', 'yes']:
            is_valid, msg, result = InputValidator.validate_boolean(val, 'test_field')
            self.assertTrue(is_valid)
            self.assertTrue(result)
    
    def test_validate_boolean_false_values(self):
        """Test validate_boolean with false values"""
        from api.gemilang.security import InputValidator
        
        for val in [False, 'false', '0', 'no']:
            is_valid, msg, result = InputValidator.validate_boolean(val, 'test_field')
            self.assertTrue(is_valid)
            self.assertFalse(result)
    
    def test_validate_boolean_none(self):
        """Test validate_boolean with None"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, result = InputValidator.validate_boolean(None, 'test_field')
        
        self.assertTrue(is_valid)
        self.assertIsNone(result)
    
    def test_validate_boolean_empty_string(self):
        """Test validate_boolean with empty string"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, result = InputValidator.validate_boolean('', 'test_field')
        
        self.assertFalse(is_valid)
        self.assertIn('boolean', msg)
    
    def test_validate_boolean_invalid(self):
        """Test validate_boolean with invalid value"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, result = InputValidator.validate_boolean('invalid', 'test_field')
        
        self.assertFalse(is_valid)
    
    def test_sanitize_for_database(self):
        """Test sanitize_for_database removes dangerous chars"""
        from api.gemilang.security import InputValidator
        
        data = {'name': 'test\x00value', 'price': 100}
        sanitized = InputValidator.sanitize_for_database(data)
        
        self.assertNotIn('\x00', sanitized['name'])
        self.assertEqual(sanitized['price'], 100)


class TestDatabaseQueryValidator(unittest.TestCase):
    """Test DatabaseQueryValidator class"""
    
    def test_validate_table_name_valid(self):
        """Test validate_table_name with valid table"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid = DatabaseQueryValidator.validate_table_name('gemilang_products')
        
        self.assertTrue(is_valid)
    
    def test_validate_table_name_invalid(self):
        """Test validate_table_name with invalid table"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid = DatabaseQueryValidator.validate_table_name('malicious_table')
        
        self.assertFalse(is_valid)
    
    def test_validate_column_name_valid(self):
        """Test validate_column_name with valid column"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid = DatabaseQueryValidator.validate_column_name('name')
        
        self.assertTrue(is_valid)
    
    def test_validate_column_name_invalid(self):
        """Test validate_column_name with invalid column"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid = DatabaseQueryValidator.validate_column_name('malicious_column')
        
        self.assertFalse(is_valid)
    
    def test_build_safe_query_select(self):
        """Test build_safe_query for SELECT"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid, msg, query = DatabaseQueryValidator.build_safe_query(
            'SELECT', 'gemilang_products', ['name', 'price']
        )
        
        self.assertTrue(is_valid)
        self.assertIn('SELECT name, price', query)
    
    def test_build_safe_query_invalid_operation(self):
        """Test build_safe_query with invalid operation"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid, msg, query = DatabaseQueryValidator.build_safe_query(
            'MALICIOUS', 'gemilang_products', ['name']
        )
        
        self.assertFalse(is_valid)
        self.assertIn('Invalid operation', msg)
    
    def test_build_safe_query_invalid_table(self):
        """Test build_safe_query with invalid table"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid, msg, query = DatabaseQueryValidator.build_safe_query(
            'SELECT', 'bad_table', ['name']
        )
        
        self.assertFalse(is_valid)
        self.assertIn('Invalid table', msg)
    
    def test_build_safe_query_invalid_column(self):
        """Test build_safe_query with invalid column"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid, msg, query = DatabaseQueryValidator.build_safe_query(
            'SELECT', 'gemilang_products', ['bad_column']
        )
        
        self.assertFalse(is_valid)
        self.assertIn('Invalid column', msg)


class TestSecurityDesignPatterns(unittest.TestCase):
    """Test SecurityDesignPatterns class"""
    
    def test_validate_price_field_valid(self):
        """Test _validate_price_field with valid price"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_price_field(99.99)
        
        self.assertTrue(is_valid)
    
    def test_validate_price_field_negative(self):
        """Test _validate_price_field with negative price"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_price_field(-10)
        
        self.assertFalse(is_valid)
        self.assertIn('positive', msg)
    
    def test_validate_price_field_too_large(self):
        """Test _validate_price_field with unreasonably large price"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_price_field(2000000000)
        
        self.assertFalse(is_valid)
        self.assertIn('exceeds', msg)
    
    def test_validate_name_field_valid(self):
        """Test _validate_name_field with valid name"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_name_field('Valid Product Name')
        
        self.assertTrue(is_valid)
    
    def test_validate_name_field_too_long(self):
        """Test _validate_name_field with too long name"""
        from api.gemilang.security import SecurityDesignPatterns
        
        long_name = 'a' * 501
        is_valid, msg = SecurityDesignPatterns._validate_name_field(long_name)
        
        self.assertFalse(is_valid)
        self.assertIn('too long', msg)
    
    def test_validate_name_field_too_short(self):
        """Test _validate_name_field with too short name"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_name_field('a')
        
        self.assertFalse(is_valid)
        self.assertIn('too short', msg)
    
    def test_validate_url_field_valid(self):
        """Test _validate_url_field with valid HTTPS URL"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_url_field('https://example.com/product')
        
        self.assertTrue(is_valid)
    
    def test_validate_url_field_not_https(self):
        """Test _validate_url_field rejects non-HTTPS"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_url_field('http://example.com')
        
        self.assertFalse(is_valid)
        self.assertIn('HTTPS', msg)
    
    def test_validate_url_field_localhost_ssrf(self):
        """Test _validate_url_field detects localhost SSRF"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_url_field('https://localhost/admin')
        
        self.assertFalse(is_valid)
        self.assertEqual(msg, 'Invalid URL')
    
    def test_validate_url_field_127_ssrf(self):
        """Test _validate_url_field detects 127.0.0.1 SSRF"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_url_field('https://127.0.0.1/admin')
        
        self.assertFalse(is_valid)
    
    def test_validate_url_field_0000_ssrf(self):
        """Test _validate_url_field detects 0.0.0.0 SSRF"""
        from api.gemilang.security import SecurityDesignPatterns
        
        is_valid, msg = SecurityDesignPatterns._validate_url_field('https://0.0.0.0/admin')
        
        self.assertFalse(is_valid)
    
    def test_validate_business_logic_valid_data(self):
        """Test validate_business_logic with valid data"""
        from api.gemilang.security import SecurityDesignPatterns
        
        data = {
            'price': 100,
            'name': 'Valid Product',
            'url': 'https://example.com/product'
        }
        
        is_valid, msg = SecurityDesignPatterns.validate_business_logic(data)
        
        self.assertTrue(is_valid)
    
    def test_validate_business_logic_invalid_price(self):
        """Test validate_business_logic with invalid price"""
        from api.gemilang.security import SecurityDesignPatterns
        
        data = {'price': -10}
        
        is_valid, msg = SecurityDesignPatterns.validate_business_logic(data)
        
        self.assertFalse(is_valid)
    
    def test_validate_business_logic_invalid_name(self):
        """Test validate_business_logic with invalid name"""
        from api.gemilang.security import SecurityDesignPatterns
        
        data = {'name': 'a'}
        
        is_valid, msg = SecurityDesignPatterns.validate_business_logic(data)
        
        self.assertFalse(is_valid)
    
    def test_validate_business_logic_invalid_url(self):
        """Test validate_business_logic with invalid URL"""
        from api.gemilang.security import SecurityDesignPatterns
        
        data = {'url': 'http://example.com'}
        
        is_valid, msg = SecurityDesignPatterns.validate_business_logic(data)
        
        self.assertFalse(is_valid)
    
    def test_enforce_resource_limits_valid(self):
        """Test enforce_resource_limits with valid request"""
        from api.gemilang.security import SecurityDesignPatterns
        
        request = Mock()
        request.GET = {'limit': '50'}
        
        is_valid, msg = SecurityDesignPatterns.enforce_resource_limits(request)
        
        self.assertTrue(is_valid)
    
    def test_enforce_resource_limits_exceeds_max(self):
        """Test enforce_resource_limits with exceeded limit"""
        from api.gemilang.security import SecurityDesignPatterns
        
        request = Mock()
        request.GET = {'limit': '200'}
        
        is_valid, msg = SecurityDesignPatterns.enforce_resource_limits(request, max_page_size=100)
        
        self.assertFalse(is_valid)
        self.assertIn('exceeds', msg)
    
    def test_enforce_resource_limits_invalid_limit(self):
        """Test enforce_resource_limits with invalid limit"""
        from api.gemilang.security import SecurityDesignPatterns
        
        request = Mock()
        request.GET = {'limit': 'abc'}
        
        is_valid, msg = SecurityDesignPatterns.enforce_resource_limits(request)
        
        self.assertFalse(is_valid)
        self.assertIn('Invalid limit', msg)
    
    def test_enforce_resource_limits_too_many_params(self):
        """Test enforce_resource_limits with too many query params"""
        from api.gemilang.security import SecurityDesignPatterns
        
        request = Mock()
        request.GET = {f'param{i}': 'value' for i in range(25)}
        
        is_valid, msg = SecurityDesignPatterns.enforce_resource_limits(request)
        
        self.assertFalse(is_valid)
        self.assertIn('Too many', msg)


class TestSecurityDecorators(TestCase):
    """Test security decorators"""
    
    def test_require_api_token_valid(self):
        """Test require_api_token with valid token"""
        from api.gemilang.security import require_api_token, rate_limiter
        
        @require_api_token()
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = Mock()
        request.headers = {'X-API-Token': 'dev-token-12345'}
        request.META = {'REMOTE_ADDR': '192.168.1.100'}  # Different IP to avoid rate limit from other tests
        request.path = '/test-unique'  # Different path
        
        # Clear any existing rate limits for this client
        client_id = '192.168.1.100:/test-unique'
        if client_id in rate_limiter.requests:
            rate_limiter.requests[client_id] = []
        if client_id in rate_limiter.blocked_ips:
            del rate_limiter.blocked_ips[client_id]
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_require_api_token_invalid(self):
        """Test require_api_token with invalid token"""
        from api.gemilang.security import require_api_token
        
        @require_api_token()
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = Mock()
        request.headers = {'X-API-Token': 'invalid'}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.path = '/test'
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 401)
    
    def test_require_api_token_insufficient_permission(self):
        """Test require_api_token with insufficient permission"""
        from api.gemilang.security import require_api_token
        
        @require_api_token(required_permission='admin')
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = Mock()
        request.headers = {'X-API-Token': 'read-only-token'}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.path = '/test'
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 403)
    
    def test_require_api_token_rate_limited(self):
        """Test require_api_token with rate limit exceeded"""
        from api.gemilang.security import require_api_token, rate_limiter
        
        @require_api_token()
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = Mock()
        request.headers = {'X-API-Token': 'dev-token-12345'}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.path = '/test'
        
        # Block the client
        rate_limiter.block_client('127.0.0.1:/test', 300)
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 429)
    
    def test_validate_input_decorator_valid(self):
        """Test validate_input decorator with valid input"""
        from api.gemilang.security import validate_input, InputValidator
        
        @validate_input({
            'keyword': lambda x: InputValidator.validate_keyword(x or '', max_length=100)
        })
        def test_view(request):
            return JsonResponse({'keyword': request.validated_data['keyword']})
        
        request = Mock()
        request.method = 'GET'
        request.GET = {'keyword': 'test'}
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_validate_input_decorator_invalid(self):
        """Test validate_input decorator with invalid input"""
        from api.gemilang.security import validate_input, InputValidator
        
        @validate_input({
            'keyword': lambda x: InputValidator.validate_keyword(x or '', max_length=100)
        })
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = Mock()
        request.method = 'GET'
        request.GET = {'keyword': ''}
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
    
    def test_validate_input_decorator_post(self):
        """Test validate_input decorator with POST request"""
        from api.gemilang.security import validate_input, InputValidator
        import json
        
        @validate_input({
            'keyword': lambda x: InputValidator.validate_keyword(x or '', max_length=100)
        })
        def test_view(request):
            return JsonResponse({'keyword': request.validated_data['keyword']})
        
        request = Mock()
        request.method = 'POST'
        request.body = json.dumps({'keyword': 'test'}).encode()
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_validate_input_decorator_invalid_json(self):
        """Test validate_input decorator with invalid JSON"""
        from api.gemilang.security import validate_input
        
        @validate_input({})
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = Mock()
        request.method = 'POST'
        request.body = b'{invalid json'
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
    
    def test_enforce_resource_limits_decorator(self):
        """Test enforce_resource_limits decorator"""
        from api.gemilang.security import enforce_resource_limits
        
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = Mock()
        request.GET = {'limit': '50'}
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_enforce_resource_limits_decorator_fails(self):
        """Test enforce_resource_limits decorator fails on violation"""
        from api.gemilang.security import enforce_resource_limits
        
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'status': 'success'})
        
        request = Mock()
        request.GET = {'limit': '200'}
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)


class TestAccessControlLogging(TestCase):
    """Test access control logging functionality"""
    
    def test_log_access_attempt_success(self):
        """Test log_access_attempt with successful access"""
        from api.gemilang.security import AccessControlManager
        
        request = Mock()
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'Test Agent'
        }
        request.path = '/test'
        request.method = 'GET'
        
        # Should not raise exception
        AccessControlManager.log_access_attempt(request, True)
    
    def test_log_access_attempt_failure(self):
        """Test log_access_attempt with failed access"""
        from api.gemilang.security import AccessControlManager
        
        request = Mock()
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'Test Agent'
        }
        request.path = '/test'
        request.method = 'GET'
        
        # Should not raise exception
        AccessControlManager.log_access_attempt(request, False, 'Test reason')
    
    @patch('api.gemilang.security.cache')
    def test_check_for_attack_pattern_low_failures(self, mock_cache):
        """Test _check_for_attack_pattern with low failure count"""
        from api.gemilang.security import AccessControlManager
        
        mock_cache.get.return_value = 5
        
        # Should not raise exception
        AccessControlManager._check_for_attack_pattern('127.0.0.1')
        
        mock_cache.set.assert_called_once()
    
    @patch('api.gemilang.security.cache')
    def test_check_for_attack_pattern_high_failures(self, mock_cache):
        """Test _check_for_attack_pattern with high failure count"""
        from api.gemilang.security import AccessControlManager
        
        mock_cache.get.return_value = 15
        
        # Should not raise exception, should log critical
        AccessControlManager._check_for_attack_pattern('192.168.1.1')
        
        mock_cache.set.assert_called_once()


class TestHelperFunctions(TestCase):
    """Test helper functions"""
    
    def test_get_request_data_get(self):
        """Test _get_request_data with GET request"""
        from api.gemilang.security import _get_request_data
        
        request = Mock()
        request.method = 'GET'
        request.GET = {'key': 'value'}
        
        data, error = _get_request_data(request)
        
        self.assertEqual(data['key'], 'value')
        self.assertIsNone(error)
    
    def test_get_request_data_post(self):
        """Test _get_request_data with POST request"""
        from api.gemilang.security import _get_request_data
        import json
        
        request = Mock()
        request.method = 'POST'
        request.body = json.dumps({'key': 'value'}).encode()
        
        data, error = _get_request_data(request)
        
        self.assertEqual(data['key'], 'value')
        self.assertIsNone(error)
    
    def test_get_request_data_empty_body(self):
        """Test _get_request_data with empty body"""
        from api.gemilang.security import _get_request_data
        
        request = Mock()
        request.method = 'POST'
        request.body = b''
        
        data, error = _get_request_data(request)
        
        self.assertEqual(data, {})
        self.assertIsNone(error)
    
    def test_validate_fields(self):
        """Test _validate_fields helper"""
        from api.gemilang.security import _validate_fields, InputValidator
        
        validators = {
            'keyword': lambda x: InputValidator.validate_keyword(x or '', max_length=100)
        }
        data_source = {'keyword': 'test'}
        
        errors, validated = _validate_fields(validators, data_source)
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(validated['keyword'], 'test')


class TestAdditionalCoverage(TestCase):
    """Additional tests to achieve 100% coverage"""
    
    def test_validate_token_with_expires_set(self):
        """Test validate_token when expires field is set"""
        from api.gemilang.security import AccessControlManager
        
        # Temporarily add expires to a token
        original_expires = AccessControlManager.API_TOKENS['dev-token-12345'].get('expires')
        AccessControlManager.API_TOKENS['dev-token-12345']['expires'] = '2025-12-31'
        
        request = Mock()
        request.headers = {'X-API-Token': 'dev-token-12345'}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        is_valid, msg, token_info = AccessControlManager.validate_token(request)
        
        # Should still be valid (expiration check is not implemented yet, just passes)
        self.assertTrue(is_valid)
        
        # Restore original
        if original_expires is None:
            AccessControlManager.API_TOKENS['dev-token-12345']['expires'] = None
    
    def test_validate_keyword_whitespace_stripped(self):
        """Test validate_keyword strips whitespace but fails if result is empty"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, sanitized = InputValidator.validate_keyword('   ')
        
        self.assertFalse(is_valid)
        self.assertIn('cannot be empty', msg)
    
    def test_validate_integer_with_none(self):
        """Test validate_integer with None value"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer(None, 'test_field')
        
        self.assertFalse(is_valid)
        self.assertIn('required', msg)
    
    def test_validate_integer_non_numeric_string(self):
        """Test validate_integer with non-numeric string"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer('12abc', 'test_field')
        
        self.assertFalse(is_valid)
        self.assertIn('valid integer', msg)
    
    def test_validate_integer_with_non_int_non_string(self):
        """Test validate_integer with non-int non-string type"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_integer(12.5, 'test_field')
        
        self.assertFalse(is_valid)
        self.assertIn('must be an integer', msg)
    
    def test_validate_boolean_with_non_boolean_non_string(self):
        """Test validate_boolean with non-boolean non-string type"""
        from api.gemilang.security import InputValidator
        
        is_valid, msg, value = InputValidator.validate_boolean(123, 'test_field')
        
        self.assertFalse(is_valid)
        self.assertIn('boolean', msg)
    
    def test_detect_sql_injection_no_match(self):
        """Test _detect_sql_injection returns False for safe input"""
        from api.gemilang.security import InputValidator
        
        result = InputValidator._detect_sql_injection('safe keyword')
        
        self.assertFalse(result)
    
    def test_build_safe_query_with_where_clause(self):
        """Test build_safe_query with where clause"""
        from api.gemilang.security import DatabaseQueryValidator
        
        is_valid, msg, query = DatabaseQueryValidator.build_safe_query(
            'SELECT',
            'gemilang_products',
            ['name', 'price'],
            where_clause={'id': 1, 'name': 'test'}
        )
        
        self.assertTrue(is_valid)
        self.assertIn('WHERE', query)
        self.assertIn('id = %s', query)
        self.assertIn('name = %s', query)
    
    def test_sanitize_for_database_with_long_string(self):
        """Test sanitize_for_database truncates long strings"""
        from api.gemilang.security import InputValidator
        
        long_string = 'a' * 2000
        data = {'field': long_string}
        
        sanitized = InputValidator.sanitize_for_database(data)
        
        self.assertLessEqual(len(sanitized['field']), 1000)
    
    def test_sanitize_for_database_with_html(self):
        """Test sanitize_for_database removes HTML"""
        from api.gemilang.security import InputValidator
        
        data = {'field': '<script>alert("xss")</script>'}
        
        sanitized = InputValidator.sanitize_for_database(data)
        
        self.assertNotIn('<script>', sanitized['field'])
    
    def test_validate_keyword_with_sql_injection_patterns(self):
        """Test various SQL injection patterns are detected"""
        from api.gemilang.security import InputValidator
        
        sql_patterns = [
            "test' OR '1'='1",
            "test; DROP TABLE users",
            "test-- comment",
            "test/* comment */",
            'test" AND "1"="1'
        ]
        
        for pattern in sql_patterns:
            is_valid, msg, sanitized = InputValidator.validate_keyword(pattern)
            self.assertFalse(is_valid, f"Should reject SQL injection: {pattern}")
    
    def test_validate_input_with_none_validator_result(self):
        """Test _validate_fields when validator returns None for sanitized_value"""
        from api.gemilang.security import _validate_fields
        
        def mock_validator(x):
            return (True, "", None)  # Valid but sanitized_value is None
        
        validators = {'field': mock_validator}
        data_source = {'field': 'value'}
        
        errors, validated = _validate_fields(validators, data_source)
        
        self.assertEqual(len(errors), 0)
        # None values should not be added to validated_data
        self.assertNotIn('field', validated)
    
    def test_validate_integer_string_causes_value_error(self):
        """Test validate_integer with string that matches NUMERIC_PATTERN but causes ValueError"""
        from api.gemilang.security import InputValidator
        from unittest.mock import patch
        
        # Mock int() to raise ValueError even for valid numeric strings
        with patch('builtins.int', side_effect=ValueError("Test error")):
            is_valid, msg, value = InputValidator.validate_integer('123', 'test_field')
            
            self.assertFalse(is_valid)
            self.assertIn('valid integer', msg)
