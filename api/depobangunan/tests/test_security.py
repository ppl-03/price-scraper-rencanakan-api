"""
Comprehensive tests for DepoBangunan Security Module
Tests all OWASP implementations: A01 (Broken Access Control), A03 (Injection), A04 (Insecure Design)
Combined coverage for complete security module testing
"""
import time
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.http import JsonResponse, QueryDict
from api.depobangunan.security import (
    RateLimitTracker,
    RateLimiter,
    TokenRegistry,
    AccessValidator,
    SecurityAuditLog,
    AccessControlManager,
    ValidationRule,
    RequiredRule,
    LengthRule,
    PatternRule,
    SqlInjectionRule,
    SanitizeRule,
    StripWhitespaceRule,
    TypeConversionRule,
    RangeRule,
    BooleanConversionRule,
    ValidationChainBuilder,
    InputValidator,
    DatabaseQueryValidator,
    SecurityDesignPatterns,
    require_api_token,
    validate_input,
    enforce_resource_limits,
    RequestDataExtractor,
    FieldValidationExecutor,
    _get_request_data,
    _validate_fields,
)
import re
import logging

# Suppress logger during tests
logging.disable(logging.CRITICAL)


# ============================================================================
# OWASP A01 & A03: Access Control and Injection Prevention Tests
# ============================================================================

class RateLimitTrackerTests(TestCase):
    """Test RateLimitTracker for line 48"""
    
    def test_apply_block_logging(self):
        """Test that apply_block logs warning - covers line 48"""
        tracker = RateLimitTracker()
        with patch('api.depobangunan.security.logger.warning') as mock_log:
            tracker.apply_block('test_client', 60)
            mock_log.assert_called_once()
            self.assertIn('Rate limit block applied', mock_log.call_args[0][0])


class AccessValidatorTests(TestCase):
    """Test AccessValidator edge cases"""
    
    def test_extract_token_with_bearer_prefix(self):
        """Test Bearer token extraction - covers line 197"""
        request = Mock()
        request.headers.get = Mock(side_effect=lambda x: 'Bearer test_token_123' if x == 'Authorization' else None)
        request.META = {'HTTP_AUTHORIZATION': 'Bearer test_token_123'}
        
        token = AccessValidator.extract_token_from_request(request)
        self.assertEqual(token, 'test_token_123')
    
    def test_extract_token_raw_authorization(self):
        """Test raw token in Authorization header - covers line 197"""
        request = Mock()
        request.headers.get = Mock(side_effect=lambda x: 'raw_token_123' if x == 'Authorization' else None)
        request.META = {'HTTP_AUTHORIZATION': 'raw_token_123'}
        
        token = AccessValidator.extract_token_from_request(request)
        self.assertEqual(token, 'raw_token_123')
    
    def test_verify_token_unknown_token_logs_warning(self):
        """Test unknown token logging - covers line 213"""
        with patch('api.depobangunan.security.logger.warning') as mock_log:
            is_valid, _, _ = AccessValidator.verify_token_exists('unknown_token', '192.168.1.1')
            self.assertFalse(is_valid)
            mock_log.assert_called_once()
            self.assertIn('Unknown token attempted', mock_log.call_args[0][0])
    
    def test_verify_ip_authorization_unauthorized_ip_logs_warning(self):
        """Test unauthorized IP logging - covers lines 207-215"""
        token_data = {
            'name': 'Test Token',
            'allowed_ips': ['10.0.0.1']
        }
        with patch('api.depobangunan.security.logger.warning') as mock_log:
            is_valid, msg = AccessValidator.verify_ip_authorization(token_data, '192.168.1.1')
            self.assertFalse(is_valid)
            self.assertEqual(msg, 'IP not authorized for this token')
            mock_log.assert_called_once()
    
    def test_verify_ip_authorization_authorized_ip(self):
        """Test authorized IP - covers line 215"""
        token_data = {
            'name': 'Test Token',
            'allowed_ips': ['192.168.1.1', '10.0.0.1']
        }
        is_valid, msg = AccessValidator.verify_ip_authorization(token_data, '192.168.1.1')
        self.assertTrue(is_valid)
        self.assertEqual(msg, '')
    
    def test_verify_permission_denied_logs_warning(self):
        """Test permission denied logging - covers lines 173"""
        token_data = {
            'name': 'Limited Token',
            'permissions': ['read']
        }
        with patch('api.depobangunan.security.logger.warning') as mock_log:
            has_perm = AccessValidator.verify_permission(token_data, 'write')
            self.assertFalse(has_perm)
            mock_log.assert_called_once()
            self.assertIn('Permission', mock_log.call_args[0][0])


