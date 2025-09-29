import json
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.urls import reverse
from django.http import JsonResponse
from django.middleware.csrf import get_token

from api.validation import InputValidator, ValidationResult
from api.interfaces import ScrapingResult

from django.test import RequestFactory
from api.views import validate_scraper_input_api


class ViewsTestCase(TestCase):
    """Base test case with common setup"""
    
    def setUp(self):
        self.client = Client()
        self.valid_data = {
            'keyword': 'cement blocks',
            'vendor': 'depobangunan',
            'page': 1,
            'sort_by_price': True
        }
        self.invalid_data = {
            'keyword': '',
            'vendor': 'invalid_vendor',
            'page': -1,
            'sort_by_price': True
        }


class HealthCheckViewTests(ViewsTestCase):
    """Tests for health_check view"""
    
    def test_health_check_success(self):
        """Test successful health check"""
        response = self.client.get(reverse('health_check'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['status'] == 'healthy')
        self.assertTrue(data['api_version'] == '1.0')
        self.assertTrue(data['validation_enabled'])
    
    def test_health_check_method_not_allowed(self):
        """Test health check with wrong HTTP method"""
        response = self.client.post(reverse('health_check'))
        self.assertEqual(response.status_code, 405)


class ValidateScraperInputViewTests(ViewsTestCase):
    """Tests for validate_scraper_input view (GET endpoint)"""
    
    def test_validate_scraper_input_success(self):
        """Test successful validation with GET parameters"""
        response = self.client.get(reverse('validate_scraper_input'), {
            'keyword': 'cement blocks',
            'vendor': 'depobangunan',
            'page': '1',
            'sort_by_price': 'true'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('validated_data', data)
        self.assertIn('scraper_info', data)
        self.assertIn('would_scrape_url', data)
    
    def test_validate_scraper_input_validation_error(self):
        """Test validation failure with invalid parameters"""
        response = self.client.get(reverse('validate_scraper_input'), {
            'keyword': '',  # Empty keyword should fail
            'vendor': 'depobangunan',
            'page': '1',
            'sort_by_price': 'true'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'VALIDATION_ERROR')
        self.assertIn('validation_errors', data)
    
    @patch('api.views.validate_and_process_request')
    def test_validate_scraper_input_internal_error(self, mock_validate):
        """Test internal server error handling"""
        mock_validate.side_effect = Exception("Test exception")
        
        response = self.client.get(reverse('validate_scraper_input'), {
            'keyword': 'test',
            'vendor': 'depobangunan'
        })
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INTERNAL_ERROR')
    
    def test_validate_scraper_input_method_not_allowed(self):
        """Test with wrong HTTP method"""
        response = self.client.post(reverse('validate_scraper_input'))
        self.assertEqual(response.status_code, 405)


class ValidateScraperInputJsonViewTests(ViewsTestCase):
    """Tests for validate_scraper_input_json view (POST with JSON)"""
    
    def test_validate_scraper_input_json_success(self):
        """Test successful JSON validation"""
        response = self.client.post(
            reverse('validate_scraper_input_json'),
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('validated_data', data)
        self.assertEqual(data['message'], 'JSON input validation successful - parameters valid for scraping')
    
    def test_validate_scraper_input_json_invalid_json(self):
        """Test with invalid JSON"""
        response = self.client.post(
            reverse('validate_scraper_input_json'),
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INVALID_JSON')
    
    def test_validate_scraper_input_json_validation_error(self):
        """Test validation failure"""
        response = self.client.post(
            reverse('validate_scraper_input_json'),
            data=json.dumps(self.invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'VALIDATION_ERROR')
        self.assertIn('validation_errors', data)
    
    @patch('api.views.validate_and_process_request')
    def test_validate_scraper_input_json_internal_error(self, mock_validate):
        """Test internal server error handling"""
        mock_validate.side_effect = Exception("Test exception")
        
        response = self.client.post(
            reverse('validate_scraper_input_json'),
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INTERNAL_ERROR')


class ValidateScraperInputApiViewTests(ViewsTestCase):
    """Tests for validate_scraper_input_api view (secure API with CSRF)"""
    
    def test_validate_scraper_input_api_invalid_content_type(self):
        """Test with invalid content type"""
        response = self.client.post(
            reverse('validate_scraper_input_api'),
            data=json.dumps(self.valid_data),
            content_type='text/plain'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INVALID_CONTENT_TYPE')
    
    @patch('api.views.logger')
    def test_validate_scraper_input_api_browser_warning(self, mock_logger):
        """Test browser user agent warning"""
        response = self.client.post(
            reverse('validate_scraper_input_api'),
            data=json.dumps(self.valid_data),
            content_type='application/json',
            HTTP_USER_AGENT='Mozilla/5.0 (browser test)'
        )
        
        # Should warn about browser access
        mock_logger.warning.assert_called()
    
    def test_validate_scraper_input_api_invalid_json(self):
        """Test with invalid JSON"""
        response = self.client.post(
            reverse('validate_scraper_input_api'),
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'INVALID_JSON')
    
    @patch('api.views.validate_and_process_request')
    def test_validate_scraper_input_api_internal_error(self, mock_validate):
        """Test internal server error handling"""
        mock_validate.side_effect = Exception("Test exception")
        
        response = self.client.post(
            reverse('validate_scraper_input_api'),
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['code'], 'INTERNAL_ERROR')


class ValidateScraperInputLegacyApiViewTests(ViewsTestCase):
    """Tests for validate_scraper_input_legacy_api view (CSRF exempt)"""
    
    def test_validate_scraper_input_legacy_api_success(self):
        """Test successful legacy API validation"""
        response = self.client.post(
            reverse('validate_scraper_input_legacy_api'),
            data=json.dumps(self.valid_data),
            content_type='application/json',
            HTTP_USER_AGENT='TestClient/1.0'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('WARNING', data['note'])
        
        # Check security headers
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-XSS-Protection'], '1; mode=block')
    
    def test_validate_scraper_input_legacy_api_invalid_content_type(self):
        """Test with invalid content type"""
        response = self.client.post(
            reverse('validate_scraper_input_legacy_api'),
            data=json.dumps(self.valid_data),
            content_type='text/plain'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'INVALID_CONTENT_TYPE')
    
    def test_validate_scraper_input_legacy_api_browser_blocked(self):
        """Test browser requests are blocked"""
        response = self.client.post(
            reverse('validate_scraper_input_legacy_api'),
            data=json.dumps(self.valid_data),
            content_type='application/json',
            HTTP_USER_AGENT='Mozilla/5.0 (Chrome browser test)'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['code'], 'BROWSER_REQUEST_BLOCKED')
    
    @patch('api.views.logger')
    def test_validate_scraper_input_legacy_api_suspicious_agent_logged(self, mock_logger):
        """Test suspicious user agent logging"""
        response = self.client.post(
            reverse('validate_scraper_input_legacy_api'),
            data=json.dumps(self.valid_data),
            content_type='application/json',
            HTTP_USER_AGENT='curl/7.68.0'
        )
        
        # Should log development tool detection
        mock_logger.info.assert_called()
    
    def test_validate_scraper_input_legacy_api_invalid_json(self):
        """Test with invalid JSON"""
        response = self.client.post(
            reverse('validate_scraper_input_legacy_api'),
            data='invalid json',
            content_type='application/json',
            HTTP_USER_AGENT='TestClient/1.0'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'INVALID_JSON')
    
    def test_validate_scraper_input_legacy_api_validation_error(self):
        """Test validation failure"""
        response = self.client.post(
            reverse('validate_scraper_input_legacy_api'),
            data=json.dumps(self.invalid_data),
            content_type='application/json',
            HTTP_USER_AGENT='TestClient/1.0'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'VALIDATION_ERROR')


class GetCsrfTokenViewTests(ViewsTestCase):
    """Tests for get_csrf_token view"""
    
    def test_get_csrf_token_success(self):
        """Test successful CSRF token retrieval"""
        response = self.client.get(reverse('get_csrf_token'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('csrf_token', data)
        self.assertIn('usage', data)
        self.assertIn('example', data)
        self.assertEqual(data['example']['header'], 'X-CSRFToken')


class ValidateScrapingParamsEndpointViewTests(ViewsTestCase):
    """Tests for validate_scraping_params_endpoint view"""
    
    def test_validate_scraping_params_success(self):
        """Test successful parameter validation"""
        response = self.client.post(
            reverse('validate_params'),
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('cleaned_data', data)
    
    def test_validate_scraping_params_invalid_json(self):
        """Test with invalid JSON"""
        response = self.client.post(
            reverse('validate_params'),
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'INVALID_JSON')
    
    def test_validate_scraping_params_validation_error(self):
        """Test validation failure"""
        response = self.client.post(
            reverse('validate_params'),
            data=json.dumps(self.invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('validation_errors', data)


class GetValidationRulesViewTests(ViewsTestCase):
    """Tests for get_validation_rules view"""
    
    def test_get_validation_rules_success(self):
        """Test successful validation rules retrieval"""
        response = self.client.get(reverse('validation_rules'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('validation_rules', data)
        
        rules = data['validation_rules']
        self.assertIn('keyword', rules)
        self.assertIn('vendor', rules)
        self.assertIn('page', rules)
        self.assertIn('sort_by_price', rules)
        
        # Check keyword rules
        self.assertTrue(rules['keyword']['required'])
        self.assertEqual(rules['keyword']['min_length'], InputValidator.MIN_KEYWORD_LENGTH)
        self.assertEqual(rules['keyword']['max_length'], InputValidator.MAX_KEYWORD_LENGTH)
        
        # Check vendor rules
        self.assertEqual(rules['vendor']['allowed_values'], InputValidator.ALLOWED_VENDORS)


class GetSupportedVendorsViewTests(ViewsTestCase):
    """Tests for get_supported_vendors view"""
    
    def test_get_supported_vendors_success(self):
        """Test successful supported vendors retrieval"""
        response = self.client.get(reverse('supported_vendors'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('supported_vendors', data)
        self.assertIn('vendors_status', data)
        self.assertEqual(data['total_vendors'], len(InputValidator.ALLOWED_VENDORS))
        
        # Check each vendor has status info
        for vendor in InputValidator.ALLOWED_VENDORS:
            self.assertIn(vendor, data['vendors_status'])
            vendor_status = data['vendors_status'][vendor]
            self.assertIn('available', vendor_status)
    
    @patch('api.views.get_scraper_factory')
    def test_get_supported_vendors_with_unavailable_vendor(self, mock_factory):
        """Test when a vendor is unavailable"""
        mock_factory.side_effect = Exception("Scraper not available")
        
        response = self.client.get(reverse('supported_vendors'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])


class ValidateVendorInputViewTests(ViewsTestCase):
    """Tests for validate_vendor_input view"""
    
    def test_validate_vendor_input_success(self):
        """Test successful vendor-specific validation"""
        vendor = 'depobangunan'
        test_data = {
            'keyword': 'cement blocks',
            'page': 1,
            'sort_by_price': True
        }
        
        response = self.client.post(
            reverse('validate_vendor_input', kwargs={'vendor': vendor}),
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['vendor'], vendor)
        self.assertIn('validated_input', data)
    
    def test_validate_vendor_input_invalid_vendor(self):
        """Test with invalid vendor"""
        vendor = 'invalid_vendor'
        test_data = {
            'keyword': 'cement blocks',
            'page': 1,
            'sort_by_price': True
        }
        
        response = self.client.post(
            reverse('validate_vendor_input', kwargs={'vendor': vendor}),
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INVALID_VENDOR')
    
    def test_validate_vendor_input_invalid_json(self):
        """Test with invalid JSON"""
        response = self.client.post(
            reverse('validate_vendor_input', kwargs={'vendor': 'depobangunan'}),
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'INVALID_JSON')
    
    def test_validate_vendor_input_validation_error(self):
        """Test validation failure"""
        vendor = 'depobangunan'
        test_data = {
            'keyword': '',  # Empty keyword should fail
            'page': 1,
            'sort_by_price': True
        }
        
        response = self.client.post(
            reverse('validate_vendor_input', kwargs={'vendor': vendor}),
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'VALIDATION_ERROR')
    
    @patch('api.views.validate_and_process_request')
    def test_validate_vendor_input_internal_error(self, mock_validate):
        """Test internal server error handling"""
        mock_validate.side_effect = Exception("Test exception")
        
        response = self.client.post(
            reverse('validate_vendor_input', kwargs={'vendor': 'depobangunan'}),
            data=json.dumps({'keyword': 'test'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['code'], 'INTERNAL_ERROR')


class HelperFunctionTests(ViewsTestCase):
    """Tests for helper functions in views.py"""
    
    def test_get_scraper_factory_success(self):
        """Test successful scraper factory retrieval"""
        from api.views import get_scraper_factory
        
        scraper = get_scraper_factory('depobangunan')
        self.assertIsNotNone(scraper)
        self.assertTrue(hasattr(scraper, '__class__'))
    
    def test_get_scraper_factory_invalid_vendor(self):
        """Test scraper factory with invalid vendor"""
        from api.views import get_scraper_factory
        
        with self.assertRaises(ValueError) as context:
            get_scraper_factory('invalid_vendor')
        
        self.assertIn('Unsupported vendor', str(context.exception))
    
    def test_get_scraper_info_and_url_success(self):
        """Test successful scraper info and URL generation"""
        from api.views import get_scraper_info_and_url
        
        cleaned_data = {
            'vendor': 'depobangunan',
            'keyword': 'cement',
            'page': 1,
            'sort_by_price': True
        }
        
        scraper_info, scraping_url = get_scraper_info_and_url(cleaned_data)
        
        self.assertTrue(scraper_info['available'])
        self.assertIn('class_name', scraper_info)
        self.assertIsNotNone(scraping_url)
    
    def test_get_scraper_info_and_url_invalid_vendor(self):
        """Test scraper info with invalid vendor"""
        from api.views import get_scraper_info_and_url
        
        cleaned_data = {
            'vendor': 'invalid_vendor',
            'keyword': 'cement',
            'page': 1,
            'sort_by_price': True
        }
        
        scraper_info, scraping_url = get_scraper_info_and_url(cleaned_data)
        
        self.assertFalse(scraper_info['available'])
        self.assertIn('error', scraper_info)
        self.assertIsNone(scraping_url)
    
    @patch('api.views.InputValidator.validate_scraping_request')
    def test_validate_and_process_request_success(self, mock_validator):
        """Test successful request validation and processing"""
        from api.views import validate_and_process_request
        
        # Mock successful validation
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.cleaned_data = {
            'vendor': 'depobangunan',
            'keyword': 'cement',
            'page': 1,
            'sort_by_price': True
        }
        mock_validator.return_value = mock_result
        
        validation_result, cleaned_data, scraper_info, scraping_url = validate_and_process_request(
            self.valid_data
        )
        
        self.assertTrue(validation_result.is_valid)
        self.assertIsNotNone(cleaned_data)
        self.assertIsNotNone(scraper_info)
        self.assertIsNotNone(scraping_url)
    
    @patch('api.views.InputValidator.validate_scraping_request')
    def test_validate_and_process_request_failure(self, mock_validator):
        """Test failed request validation"""
        from api.views import validate_and_process_request
        
        # Mock failed validation
        mock_result = Mock()
        mock_result.is_valid = False
        mock_validator.return_value = mock_result
        
        validation_result, cleaned_data, scraper_info, scraping_url = validate_and_process_request(
            self.invalid_data
        )
        
        self.assertFalse(validation_result.is_valid)
        self.assertIsNone(cleaned_data)
        self.assertIsNone(scraper_info)
        self.assertIsNone(scraping_url)
    
    def test_create_validation_success_response(self):
        """Test creation of successful validation response"""
        from api.views import create_validation_success_response
        
        cleaned_data = {
            'keyword': 'cement',
            'vendor': 'depobangunan',
            'page': 1,
            'sort_by_price': True
        }
        scraper_info = {'available': True, 'class_name': 'TestScraper'}
        scraping_url = 'http://example.com/search'
        message = 'Test success'
        note = 'Test note'
        
        response = create_validation_success_response(
            cleaned_data, scraper_info, scraping_url, message, note
        )
        
        self.assertTrue(response['success'])
        self.assertEqual(response['message'], message)
        self.assertEqual(response['note'], note)
        self.assertIn('validated_data', response)
        self.assertEqual(response['scraper_info'], scraper_info)
        self.assertEqual(response['would_scrape_url'], scraping_url)


class EdgeCaseTests(ViewsTestCase):
    """Tests for edge cases and error conditions"""
    
    def test_missing_content_type_header(self):        
        factory = RequestFactory()
        request = factory.generic(
            'POST',
            '/api/validate-input-api/',
            data=json.dumps(self.valid_data),
            content_type='application/octet-stream'  # Default when no content-type is set
        )
        
        response = validate_scraper_input_api(request)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 'INVALID_CONTENT_TYPE')
    
    def test_empty_request_body(self):
        """Test request with empty body"""
        response = self.client.post(
            reverse('validate_scraper_input_json'),
            data='',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'INVALID_JSON')
    
    def test_malformed_json(self):
        """Test request with malformed JSON"""
        response = self.client.post(
            reverse('validate_scraper_input_json'),
            data='{"invalid": json}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'INVALID_JSON')
    
    def test_large_request_payload(self):
        """Test with large request payload"""
        large_data = self.valid_data.copy()
        large_data['keyword'] = 'a' * 10000  # Very long keyword
        
        response = self.client.post(
            reverse('validate_scraper_input_legacy_api'),
            data=json.dumps(large_data),
            content_type='application/json',
            HTTP_USER_AGENT='TestClient/1.0'
        )
        
        # Should fail validation due to keyword length
        self.assertEqual(response.status_code, 400)
    
    @patch('api.views.logger')
    def test_logging_functionality(self, mock_logger):
        """Test that logging works correctly"""
        response = self.client.post(
            reverse('validate_scraper_input_legacy_api'),
            data=json.dumps(self.valid_data),
            content_type='application/json',
            HTTP_USER_AGENT='TestClient/1.0'
        )
        
        # Verify logging was called
        mock_logger.warning.assert_called()