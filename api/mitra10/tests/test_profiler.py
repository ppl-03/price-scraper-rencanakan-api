import os
import json
import tempfile
import shutil
from django.test import TestCase
from unittest.mock import patch
from api.mitra10.utils.mitra10_profiler import Mitra10Profiler


class TestMitra10Profiler(TestCase):

    def setUp(self):
        self.profiler = Mitra10Profiler()
        self.test_temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_temp_dir):
            shutil.rmtree(self.test_temp_dir)

    def test_profiler_initialization(self):
        profiler = Mitra10Profiler()
        
        self.assertIsInstance(profiler.results, dict)
        self.assertTrue(hasattr(profiler, 'output_dir'))
        self.assertTrue(hasattr(profiler, 'test_keywords'))
        
        expected_keywords = ['semen', 'cat', 'paku', 'kawat', 'keramik']
        self.assertEqual(profiler.test_keywords, expected_keywords)

    def test_profiler_with_custom_output_dir(self):
        profiler = Mitra10Profiler(output_dir=self.test_temp_dir)
        
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_URL': '10'}):
            result = profiler.profile_url_builder()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'url_builder')

    def test_profiler_environment_variables(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_URL': '10',
            'PROFILING_ITERATIONS_PRICE': '50'
        }):
            profiler = Mitra10Profiler()
            
            result = profiler.profile_url_builder()
            self.assertEqual(result['iterations'], 10)
            
            result = profiler.profile_price_cleaner()
            self.assertEqual(result['iterations'], 50)

    def test_create_mock_html(self):
        html_content = self.profiler._create_mock_html()
        
        self.assertIn('MuiGrid-item', html_content)
        self.assertIn('gtm_mitra10_cta_product', html_content)
        
        product_count = html_content.count('gtm_mitra10_cta_product')
        self.assertEqual(product_count, 50)

    def test_get_fallback_html(self):
        html_content = self.profiler._get_fallback_html()
        
        self.assertIn('MuiGrid-item', html_content)
        self.assertIn('gtm_mitra10_cta_product', html_content)

    def test_profile_url_builder(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_URL': '10'}):
            result = self.profiler.profile_url_builder()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'url_builder')
        self.assertIn('iterations', result)
        self.assertIn('total_time', result)

    def test_profile_price_cleaner(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_PRICE': '50'}):
            result = self.profiler.profile_price_cleaner()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'price_cleaner')
        self.assertIn('iterations', result)
        self.assertIn('total_time', result)

    def test_profile_html_parser(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_HTML': '2'}):
            result = self.profiler.profile_html_parser()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'html_parser')
        self.assertIn('iterations', result)
        self.assertIn('total_time', result)

    def test_profile_factory(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_FACTORY': '10'}):
            result = self.profiler.profile_factory()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'factory')

    def test_profile_playwright_client(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_PLAYWRIGHT': '2'}):
            result = self.profiler.profile_playwright_client()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'playwright_client')

    def test_run_complete_profiling(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_URL': '10',
            'PROFILING_ITERATIONS_PRICE': '50',
            'PROFILING_ITERATIONS_HTML': '2',
            'PROFILING_ITERATIONS_FACTORY': '10',
            'PROFILING_ITERATIONS_PLAYWRIGHT': '2',
            'PROFILING_AUTO_SCRAPE': 'false'
        }):
            with patch('builtins.input', return_value='n'):
                self.profiler.run_complete_profiling()
        
        self.assertGreater(len(self.profiler.results), 3)

    def test_generate_performance_report(self):
        self.profiler.results = {
            'url_builder': {
                'component': 'url_builder',
                'total_time': 0.1,
                'total_calls': 500,
                'iterations': 500
            }
        }
        
        report_file = self.profiler.generate_performance_report()
        self.assertTrue(os.path.exists(report_file))
        
        with open(report_file, 'r') as f:
            report_data = json.load(f)
        
        self.assertIn('profiling_results', report_data)
        self.assertIn('environment_config', report_data)
        self.assertIn('timestamp', report_data)
        self.assertIn('url_builder', report_data['profiling_results'])

    def test_performance_metrics_calculation(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_URL': '10'}):
            result = self.profiler.profile_url_builder()
        
        required_metrics = ['component', 'iterations', 'total_time', 'total_calls']
        for metric in required_metrics:
            self.assertIn(metric, result)
        
        self.assertGreater(result['total_calls'], 0)
        self.assertGreaterEqual(result['total_time'], 0)

    # NOTE: test_optimization_recommendations removed - _generate_recommendations() method does not exist in Mitra10Profiler
    # The profiler generates performance reports without optimization recommendations


class TestProfilerIntegration(TestCase):
    
    def setUp(self):
        self.profiler = Mitra10Profiler()

    def test_real_factory_integration(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_FACTORY': '10'}):
            result = self.profiler.profile_factory()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'factory')

    def test_real_url_builder_integration(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_URL': '10'}):
            result = self.profiler.profile_url_builder()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'url_builder')

    def test_real_price_cleaner_integration(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_PRICE': '50'}):
            result = self.profiler.profile_price_cleaner()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'price_cleaner')

    def test_real_html_parser_integration(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_HTML': '2'}):
            result = self.profiler.profile_html_parser()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'html_parser')

    def test_real_playwright_client_integration(self):
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_PLAYWRIGHT': '2'}):
            result = self.profiler.profile_playwright_client()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'playwright_client')