class AccessControlManagerTests(TestCase):
    """Test AccessControlManager edge cases"""
    
    def test_log_access_attempt(self):
        """Test log_access_attempt calls SecurityAuditLog - covers line 346"""
        request = Mock()
        request.path = '/api/test'
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        
        with patch.object(SecurityAuditLog, 'log_access_event') as mock_log:
            AccessControlManager.log_access_attempt(request, True, '')
            mock_log.assert_called_once_with(request, True, '')
    
    def test_check_for_attack_pattern(self):
        """Test _check_for_attack_pattern calls SecurityAuditLog - covers line 346"""
        with patch.object(SecurityAuditLog, 'check_attack_indicators') as mock_check:
            AccessControlManager._check_for_attack_pattern('192.168.1.1')
            mock_check.assert_called_once_with('192.168.1.1')


class LengthRuleTests(TestCase):
    """Test LengthRule validation"""
    
    def test_length_min_violation(self):
        """Test minimum length validation - covers line 410"""
        rule = LengthRule('test_field', min_len=5, max_len=10)
        is_valid, error, _ = rule.validate('abc')
        self.assertFalse(is_valid)
        self.assertIn('at least 5', error)
    
    def test_length_max_violation(self):
        """Test maximum length validation - covers line 410"""
        rule = LengthRule('test_field', min_len=5, max_len=10)
        is_valid, error, _ = rule.validate('12345678901')
        self.assertFalse(is_valid)
        self.assertIn('maximum length', error)


class PatternRuleTests(TestCase):
    """Test PatternRule validation"""
    
    def test_pattern_mismatch_logs_warning(self):
        """Test pattern validation failure logging - covers line 431-432"""
        pattern = re.compile(r'^[a-z]+$')
        rule = PatternRule('test_field', pattern, 'Only lowercase letters allowed')
        
        with patch('api.depobangunan.security.logger.warning') as mock_log:
            is_valid, _, _ = rule.validate('ABC123')
            self.assertFalse(is_valid)
            mock_log.assert_called_once()
            self.assertIn('Pattern validation failed', mock_log.call_args[0][0])


class SqlInjectionRuleTests(TestCase):
    """Test SqlInjectionRule validation"""
    
    def test_sql_injection_detected_logs_critical(self):
        """Test SQL injection detection logging - covers line 456"""
        rule = SqlInjectionRule('query_field')
        
        with patch('api.depobangunan.security.logger.critical') as mock_log:
            is_valid, _, _ = rule.validate("test' OR '1'='1")
            self.assertFalse(is_valid)
            mock_log.assert_called_once()
            self.assertIn('SQL injection detected', mock_log.call_args[0][0])


class SanitizeRuleTests(TestCase):
    """Test SanitizeRule validation"""
    
    def test_null_byte_removal(self):
        """Test null byte sanitization - covers line 471"""
        rule = SanitizeRule('data_field')
        is_valid, _, sanitized = rule.validate('test\x00data')
        self.assertTrue(is_valid)
        self.assertEqual(sanitized, 'testdata')


class TypeConversionRuleTests(TestCase):
    """Test TypeConversionRule validation"""
    
    def test_conversion_failure(self):
        """Test type conversion failure - covers line 495"""
        rule = TypeConversionRule('num_field', int)
        is_valid, error, _ = rule.validate('not_a_number')
        self.assertFalse(is_valid)
        self.assertIn('valid integer', error)


