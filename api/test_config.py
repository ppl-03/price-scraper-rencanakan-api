import unittest
import os
import re
from unittest.mock import patch

from api.config import ScraperConfig, config


class TestScraperConfig(unittest.TestCase):
    def test_default_configuration(self):
        config_obj = ScraperConfig()
        
        self.assertEqual(config_obj.request_timeout, 30)
        self.assertEqual(config_obj.max_retries, 3)
        self.assertEqual(config_obj.retry_delay, 1.0)
        self.assertEqual(config_obj.requests_per_minute, 60)
        self.assertEqual(config_obj.min_request_interval, 1.0)
        self.assertTrue(config_obj.cache_enabled)
        self.assertEqual(config_obj.cache_ttl, 300)
        self.assertEqual(config_obj.log_level, 'INFO')
        self.assertTrue(config_obj.log_requests)
        self.assertEqual(config_obj.gemilang_base_url, 'https://gemilang-store.com')
        self.assertEqual(config_obj.gemilang_search_path, '/pusat/shop')
        
        # Verify User-Agent contains expected browser components (extract version dynamically)
        self.assertIn('Mozilla', config_obj.user_agent)
        # Extract Chrome version from the default user agent to avoid hardcoding
        chrome_match = re.search(r'Chrome/([\d.]+)', config_obj.user_agent)
        self.assertIsNotNone(chrome_match, "User-Agent should contain Chrome version")
        self.assertIn('Safari', config_obj.user_agent)

    def test_custom_configuration(self):
        config_obj = ScraperConfig(
            request_timeout=45,
            max_retries=5,
            retry_delay=2.0,
            user_agent='Test Agent',
            requests_per_minute=30,
            min_request_interval=2.0,
            cache_enabled=False,
            cache_ttl=600,
            log_level='DEBUG',
            log_requests=False,
            gemilang_base_url='https://test.com',
            gemilang_search_path='/test'
        )
        
        self.assertEqual(config_obj.request_timeout, 45)
        self.assertEqual(config_obj.max_retries, 5)
        self.assertEqual(config_obj.retry_delay, 2.0)
        self.assertEqual(config_obj.user_agent, 'Test Agent')
        self.assertEqual(config_obj.requests_per_minute, 30)
        self.assertEqual(config_obj.min_request_interval, 2.0)
        self.assertFalse(config_obj.cache_enabled)
        self.assertEqual(config_obj.cache_ttl, 600)
        self.assertEqual(config_obj.log_level, 'DEBUG')
        self.assertFalse(config_obj.log_requests)
        self.assertEqual(config_obj.gemilang_base_url, 'https://test.com')
        self.assertEqual(config_obj.gemilang_search_path, '/test')

    @patch.dict(os.environ, {}, clear=True)
    def test_from_environment_defaults(self):
        config_obj = ScraperConfig.from_environment()
        
        self.assertEqual(config_obj.request_timeout, 30)
        self.assertEqual(config_obj.max_retries, 3)
        self.assertEqual(config_obj.retry_delay, 1.0)
        self.assertEqual(config_obj.requests_per_minute, 60)
        self.assertEqual(config_obj.min_request_interval, 1.0)
        self.assertTrue(config_obj.cache_enabled)
        self.assertEqual(config_obj.cache_ttl, 300)
        self.assertEqual(config_obj.log_level, 'INFO')
        self.assertTrue(config_obj.log_requests)
        self.assertEqual(config_obj.gemilang_base_url, 'https://gemilang-store.com')
        self.assertEqual(config_obj.gemilang_search_path, '/pusat/shop')

    @patch.dict(os.environ, {
        'SCRAPER_REQUEST_TIMEOUT': '60',
        'SCRAPER_MAX_RETRIES': '5',
        'SCRAPER_RETRY_DELAY': '2.5',
        'SCRAPER_USER_AGENT': 'Custom Agent',
        'SCRAPER_REQUESTS_PER_MINUTE': '120',
        'SCRAPER_MIN_REQUEST_INTERVAL': '0.5',
        'SCRAPER_CACHE_ENABLED': 'false',
        'SCRAPER_CACHE_TTL': '600',
        'SCRAPER_LOG_LEVEL': 'DEBUG',
        'SCRAPER_LOG_REQUESTS': 'false',
        'GEMILANG_BASE_URL': 'https://custom-gemilang.com',
        'GEMILANG_SEARCH_PATH': '/custom/search'
    })
    def test_from_environment_custom_values(self):
        config_obj = ScraperConfig.from_environment()
        
        self.assertEqual(config_obj.request_timeout, 60)
        self.assertEqual(config_obj.max_retries, 5)
        self.assertEqual(config_obj.retry_delay, 2.5)
        self.assertEqual(config_obj.user_agent, 'Custom Agent')
        self.assertEqual(config_obj.requests_per_minute, 120)
        self.assertEqual(config_obj.min_request_interval, 0.5)
        self.assertFalse(config_obj.cache_enabled)
        self.assertEqual(config_obj.cache_ttl, 600)
        self.assertEqual(config_obj.log_level, 'DEBUG')
        self.assertFalse(config_obj.log_requests)
        self.assertEqual(config_obj.gemilang_base_url, 'https://custom-gemilang.com')
        self.assertEqual(config_obj.gemilang_search_path, '/custom/search')

    @patch.dict(os.environ, {
        'SCRAPER_CACHE_ENABLED': 'TRUE',
        'SCRAPER_LOG_REQUESTS': 'TRUE'
    })
    def test_from_environment_boolean_true_uppercase(self):
        config_obj = ScraperConfig.from_environment()
        
        self.assertTrue(config_obj.cache_enabled)
        self.assertTrue(config_obj.log_requests)
        self.assertEqual(config_obj.log_level, 'INFO')

    @patch.dict(os.environ, {
        'SCRAPER_CACHE_ENABLED': 'True',
        'SCRAPER_LOG_REQUESTS': 'True'
    })
    def test_from_environment_boolean_true_capitalized(self):
        config_obj = ScraperConfig.from_environment()
        
        self.assertTrue(config_obj.cache_enabled)
        self.assertTrue(config_obj.log_requests)
        self.assertEqual(config_obj.request_timeout, 30)

    @patch.dict(os.environ, {
        'SCRAPER_CACHE_ENABLED': 'false',
        'SCRAPER_LOG_REQUESTS': 'FALSE'
    })
    def test_from_environment_boolean_false_variations(self):
        config_obj = ScraperConfig.from_environment()
        
        self.assertFalse(config_obj.cache_enabled)
        self.assertFalse(config_obj.log_requests)
        self.assertEqual(config_obj.max_retries, 3)

    @patch.dict(os.environ, {
        'SCRAPER_CACHE_ENABLED': 'invalid',
        'SCRAPER_LOG_REQUESTS': 'random'
    })
    def test_from_environment_boolean_invalid_values(self):
        config_obj = ScraperConfig.from_environment()
        
        self.assertFalse(config_obj.cache_enabled)
        self.assertFalse(config_obj.log_requests)
        self.assertEqual(config_obj.retry_delay, 1.0)

    def test_to_dict_method(self):
        config_obj = ScraperConfig(
            request_timeout=45,
            max_retries=5,
            retry_delay=2.0,
            user_agent='Test Agent',
            requests_per_minute=30,
            min_request_interval=2.0,
            cache_enabled=False,
            cache_ttl=600,
            log_level='DEBUG',
            log_requests=False,
            gemilang_base_url='https://test.com',
            gemilang_search_path='/test'
        )
        
        result_dict = config_obj.to_dict()
        
        # Check key values that were explicitly set
        self.assertEqual(result_dict['request_timeout'], 45)
        self.assertEqual(result_dict['max_retries'], 5)
        self.assertEqual(result_dict['retry_delay'], 2.0)
        self.assertEqual(result_dict['user_agent'], 'Test Agent')
        self.assertEqual(result_dict['requests_per_minute'], 30)
        self.assertEqual(result_dict['min_request_interval'], 2.0)
        self.assertFalse(result_dict['cache_enabled'])
        self.assertEqual(result_dict['cache_ttl'], 600)
        self.assertEqual(result_dict['log_level'], 'DEBUG')
        self.assertFalse(result_dict['log_requests'])
        self.assertEqual(result_dict['gemilang_base_url'], 'https://test.com')
        self.assertEqual(result_dict['gemilang_search_path'], '/test')
        
        # Verify all vendor base URLs are included
        self.assertIn('mitra10_base_url', result_dict)
        self.assertIn('juragan_material_base_url', result_dict)
        self.assertIn('depobangunan_base_url', result_dict)

    def test_to_dict_with_defaults(self):
        config_obj = ScraperConfig()
        result_dict = config_obj.to_dict()
        
        expected_keys = {
            'request_timeout', 'max_retries', 'retry_delay', 'user_agent',
            'requests_per_minute', 'min_request_interval', 'cache_enabled',
            'cache_ttl', 'log_level', 'log_requests', 'gemilang_base_url',
            'gemilang_search_path', 'mitra10_base_url', 'mitra10_search_path',
            'juragan_material_base_url', 'juragan_material_search_path',
            'depobangunan_base_url', 'depobangunan_search_path'
        }
        
        self.assertEqual(set(result_dict.keys()), expected_keys)
        
        self.assertEqual(result_dict['request_timeout'], config_obj.request_timeout)
        self.assertEqual(result_dict['max_retries'], config_obj.max_retries)
        self.assertEqual(result_dict['retry_delay'], config_obj.retry_delay)
        self.assertEqual(result_dict['user_agent'], config_obj.user_agent)
        self.assertEqual(result_dict['requests_per_minute'], config_obj.requests_per_minute)
        self.assertEqual(result_dict['min_request_interval'], config_obj.min_request_interval)
        self.assertEqual(result_dict['cache_enabled'], config_obj.cache_enabled)
        self.assertEqual(result_dict['cache_ttl'], config_obj.cache_ttl)
        self.assertEqual(result_dict['log_level'], config_obj.log_level)
        self.assertEqual(result_dict['log_requests'], config_obj.log_requests)
        self.assertEqual(result_dict['gemilang_base_url'], config_obj.gemilang_base_url)
        self.assertEqual(result_dict['gemilang_search_path'], config_obj.gemilang_search_path)

    def test_global_config_instance(self):
        self.assertIsInstance(config, ScraperConfig)
        
        self.assertTrue(hasattr(config, 'request_timeout'))
        self.assertTrue(hasattr(config, 'max_retries'))
        self.assertTrue(hasattr(config, 'user_agent'))
        self.assertTrue(hasattr(config, 'gemilang_base_url'))

    def test_dataclass_behavior(self):
        config1 = ScraperConfig(request_timeout=30, max_retries=3)
        config2 = ScraperConfig(request_timeout=30, max_retries=3)
        config3 = ScraperConfig(request_timeout=45, max_retries=3)
        
        self.assertEqual(config1, config2)
        self.assertNotEqual(config1, config3)
        
        repr_str = repr(config1)
        self.assertIn('ScraperConfig', repr_str)
        self.assertIn('request_timeout=30', repr_str)
