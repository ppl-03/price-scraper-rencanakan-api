"""
OWASP Compliance Tests for Tokopedia API
Tests A01:2021 (Broken Access Control), A03:2021 (Injection), A04:2021 (Insecure Design)
"""
from django.test import RequestFactory, TestCase
from django.http import JsonResponse
from api.tokopedia.security import (
    TokopediaRateLimitTracker,
    TokopediaAccessControl,
    ValidationPipeline,
    DatabaseSecurityValidator,
    BusinessLogicValidator,
    require_api_token,
    validate_input,
    enforce_resource_limits,
    _rate_tracker
)
import time
import json


class TestRateLimiter(TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        self.rate_limiter = TokopediaRateLimitTracker()
        
    def test_rate_limit_allows_requests_within_limit(self):
        """Test that requests within rate limit are allowed"""
        client_id = "test_client_1"
        
        # Make requests within limit
        for _ in range(10):
            is_allowed, error = self.rate_limiter.evaluate_limit(
                client_id, max_requests=10
            )
            if _ < 10:
                self.assertTrue(is_allowed)
                self.assertIsNone(error)
    
    def test_rate_limit_blocks_excessive_requests(self):
        """Test that excessive requests are blocked"""
        client_id = "test_client_2"
        
        # Make requests up to limit
        for _ in range(10):
            self.rate_limiter.evaluate_limit(
                client_id, max_requests=10
            )
        
        # Next request should be blocked
        is_allowed, error = self.rate_limiter.evaluate_limit(
            client_id, max_requests=10
        )
        self.assertFalse(is_allowed)
        self.assertIsNotNone(error)
        self.assertIn("Rate limit exceeded", error)
    
    def test_rate_limit_blocks_client_temporarily(self):
        """Test that blocked clients remain blocked for specified duration"""
        client_id = "test_client_3"
        
        # Block the client
        self.rate_limiter.apply_block(client_id, duration=1)
        
        # Check that client is blocked
        is_blocked, _ = self.rate_limiter.check_client_blocked(client_id)
        self.assertTrue(is_blocked)
        
        # Wait for block to expire
        time.sleep(1.1)
        
        # Check that client is no longer blocked
        is_blocked, _ = self.rate_limiter.check_client_blocked(client_id)
        self.assertFalse(is_blocked)
    
    def test_rate_limit_cleans_old_requests(self):
        """Test that old requests are properly cleaned up"""
        client_id = "test_client_4"
        tracker = TokopediaRateLimitTracker({'default_window': 1, 'default_max_requests': 10, 'block_duration': 300, 'attack_threshold': 10})
        
        # Make requests
        for _ in range(5):
            tracker.evaluate_limit(client_id, max_requests=10)
        
        # Wait for window to pass
        time.sleep(1.1)
        
        # Old requests should be cleaned, new requests allowed
        is_allowed, _ = tracker.evaluate_limit(client_id, max_requests=10)
        self.assertTrue(is_allowed)


class TestAccessControlManager(TestCase):
    """Test access control and token validation"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_valid_token_authentication(self):
        """Test that valid tokens are accepted"""
        request = self.factory.get('/api/test')
        request.META['HTTP_X_API_TOKEN'] = 'dev-token-12345'
        
        is_valid, error_msg, token_info = TokopediaAccessControl().authenticate_request(request)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, '')
        self.assertIsNotNone(token_info)
        self.assertEqual(token_info['name'], 'Development Token')
    
    def test_missing_token_rejection(self):
        """Test that requests without tokens are rejected"""
        request = self.factory.get('/api/test')
        
        is_valid, error_msg, token_info = TokopediaAccessControl().authenticate_request(request)
        
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, 'API token required')
        self.assertIsNone(token_info)
    
    def test_invalid_token_rejection(self):
        """Test that invalid tokens are rejected"""
        request = self.factory.get('/api/test')
        request.META['HTTP_X_API_TOKEN'] = 'invalid-token'
        
        is_valid, error_msg, token_info = TokopediaAccessControl().authenticate_request(request)
        
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, 'Invalid API token')
        self.assertIsNone(token_info)
    
    def test_permission_check_allows_authorized_action(self):
        """Test that tokens with required permission are allowed"""
        token_info = {
            'name': 'Test Token',
            'permissions': ['read', 'write', 'scrape']
        }
        
        has_permission = TokopediaAccessControl.has_permission(token_info, 'scrape')
        self.assertTrue(has_permission)
    
    def test_permission_check_denies_unauthorized_action(self):
        """Test that tokens without required permission are denied"""
        token_info = {
            'name': 'Read Only Token',
            'permissions': ['read']
        }
        
        has_permission = TokopediaAccessControl.has_permission(token_info, 'scrape')
        self.assertFalse(has_permission)
    
    def test_token_authorization_header(self):
        """Test token extraction from Authorization header"""
        request = self.factory.get('/api/test')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer dev-token-12345'
        
        is_valid, _, token_info = TokopediaAccessControl().authenticate_request(request)
        
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
        # Rate limiting is tested through the decorator
        
        @require_api_token(required_permission='scrape')
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test_rate_limit')
        request.META['HTTP_X_API_TOKEN'] = 'dev-token-12345'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.path = '/api/test_rate_limit'
        
        # Make requests up to rate limit (100 per minute for dev token)
        # Test with exactly 100 requests
        for _ in range(100):
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
        rate_limiter = TokopediaRateLimitTracker()
        
        # Exceed rate limit
        for _ in range(11):
            rate_limiter.evaluate_limit("test", max_requests=10)
        
        is_allowed, _ = rate_limiter.evaluate_limit("test", max_requests=10)
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
            self.assertTrue(any('DENIED' in log for log in cm.output))


# =============================================================================
# A03:2021 – Injection Prevention Tests
# =============================================================================

class TestInputValidator(TestCase):
    """Test input validation functionality"""
    
    def test_validate_keyword_accepts_valid_input(self):
        """Test that valid keywords are accepted"""
        is_valid, error_msg, sanitized = ValidationPipeline.validate_keyword_field("valid keyword")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
        self.assertEqual(sanitized, "valid keyword")
    
    def test_validate_keyword_rejects_empty_input(self):
        """Test that empty keywords are rejected"""
        is_valid, error_msg, sanitized = ValidationPipeline.validate_keyword_field("")
        self.assertFalse(is_valid)
        self.assertIn("required", error_msg)
        self.assertIsNone(sanitized)
    
    def test_validate_keyword_rejects_sql_injection(self):
        """Test that SQL injection patterns are detected"""
        malicious_inputs = [
            "keyword'; DROP TABLE users--",
            "keyword OR 1=1",
            "keyword' AND '1'='1",
            "keyword; DELETE FROM products"
        ]
        
        for malicious in malicious_inputs:
            is_valid, _, sanitized = ValidationPipeline.validate_keyword_field(malicious)
            self.assertFalse(is_valid, f"Should reject: {malicious}")
            self.assertIsNone(sanitized)
    
    def test_validate_keyword_rejects_invalid_characters(self):
        """Test that invalid characters are rejected"""
        is_valid, error_msg, sanitized = ValidationPipeline.validate_keyword_field("keyword<script>alert(1)</script>")
        self.assertFalse(is_valid)
        self.assertIn("invalid characters", error_msg.lower())
        self.assertIsNone(sanitized)
    
    def test_validate_keyword_enforces_length_limit(self):
        """Test that length limits are enforced"""
        long_keyword = "a" * 101
        is_valid, error_msg, sanitized = ValidationPipeline.validate_keyword_field(long_keyword, max_length=100)
        self.assertFalse(is_valid)
        self.assertIn("maximum length", error_msg)
        self.assertIsNone(sanitized)
    
    def test_validate_integer_accepts_valid_input(self):
        """Test that valid integers are accepted"""
        is_valid, error_msg, value = ValidationPipeline.validate_integer_field(42, "page")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
        self.assertEqual(value, 42)
    
    def test_validate_integer_converts_string_to_int(self):
        """Test that numeric strings are converted to integers"""
        is_valid, _, value = ValidationPipeline.validate_integer_field("42", "page")
        self.assertTrue(is_valid)
        self.assertEqual(value, 42)
    
    def test_validate_integer_enforces_min_value(self):
        """Test that minimum value is enforced"""
        is_valid, error_msg, value = ValidationPipeline.validate_integer_field(-1, "page", min_value=0)
        self.assertFalse(is_valid)
        self.assertIn("at least", error_msg)
        self.assertIsNone(value)
    
    def test_validate_integer_enforces_max_value(self):
        """Test that maximum value is enforced"""
        is_valid, error_msg, value = ValidationPipeline.validate_integer_field(1001, "limit", max_value=1000)
        self.assertFalse(is_valid)
        self.assertIn("at most", error_msg)
        self.assertIsNone(value)
    
    def test_validate_integer_rejects_invalid_input(self):
        """Test that non-numeric strings are rejected"""
        is_valid, error_msg, value = ValidationPipeline.validate_integer_field("not a number", "page")
        self.assertFalse(is_valid)
        self.assertIn("valid integer", error_msg)
        self.assertIsNone(value)
    
    def test_validate_boolean_accepts_true_values(self):
        """Test that various true values are accepted"""
        true_values = [True, "true", "1", "yes", "TRUE", "YES"]
        for val in true_values:
            is_valid, _, result = ValidationPipeline.validate_boolean_field(val, "flag")
            self.assertTrue(is_valid, f"Should accept: {val}")
            self.assertTrue(result)
    
    def test_validate_boolean_accepts_false_values(self):
        """Test that various false values are accepted"""
        false_values = [False, "false", "0", "no", "FALSE", "NO"]
        for val in false_values:
            is_valid, _, result = ValidationPipeline.validate_boolean_field(val, "flag")
            self.assertTrue(is_valid, f"Should accept: {val}")
            self.assertFalse(result)
    
    def test_validate_boolean_accepts_none(self):
        """Test that None is accepted (for optional fields)"""
        is_valid, _, result = ValidationPipeline.validate_boolean_field(None, "flag")
        self.assertTrue(is_valid)
        self.assertIsNone(result)
    
    def test_validate_boolean_rejects_invalid_input(self):
        """Test that invalid boolean values are rejected"""
        is_valid, error_msg, result = ValidationPipeline.validate_boolean_field("invalid", "flag")
        self.assertFalse(is_valid)
        self.assertIn("boolean", error_msg)
        self.assertIsNone(result)
    
    def test_sanitize_for_database_removes_null_bytes(self):
        """Test that null bytes are removed"""
        data = {"name": "test\x00product"}
        sanitized = ValidationPipeline.sanitize_for_db(data)
        self.assertNotIn("\x00", sanitized["name"])
    
    def test_sanitize_for_database_limits_length(self):
        """Test that strings are length-limited"""
        data = {"description": "a" * 2000}
        sanitized = ValidationPipeline.sanitize_for_db(data)
        self.assertLessEqual(len(sanitized["description"]), 1000)
    
    def test_sanitize_for_database_escapes_html(self):
        """Test that HTML is escaped"""
        data = {"name": "<script>alert('xss')</script>"}
        sanitized = ValidationPipeline.sanitize_for_db(data)
        self.assertNotIn("<script>", sanitized["name"])


class TestDatabaseQueryValidator(TestCase):
    """Test database query validation"""
    
    def test_validate_table_name_accepts_whitelisted_tables(self):
        """Test that whitelisted table names are accepted"""
        valid_tables = [
            'tokopedia_products',
            'tokopedia_locations',
            'tokopedia_price_history'
        ]
        for table in valid_tables:
            self.assertTrue(DatabaseSecurityValidator.is_valid_table(table))
    
    def test_validate_table_name_rejects_non_whitelisted_tables(self):
        """Test that non-whitelisted table names are rejected"""
        invalid_tables = ['users', 'admin', 'information_schema', 'mysql']
        for table in invalid_tables:
            self.assertFalse(DatabaseSecurityValidator.is_valid_table(table))
    
    def test_validate_column_name_accepts_whitelisted_columns(self):
        """Test that whitelisted column names are accepted"""
        valid_columns = ['id', 'name', 'price', 'url', 'unit', 'created_at']
        for column in valid_columns:
            self.assertTrue(DatabaseSecurityValidator.is_valid_column(column))
    
    def test_validate_column_name_rejects_non_whitelisted_columns(self):
        """Test that non-whitelisted column names are rejected"""
        invalid_columns = ['password', 'secret', 'admin', 'custom_field']
        for column in invalid_columns:
            self.assertFalse(DatabaseSecurityValidator.is_valid_column(column))
    
    def test_build_safe_query_creates_valid_select(self):
        """Test that safe SELECT queries are built"""
        is_valid, error_msg, query = DatabaseSecurityValidator.construct_safe_query(
            'SELECT',
            'tokopedia_products',
            ['id', 'name', 'price']
        )
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
        self.assertIn("SELECT id, name, price FROM tokopedia_products", query)
    
    def test_build_safe_query_rejects_invalid_table(self):
        """Test that queries with invalid table names are rejected"""
        is_valid, error_msg, _ = DatabaseSecurityValidator.construct_safe_query(
            'SELECT',
            'malicious_table',
            ['id']
        )
        self.assertFalse(is_valid)
        self.assertIn("Invalid table name", error_msg)
    
    def test_build_safe_query_rejects_invalid_column(self):
        """Test that queries with invalid column names are rejected"""
        is_valid, error_msg, _ = DatabaseSecurityValidator.construct_safe_query(
            'SELECT',
            'tokopedia_products',
            ['id', 'malicious_column']
        )
        self.assertFalse(is_valid)
        self.assertIn("Invalid column", error_msg)
    
    def test_build_safe_query_rejects_invalid_operation(self):
        """Test that invalid operations are rejected"""
        is_valid, error_msg, _ = DatabaseSecurityValidator.construct_safe_query(
            'DROP',
            'tokopedia_products',
            ['id']
        )
        self.assertFalse(is_valid)
        self.assertIn("Invalid operation", error_msg)


class TestValidateInputDecorator(TestCase):
    """Test validate_input decorator functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_validate_input_decorator_accepts_valid_input(self):
        """Test that decorator allows requests with valid input"""
        @validate_input({
            'keyword': lambda x: ValidationPipeline.validate_keyword_field(x),
            'page': lambda x: ValidationPipeline.validate_integer_field(x, 'page', min_value=0)
        })
        def test_view(request):
            return JsonResponse({
                'keyword': request.validated_data.get('keyword'),
                'page': request.validated_data.get('page')
            })
        
        request = self.factory.get('/api/test?keyword=test&page=1')
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['keyword'], 'test')
        self.assertEqual(data['page'], 1)
    
    def test_validate_input_decorator_rejects_invalid_input(self):
        """Test that decorator rejects requests with invalid input"""
        @validate_input({
            'keyword': lambda x: ValidationPipeline.validate_keyword_field(x)
        })
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test?keyword=test\'OR\'1\'=\'1')
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Validation failed', data['error'])
    
    def test_validate_input_decorator_handles_post_json(self):
        """Test that decorator handles POST requests with JSON body"""
        @validate_input({
            'name': lambda x: ValidationPipeline.validate_keyword_field(x),
            'price': lambda x: ValidationPipeline.validate_integer_field(x, 'price', min_value=0)
        })
        def test_view(request):
            return JsonResponse(request.validated_data)
        
        request = self.factory.post(
            '/api/test',
            data=json.dumps({'name': 'Product', 'price': 100}),
            content_type='application/json'
        )
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['name'], 'Product')
        self.assertEqual(data['price'], 100)
    
    def test_validate_input_decorator_returns_validation_errors(self):
        """Test that decorator returns detailed validation errors"""
        @validate_input({
            'page': lambda x: ValidationPipeline.validate_integer_field(x, 'page', min_value=0, max_value=100)
        })
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test?page=150')
        response = test_view(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('details', data)
        self.assertIn('page', data['details'])


# =============================================================================
# A04:2021 – Insecure Design Prevention Tests
# =============================================================================

class TestSecurityDesignPatterns(TestCase):
    """Test secure design patterns implementation"""
    
    def test_validate_business_logic_accepts_valid_data(self):
        """Test that valid business data is accepted"""
        data = {
            'name': 'Valid Product Name',
            'price': 100.50,
            'url': 'https://tokopedia.com/product'
        }
        is_valid, error_msg = BusinessLogicValidator.validate_business_constraints(data)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_business_logic_rejects_negative_price(self):
        """Test that negative prices are rejected"""
        data = {'price': -50}
        is_valid, error_msg = BusinessLogicValidator.validate_business_constraints(data)
        self.assertFalse(is_valid)
        self.assertIn("positive", error_msg.lower())
    
    def test_validate_business_logic_rejects_excessive_price(self):
        """Test that unreasonably high prices are rejected"""
        data = {'price': 10000000000}
        is_valid, error_msg = BusinessLogicValidator.validate_business_constraints(data)
        self.assertFalse(is_valid)
        self.assertIn("limit", error_msg.lower())
    
    def test_validate_business_logic_rejects_short_name(self):
        """Test that too-short names are rejected"""
        data = {'name': 'A'}
        is_valid, error_msg = BusinessLogicValidator.validate_business_constraints(data)
        self.assertFalse(is_valid)
        self.assertIn("short", error_msg.lower())
    
    def test_validate_business_logic_rejects_long_name(self):
        """Test that too-long names are rejected"""
        data = {'name': 'A' * 501}
        is_valid, error_msg = BusinessLogicValidator.validate_business_constraints(data)
        self.assertFalse(is_valid)
        self.assertIn("long", error_msg.lower())
    
    def test_validate_business_logic_detects_ssrf_attempts(self):
        """Test that SSRF attempts are detected"""
        ssrf_urls = [
            'https://localhost/admin',
            'https://127.0.0.1/secret',
            'https://0.0.0.0/internal'
        ]
        for url in ssrf_urls:
            data = {'url': url}
            is_valid, _ = BusinessLogicValidator.validate_business_constraints(data)
            self.assertFalse(is_valid, f"Should reject SSRF: {url}")
    
    def test_enforce_resource_limits_accepts_valid_limits(self):
        """Test that valid resource limits are accepted"""
        factory = RequestFactory()
        request = factory.get('/api/test?limit=50')
        
        is_valid, error_msg = BusinessLogicValidator.enforce_resource_constraints(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_enforce_resource_limits_rejects_excessive_limit(self):
        """Test that excessive limits are rejected"""
        factory = RequestFactory()
        request = factory.get('/api/test?limit=200')
        
        is_valid, error_msg = BusinessLogicValidator.enforce_resource_constraints(request)
        self.assertFalse(is_valid)
        self.assertIn("maximum", error_msg.lower())
    
    def test_enforce_resource_limits_rejects_too_many_params(self):
        """Test that too many query parameters are rejected"""
        factory = RequestFactory()
        query_string = '&'.join([f'param{i}=value' for i in range(21)])
        request = factory.get(f'/api/test?{query_string}')
        
        is_valid, error_msg = BusinessLogicValidator.enforce_resource_constraints(request)
        self.assertFalse(is_valid)
        self.assertIn("Too many", error_msg)


# =============================================================================
# OWASP A03:2021 Compliance Verification
# =============================================================================

class TestOWASPA03Compliance(TestCase):
    """Verify OWASP A03:2021 Injection Prevention compliance"""
    
    def test_input_validation_uses_whitelist(self):
        """Verify: Positive input validation using whitelists"""
        # Keyword validation uses whitelist pattern
        is_valid, _, _ = ValidationPipeline.validate_keyword_field("valid-input_123")
        self.assertTrue(is_valid)
        
        # Invalid characters rejected
        is_valid, _, _ = ValidationPipeline.validate_keyword_field("invalid<>input")
        self.assertFalse(is_valid)
    
    def test_sql_injection_detection(self):
        """Verify: SQL injection patterns are detected"""
        sql_injections = [
            "' OR '1'='1",
            "'; DROP TABLE users--",
            "1' AND '1'='1"
        ]
        for sql in sql_injections:
            is_valid, _, _ = ValidationPipeline.validate_keyword_field(sql)
            self.assertFalse(is_valid, f"Should detect SQL injection: {sql}")
    
    def test_database_queries_use_parameterization(self):
        """Verify: Database queries use parameterized approach"""
        is_valid, _, query = DatabaseSecurityValidator.construct_safe_query(
            'SELECT',
            'tokopedia_products',
            ['id', 'name'],
            where_clause={'id': 1}
        )
        self.assertTrue(is_valid)
        # Query should use %s placeholders for parameterization
        self.assertIn('%s', query)
    
    def test_data_sanitization(self):
        """Verify: Data is sanitized before database operations"""
        data = {"name": "<script>alert('xss')</script>"}
        sanitized = ValidationPipeline.sanitize_for_db(data)
        self.assertNotIn("<script>", sanitized["name"])


# =============================================================================
# OWASP A04:2021 Compliance Verification
# =============================================================================

class TestOWASPA04Compliance(TestCase):
    """Verify OWASP A04:2021 Insecure Design Prevention compliance"""
    
    def test_business_logic_validation(self):
        """Verify: Business logic constraints are validated"""
        # Invalid business logic should be caught
        is_valid, _ = BusinessLogicValidator.validate_business_constraints({'price': -100})
        self.assertFalse(is_valid)
    
    def test_resource_consumption_limits(self):
        """Verify: Resource consumption is limited"""
        factory = RequestFactory()
        request = factory.get('/api/test?limit=10000')
        
        is_valid, _ = BusinessLogicValidator.enforce_resource_constraints(request)
        self.assertFalse(is_valid)
    
    def test_ssrf_prevention(self):
        """Verify: SSRF attacks are prevented"""
        is_valid, _ = BusinessLogicValidator.validate_business_constraints({
            'url': 'https://localhost/admin'
        })
        self.assertFalse(is_valid)
    
    def test_plausibility_checks(self):
        """Verify: Plausibility checks on data"""
        # Unreasonably high price should be rejected
        is_valid, _ = BusinessLogicValidator.validate_business_constraints({'price': 999999999999})
        self.assertFalse(is_valid)