class RangeRuleTests(TestCase):
    """Test RangeRule validation"""
    
    def test_value_below_minimum(self):
        """Test value below minimum - covers line 511"""
        rule = RangeRule('age', min_val=18, max_val=100)
        is_valid, error, _ = rule.validate(15)
        self.assertFalse(is_valid)
        self.assertIn('at least 18', error)
    
    def test_value_above_maximum(self):
        """Test value above maximum - covers line 511"""
        rule = RangeRule('age', min_val=18, max_val=100)
        is_valid, error, _ = rule.validate(150)
        self.assertFalse(is_valid)
        self.assertIn('at most 100', error)


class BooleanConversionRuleTests(TestCase):
    """Test BooleanConversionRule validation"""
    
    def test_none_value(self):
        """Test None value handling - covers line 527"""
        rule = BooleanConversionRule('bool_field')
        is_valid, _, result = rule.validate(None)
        self.assertTrue(is_valid)
        self.assertIsNone(result)
    
    def test_non_string_non_bool(self):
        """Test non-string, non-bool value - covers line 548"""
        rule = BooleanConversionRule('bool_field')
        is_valid, error, _ = rule.validate(123)
        self.assertFalse(is_valid)
        self.assertIn('must be a boolean', error)
    
    def test_empty_string(self):
        """Test empty string - covers line 551"""
        rule = BooleanConversionRule('bool_field')
        is_valid, error, _ = rule.validate('   ')
        self.assertFalse(is_valid)
        self.assertIn('cannot be empty', error)
    
    def test_sql_injection_in_boolean(self):
        """Test SQL injection attempt in boolean - covers lines 554, 563-564"""
        rule = BooleanConversionRule('bool_field')
        
        with patch('api.depobangunan.security.logger.warning') as mock_log:
            is_valid, error, _ = rule.validate("true' OR '1'='1")
            self.assertFalse(is_valid)
            self.assertIn('forbidden characters', error)
            mock_log.assert_called_once()
    
    def test_invalid_boolean_value(self):
        """Test invalid boolean string - covers lines 567, 569"""
        rule = BooleanConversionRule('bool_field')
        is_valid, error, _ = rule.validate('maybe')
        self.assertFalse(is_valid)
        self.assertIn("must be 'true'", error)


class InputValidatorTests(TestCase):
    """Test InputValidator legacy methods"""
    
    def test_validate_boolean_string_legacy(self):
        """Test legacy _validate_boolean_string method - covers line 647"""
        is_valid, _, result = InputValidator._validate_boolean_string('true', 'test_field')
        self.assertTrue(is_valid)
        self.assertTrue(result)
    
    def test_contains_sql_injection_pattern(self):
        """Test _contains_sql_injection_pattern - covers lines 652-653"""
        result = InputValidator._contains_sql_injection_pattern("select * from")
        self.assertTrue(result)
        
        result = InputValidator._contains_sql_injection_pattern("clean text")
        self.assertFalse(result)
    
    def test_parse_boolean_value_legacy(self):
        """Test legacy _parse_boolean_value method - covers line 658"""
        is_valid, _, result = InputValidator._parse_boolean_value('false', 'test_field')
        self.assertTrue(is_valid)
        self.assertFalse(result)
    
    def test_detect_sql_injection(self):
        """Test _detect_sql_injection method - covers lines 672-682"""
        # Test with SQL injection patterns
        self.assertTrue(InputValidator._detect_sql_injection("test' OR '1'='1"))
        self.assertTrue(InputValidator._detect_sql_injection("SELECT * FROM users"))
        self.assertTrue(InputValidator._detect_sql_injection("test UNION SELECT"))
        
        # Test clean input
        self.assertFalse(InputValidator._detect_sql_injection("clean input"))


class DatabaseQueryValidatorTests(TestCase):
    """Test DatabaseQueryValidator"""
    
    def test_build_safe_query_invalid_operation(self):
        """Test invalid SQL operation - covers line 722"""
        is_valid, error, _ = DatabaseQueryValidator.build_safe_query(
            'DROP', 'depobangunan_products', ['id', 'name']
        )
        self.assertFalse(is_valid)
        self.assertEqual(error, "Invalid operation")
    
    def test_build_safe_query_invalid_table(self):
        """Test invalid table name - covers lines 730-742"""
        with patch('api.depobangunan.security.logger.critical') as mock_log:
            is_valid, error, _ = DatabaseQueryValidator.build_safe_query(
                'SELECT', 'products; DROP TABLE users', ['id']
            )
            self.assertFalse(is_valid)
            self.assertEqual(error, "Invalid table name")
            mock_log.assert_called_once()
    
    def test_build_safe_query_invalid_column(self):
        """Test invalid column name - covers lines 730-742"""
        with patch('api.depobangunan.security.logger.critical') as mock_log:
            is_valid, error, _ = DatabaseQueryValidator.build_safe_query(
                'SELECT', 'depobangunan_products', ['id', 'name; DROP TABLE']
            )
            self.assertFalse(is_valid)
            self.assertEqual(error, "Invalid column name")
            mock_log.assert_called_once()
    
    def test_build_safe_query_success_simple(self):
        """Test successful query building - covers lines 736-742"""
        is_valid, error, query = DatabaseQueryValidator.build_safe_query(
            'SELECT', 'depobangunan_products', ['id', 'name', 'price']
        )
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        self.assertEqual(query, "SELECT id, name, price FROM depobangunan_products")
    
    def test_build_safe_query_with_where_clause(self):
        """Test query building with WHERE clause - covers lines 736-742"""
        is_valid, error, query = DatabaseQueryValidator.build_safe_query(
            'SELECT', 'depobangunan_products', ['id', 'name'],
            where_clause={'id': 1, 'code': 'ABC'}
        )
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        self.assertIn("WHERE", query)
        self.assertIn("id = %s", query)
        self.assertIn("code = %s", query)


class RequireApiTokenDecoratorTests(TestCase):
    """Test require_api_token decorator"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_token_validation_failure(self):
        """Test token validation failure - covers lines 870-871"""
        @require_api_token()
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test')
        request.headers = {}
        request.META = {}
        
        with patch.object(AccessControlManager, 'validate_token', return_value=(False, 'Invalid token', None)):
            with patch.object(AccessControlManager, 'log_access_attempt') as mock_log:
                response = test_view(request)
                self.assertEqual(response.status_code, 401)
                mock_log.assert_called_once()
    
    def test_permission_check_failure(self):
        """Test permission check failure - covers lines 877-880"""
        @require_api_token(required_permission='admin')
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test')
        token_info = {'permissions': ['read']}
        
        with patch.object(AccessControlManager, 'validate_token', return_value=(True, '', token_info)):
            with patch.object(AccessControlManager, 'check_permission', return_value=False):
                with patch.object(AccessControlManager, 'log_access_attempt') as mock_log:
                    response = test_view(request)
                    self.assertEqual(response.status_code, 403)
                    mock_log.assert_called_once()
    
    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded - covers lines 897-898"""
        @require_api_token()
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/api/test')
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        request.path = '/api/test'
        token_info = {'rate_limit': {'requests': 10, 'window': 60}}
        
        with patch.object(AccessControlManager, 'validate_token', return_value=(True, '', token_info)):
            with patch.object(AccessControlManager, 'check_permission', return_value=True):
                with patch('api.depobangunan.security.rate_limiter.check_rate_limit', return_value=(False, 'Rate limit exceeded')):
                    with patch.object(AccessControlManager, 'log_access_attempt') as mock_log:
                        response = test_view(request)
                        self.assertEqual(response.status_code, 429)
                        mock_log.assert_called_once()


class RequestDataExtractorTests(TestCase):
    """Test RequestDataExtractor"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_extract_get_request(self):
        """Test GET request extraction - covers line 918-925"""
        request = self.factory.get('/api/test?param=value')
        data, error = RequestDataExtractor.extract(request)
        self.assertIsNone(error)
        self.assertEqual(data.get('param'), 'value')
    
    def test_extract_post_with_valid_json(self):
        """Test POST request with valid JSON - covers lines 918-925"""
        request = self.factory.post('/api/test', 
                                   data=json.dumps({'key': 'value'}),
                                   content_type='application/json')
        data, error = RequestDataExtractor.extract(request)
        self.assertIsNone(error)
        self.assertEqual(data['key'], 'value')
    
    def test_extract_post_with_invalid_json(self):
        """Test POST request with invalid JSON - covers lines 936-948"""
        request = self.factory.post('/api/test',
                                   data='invalid json{',
                                   content_type='application/json')
        data, error = RequestDataExtractor.extract(request)
        self.assertIsNone(data)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 400)
    
    def test_extract_empty_body(self):
        """Test request with empty body - covers lines 918-925"""
        request = self.factory.post('/api/test')
        request._body = b''
        data, error = RequestDataExtractor.extract(request)
        self.assertIsNone(error)
        self.assertEqual(data, {})


class ValidateInputDecoratorTests(TestCase):
    """Test validate_input decorator"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_validation_success(self):
        """Test successful validation - covers lines 973-974"""
        def validator_func(value):
            return True, '', value.upper() if value else None
        
        @validate_input({'field': validator_func})
        def test_view(request):
            return JsonResponse({'data': request.validated_data})
        
        request = self.factory.post('/api/test',
                                   data=json.dumps({'field': 'value'}),
                                   content_type='application/json')
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['data']['field'], 'VALUE')
    
    def test_validation_error_response(self):
        """Test validation error response - covers lines 956-977"""
        def validator_func(value):
            return False, 'Validation failed', None
        
        @validate_input({'field': validator_func})
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/api/test',
                                   data=json.dumps({'field': 'value'}),
                                   content_type='application/json')
        
        response = test_view(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Validation failed')
    
    def test_json_decode_error(self):
        """Test JSON decode error in decorator - covers lines 956-977"""
        @validate_input({'field': lambda v: (True, '', v)})
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/api/test',
                                   data='invalid json',
                                   content_type='application/json')
        
        response = test_view(request)
        self.assertEqual(response.status_code, 400)


class EnforceResourceLimitsDecoratorTests(TestCase):
    """Test enforce_resource_limits decorator"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_resource_limit_violation(self):
        """Test resource limit violation - covers lines 1000, 1005"""
        @enforce_resource_limits
        def test_view(request):
            return JsonResponse({'success': True})
        
        # Create request with too many parameters
        params = '&'.join([f'p{i}=v{i}' for i in range(25)])
        request = self.factory.get(f'/api/test?{params}')
        
        response = test_view(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)


class LegacyHelperFunctionsTests(TestCase):
    """Test legacy helper functions"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_get_request_data_legacy(self):
        """Test _get_request_data legacy function - covers line 1000"""
        request = self.factory.get('/api/test?key=value')
        data, error = _get_request_data(request)
        self.assertIsNone(error)
        self.assertEqual(data.get('key'), 'value')
    
    def test_validate_fields_legacy(self):
        """Test _validate_fields legacy function - covers line 1005"""
        validators = {
            'field1': lambda v: (True, '', v),
            'field2': lambda v: (False, 'Invalid', None)
        }
        data_source = {'field1': 'value1', 'field2': 'value2'}
        
        errors, validated = _validate_fields(validators, data_source)
        self.assertEqual(len(errors), 1)
        self.assertIn('field2', errors)
        self.assertIn('field1', validated)


class FieldValidationExecutorTests(TestCase):
    """Test FieldValidationExecutor"""
    
    def test_validate_all_with_none_sanitized(self):
        """Test validate_all when sanitized_value is None"""
        validators = {
            'field1': lambda v: (True, '', None),  # Returns None
            'field2': lambda v: (True, '', 'value2')  # Returns value
        }
        data_source = {'field1': 'value1', 'field2': 'value2'}
        
        errors, validated = FieldValidationExecutor.validate_all(validators, data_source)
        self.assertEqual(len(errors), 0)
        self.assertNotIn('field1', validated)  # Should not include field with None
        self.assertIn('field2', validated)


# ============================================================================
# OWASP A04: Insecure Design Prevention Tests
# ============================================================================


class SecurityDesignPatternsValidatePriceTests(TestCase):
    """Test suite for price field validation"""
    
    def test_valid_price_integer(self):
        """Test that valid integer prices are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(100)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_valid_price_float(self):
        """Test that valid float prices are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(99.99)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_valid_price_zero(self):
        """Test that zero price is accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(0)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_negative_price_rejected(self):
        """Test that negative prices are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(-50)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")
    
    def test_excessive_price_rejected(self):
        """Test that excessively high prices are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(2000000000)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price value exceeds reasonable limit")
    
    def test_max_reasonable_price_accepted(self):
        """Test that maximum reasonable price is accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(1000000000)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_string_price_rejected(self):
        """Test that string prices are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field("100")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")
    
    def test_none_price_rejected(self):
        """Test that None price is rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_price_field(None)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")


class SecurityDesignPatternsValidateNameTests(TestCase):
    """Test suite for name field validation"""
    
    def test_valid_name(self):
        """Test that valid product names are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field("Cement Bag 50kg")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_name_too_short(self):
        """Test that names shorter than 2 characters are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field("A")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Product name too short")
    
    def test_name_two_chars_accepted(self):
        """Test that 2 character names are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field("AB")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_name_too_long(self):
        """Test that names longer than 500 characters are rejected"""
        long_name = "A" * 501
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field(long_name)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Product name too long")
    
    def test_name_max_length_accepted(self):
        """Test that names exactly 500 characters are accepted"""
        max_name = "A" * 500
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field(max_name)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_empty_name_rejected(self):
        """Test that empty names are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_name_field("")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Product name too short")


class SecurityDesignPatternsValidateURLTests(TestCase):
    """Test suite for URL field validation (SSRF protection)"""
    
    def test_valid_https_url(self):
        """Test that valid HTTPS URLs are accepted"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://example.com/product")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_http_url_rejected(self):
        """Test that HTTP URLs are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field(
            "http://example.com/product"
        )
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "URL must use HTTPS protocol for security")

    
    def test_localhost_rejected(self):
        """Test that localhost URLs are rejected (SSRF protection)"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://localhost/admin")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")
    
    def test_127_0_0_1_rejected(self):
        """Test that 127.0.0.1 URLs are rejected (SSRF protection)"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://127.0.0.1/admin")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")
    
    def test_0_0_0_0_rejected(self):
        """Test that 0.0.0.0 URLs are rejected (SSRF protection)"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://0.0.0.0/admin")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")
    
    def test_url_with_localhost_substring(self):
        """Test that URLs containing 'localhost' substring are rejected"""
        is_valid, error_msg = SecurityDesignPatterns._validate_url_field("https://mylocalhostserver.com")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")


class SecurityDesignPatternsValidateBusinessLogicTests(TestCase):
    """Test suite for overall business logic validation"""
    
    def test_valid_product_data(self):
        """Test that valid product data passes all validations"""
        data = {
            'name': 'Cement Bag 50kg',
            'price': 75000,
            'url': 'https://depobangunan.com/product/cement'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_invalid_price_in_data(self):
        """Test that invalid price causes validation to fail"""
        data = {
            'name': 'Cement Bag 50kg',
            'price': -100,
            'url': 'https://depobangunan.com/product/cement'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")
    
    def test_invalid_name_in_data(self):
        """Test that invalid name causes validation to fail"""
        data = {
            'name': 'A',
            'price': 75000,
            'url': 'https://depobangunan.com/product/cement'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Product name too short")
    
    def test_invalid_url_in_data(self):
        """Test that invalid URL causes validation to fail"""
        data = {
            'name': 'Cement Bag 50kg',
            'price': 75000,
            'url': 'http://depobangunan.com/product/cement', 
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "URL must use HTTPS protocol for security")

    
    def test_ssrf_attempt_detected(self):
        """Test that SSRF attempts are detected and blocked"""
        data = {
            'name': 'Cement Bag 50kg',
            'price': 75000,
            'url': 'https://localhost/admin/delete'
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid URL")
    
    def test_partial_data_validation(self):
        """Test that validation works with partial data"""
        data = {'price': 50000}
        is_valid, _ = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid)
        self.assertEqual(_, "")
    
    def test_empty_data_valid(self):
        """Test that empty data is considered valid"""
        data = {}
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_multiple_invalid_fields_returns_first_error(self):
        """Test that when multiple fields are invalid, the first error is returned"""
        data = {
            'price': -100,
            'name': 'A',
            'url': 'http://example.com', 
        }
        is_valid, error_msg = SecurityDesignPatterns.validate_business_logic(data)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Price must be a positive number")



class SecurityDesignPatternsEnforceResourceLimitsTests(TestCase):
    """Test suite for resource limit enforcement"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_valid_request_no_limits(self):
        """Test that requests without limit parameters are accepted"""
        request = self.factory.get('/api/products')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_valid_limit_parameter(self):
        """Test that valid limit parameters are accepted"""
        request = self.factory.get('/api/products?limit=50')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_limit_at_max_accepted(self):
        """Test that limit exactly at max is accepted"""
        request = self.factory.get('/api/products?limit=100')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request, max_page_size=100)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_limit_exceeds_max_rejected(self):
        """Test that limit exceeding max is rejected"""
        request = self.factory.get('/api/products?limit=150')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request, max_page_size=100)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Limit exceeds maximum of 100")
    
    def test_invalid_limit_format_rejected(self):
        """Test that non-integer limit is rejected"""
        request = self.factory.get('/api/products?limit=abc')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Invalid limit parameter")
    
    def test_excessive_query_parameters_rejected(self):
        """Test that excessive query parameters are rejected"""
        # Create request with 21 parameters
        params = '&'.join([f'param{i}=value{i}' for i in range(21)])
        request = self.factory.get(f'/api/products?{params}')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Too many query parameters")
    
    def test_exactly_20_parameters_accepted(self):
        """Test that exactly 20 query parameters are accepted"""
        params = '&'.join([f'param{i}=value{i}' for i in range(20)])
        request = self.factory.get(f'/api/products?{params}')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_custom_max_page_size(self):
        """Test that custom max_page_size is respected"""
        request = self.factory.get('/api/products?limit=60')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request, max_page_size=50)
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Limit exceeds maximum of 50")
    
    def test_zero_limit_accepted(self):
        """Test that zero limit is accepted (could mean no limit)"""
        request = self.factory.get('/api/products?limit=0')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_negative_limit_accepted(self):
        """Test that negative limit is accepted (handled by integer parsing)"""
        request = self.factory.get('/api/products?limit=-10')
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")


class SecurityDesignPatternsIntegrationTests(TestCase):
    """Integration tests for security design patterns"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_complete_secure_request_flow(self):
        """Test a complete secure request flow"""
        # Create a valid request
        request = self.factory.get('/api/products?keyword=cement&limit=50')
        
        # Check resource limits
        is_valid, _ = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertTrue(is_valid)
        
        # Validate product data
        product_data = {
            'name': 'Premium Cement 50kg',
            'price': 75000,
            'url': 'https://depobangunan.com/product/cement-premium'
        }
        is_valid,  _ =  SecurityDesignPatterns.validate_business_logic(product_data)
        self.assertTrue(is_valid)
    
    def test_attack_detection_flow(self):
        """Test that various attack attempts are detected"""
        # Test SSRF attempt
        ssrf_data = {
            'name': 'Product',
            'price': 100,
            'url': 'https://127.0.0.1/admin'
        }
        is_valid, _ = SecurityDesignPatterns.validate_business_logic(ssrf_data)
        self.assertFalse(is_valid)
        
        # Test resource exhaustion attempt
        params = '&'.join([f'p{i}=v{i}' for i in range(25)])
        request = self.factory.get(f'/api/products?{params}')
        is_valid, _ = SecurityDesignPatterns.enforce_resource_limits(request)
        self.assertFalse(is_valid)
        
        # Test business logic violation
        invalid_data = {'price': 5000000000}
        is_valid, _ = SecurityDesignPatterns.validate_business_logic(invalid_data)
        self.assertFalse(is_valid)


# Re-enable logging after tests
logging.disable(logging.NOTSET)
