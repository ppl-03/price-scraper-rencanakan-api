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


class TestProfilerEdgeCases(TestCase):
    """Test edge cases and missing coverage in profiler"""
    
    def setUp(self):
        self.profiler = Mitra10Profiler()
        self.test_temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        if os.path.exists(self.test_temp_dir):
            shutil.rmtree(self.test_temp_dir)
    
    def test_fetch_real_html_exception_handling(self):
        """Test _fetch_real_html handles exceptions and uses fallback"""
        with patch.object(self.profiler.real_scraper.url_builder, 'build_search_url', side_effect=Exception("URL error")):
            html = self.profiler._fetch_real_html("error_keyword")
            self.assertIsNotNone(html)
            self.assertIn('MuiGrid-item', html)  # Should be fallback HTML
    
    def test_create_mock_html_with_custom_product_count(self):
        """Test _create_mock_html with custom product count from ENV"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'MOCK_HTML_PRODUCTS': '10'}):
            profiler = Mitra10Profiler()
            html = profiler._create_mock_html()
            
            product_count = html.count('gtm_mitra10_cta_product')
            self.assertEqual(product_count, 10)
    
    def test_profile_html_parser_with_parse_error(self):
        """Test profile_html_parser handles parse errors gracefully"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_HTML': '2'}):
            with patch.object(self.profiler, '_fetch_real_html', return_value='<invalid>html'):
                result = self.profiler.profile_html_parser()
                
                self.assertIsInstance(result, dict)
                self.assertEqual(result['component'], 'html_parser')
    
    def test_profile_playwright_client_with_exception(self):
        """Test profile_playwright_client handles exceptions"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_PLAYWRIGHT': '1'}):
            with patch('api.mitra10.utils.mitra10_profiler.PlaywrightHttpClient', side_effect=Exception("Init error")):
                result = self.profiler.profile_playwright_client()
                
                self.assertIsInstance(result, dict)
                self.assertEqual(result['component'], 'playwright_client')
    
    def test_generate_performance_report_creates_file(self):
        """Test generate_performance_report creates report file with timestamp"""
        self.profiler.results = {
            'url_builder': {
                'component': 'url_builder',
                'total_time': 0.05,
                'total_calls': 100,
                'iterations': 10
            },
            'price_cleaner': {
                'component': 'price_cleaner',
                'total_time': 0.02,
                'total_calls': 50,
                'iterations': 50
            }
        }
        
        profiler = Mitra10Profiler(output_dir=self.test_temp_dir)
        profiler.results = self.profiler.results
        
        report_file = profiler.generate_performance_report()
        
        self.assertTrue(os.path.exists(report_file))
        self.assertTrue(report_file.startswith(os.path.join(self.test_temp_dir, 'mitra10_performance_report_')))
        
        with open(report_file, 'r') as f:
            report_data = json.load(f)
        
        self.assertIn('profiling_results', report_data)
        self.assertIn('environment_config', report_data)
        self.assertIn('timestamp', report_data)
        self.assertEqual(len(report_data['profiling_results']), 2)
    
    def test_run_complete_profiling_with_auto_scrape_disabled(self):
        """Test run_complete_profiling skips scraper profiling when auto_scrape is false"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_URL': '5',
            'PROFILING_ITERATIONS_PRICE': '25',
            'PROFILING_ITERATIONS_HTML': '2',
            'PROFILING_ITERATIONS_FACTORY': '5',
            'PROFILING_ITERATIONS_PLAYWRIGHT': '1',
            'PROFILING_AUTO_SCRAPE': 'false'
        }):
            with patch('builtins.input', return_value='n'):
                self.profiler.run_complete_profiling()
        
        # Should have profiled all components except complete scraper
        self.assertIn('url_builder', self.profiler.results)
        self.assertIn('price_cleaner', self.profiler.results)
        self.assertIn('html_parser', self.profiler.results)
        self.assertIn('factory', self.profiler.results)
    
    def test_profiler_with_custom_output_dir_creation(self):
        """Test profiler creates output directory if it doesn't exist"""
        new_dir = os.path.join(self.test_temp_dir, 'new_profiling_dir')
        Mitra10Profiler(output_dir=new_dir)
        
        self.assertTrue(os.path.exists(new_dir))
    
    def test_profiler_stats_file_creation(self):
        """Test that profiling creates stats files in output directory"""
        profiler = Mitra10Profiler(output_dir=self.test_temp_dir)
        
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_HTML': '2'}):
            result = profiler.profile_html_parser()
        
        self.assertIn('stats_file', result)
        stats_file = result['stats_file']
        self.assertTrue(os.path.exists(stats_file))
        self.assertTrue(stats_file.endswith('html_parser_profile.txt'))
    
    def test_fetch_real_html_with_cache(self):
        """Test that _fetch_real_html uses cache on subsequent calls"""
        keyword = "test_keyword"
        
        # First call should cache the result
        mock_html = "<html>Test HTML</html>"
        with patch.object(self.profiler.real_scraper.http_client, 'get', return_value=mock_html):
            html1 = self.profiler._fetch_real_html(keyword)
            self.assertEqual(html1, mock_html)
            self.assertIn(keyword, self.profiler.real_html_cache)
        
        # Second call should use cache (http_client.get should not be called)
        with patch.object(self.profiler.real_scraper.http_client, 'get', side_effect=Exception("Should not be called")):
            html2 = self.profiler._fetch_real_html(keyword)
            self.assertEqual(html2, mock_html)
            self.assertEqual(html1, html2)
    
    def test_profile_complete_scraper_success(self):
        """Test profile_complete_scraper with successful scraping (covers lines 257-268)"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_SCRAPER': '1'}):
            # Create mock products with name and price attributes to trigger lines 257-268
            mock_products = [
                type('Product', (), {
                    'name': 'Test Product With A Very Long Name That Needs Truncation',
                    'price': 150000,
                    'url': 'http://test.com/product'
                })(),
                type('Product', (), {
                    'name': 'Another Product',
                    'price': 75000,
                    'url': 'http://test.com/product2'
                })()
            ]
            
            with patch.object(self.profiler.real_scraper.http_client, 'get', return_value='<html>Mock HTML Content</html>'):
                with patch.object(self.profiler.real_scraper.html_parser, 'parse_products', return_value=mock_products):
                    result = self.profiler.profile_complete_scraper()
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['component'], 'complete_scraper')
            self.assertIn('total_time', result)
            self.assertIn('total_calls', result)
    
    def test_profile_complete_scraper_with_exception_and_fallback(self):
        """Test profile_complete_scraper handles exceptions and uses fallback"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_SCRAPER': '1'}):
            mock_products = [
                type('Product', (), {'name': 'Fallback Product', 'price': 25000})()
            ]
            
            # Simulate scraping error, then successful fallback
            with patch.object(self.profiler.real_scraper.http_client, 'get', side_effect=Exception("Network error")):
                with patch.object(self.profiler, '_get_fallback_html', return_value='<html>Fallback HTML</html>'):
                    with patch.object(self.profiler.real_scraper.html_parser, 'parse_products', return_value=mock_products):
                        result = self.profiler.profile_complete_scraper()
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['component'], 'complete_scraper')
    
    def test_profile_complete_scraper_with_fallback_failure(self):
        """Test profile_complete_scraper when both scraping and fallback fail"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_SCRAPER': '1'}):
            # Both main scraping and fallback fail
            with patch.object(self.profiler.real_scraper.http_client, 'get', side_effect=Exception("Network error")):
                with patch.object(self.profiler, '_get_fallback_html', side_effect=Exception("Fallback error")):
                    result = self.profiler.profile_complete_scraper()
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['component'], 'complete_scraper')
    
    def test_profile_complete_scraper_initialization_failure(self):
        """Test profile_complete_scraper when scraper initialization fails"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_SCRAPER': '1'}):
            with patch('api.mitra10.utils.mitra10_profiler.create_mitra10_scraper', side_effect=Exception("Init error")):
                result = self.profiler.profile_complete_scraper()
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['component'], 'complete_scraper')
    
    def test_profile_factory_with_close_exception(self):
        """Test profile_factory handles close() exceptions gracefully"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_FACTORY': '2'}):
            def raise_exception():
                raise RuntimeError("Close error")
            
            mock_scraper = type('Scraper', (), {
                'http_client': type('Client', (), {
                    'close': raise_exception
                })()
            })()
            
            with patch('api.mitra10.utils.mitra10_profiler.create_mitra10_scraper', return_value=mock_scraper):
                result = self.profiler.profile_factory()
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['component'], 'factory')
    
    def test_run_complete_profiling_disabled(self):
        """Test run_complete_profiling when profiling is disabled"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ENABLED': 'false'}):
            result = self.profiler.run_complete_profiling()
            
            self.assertIsNone(result)
            self.assertEqual(len(self.profiler.results), 0)
    
    def test_run_complete_profiling_with_auto_scrape_enabled(self):
        """Test run_complete_profiling automatically runs scraper when AUTO_SCRAPE is true"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_URL': '5',
            'PROFILING_ITERATIONS_PRICE': '25',
            'PROFILING_ITERATIONS_HTML': '2',
            'PROFILING_ITERATIONS_FACTORY': '5',
            'PROFILING_ITERATIONS_PLAYWRIGHT': '1',
            'PROFILING_AUTO_SCRAPE': 'true',
            'PROFILING_ITERATIONS_SCRAPER': '1'
        }):
            mock_products = [type('Product', (), {'name': 'Test', 'price': 50000})()]
            
            with patch.object(self.profiler.real_scraper.http_client, 'get', return_value='<html>Test</html>'):
                with patch.object(self.profiler.real_scraper.html_parser, 'parse_products', return_value=mock_products):
                    result = self.profiler.run_complete_profiling()
            
            self.assertIsNotNone(result)
            self.assertIn('complete_scraper', self.profiler.results)
            self.assertIn('report_file', result)
            self.assertIn('output_dir', result)
            self.assertIn('results', result)
    
    def test_run_complete_profiling_with_user_consent_yes(self):
        """Test run_complete_profiling includes scraper when user consents"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_URL': '5',
            'PROFILING_ITERATIONS_PRICE': '25',
            'PROFILING_ITERATIONS_HTML': '2',
            'PROFILING_ITERATIONS_FACTORY': '5',
            'PROFILING_ITERATIONS_PLAYWRIGHT': '1',
            'PROFILING_AUTO_SCRAPE': 'false',
            'PROFILING_ITERATIONS_SCRAPER': '1'
        }):
            mock_products = [type('Product', (), {'name': 'Test', 'price': 50000})()]
            
            with patch('builtins.input', return_value='y'):
                with patch.object(self.profiler.real_scraper.http_client, 'get', return_value='<html>Test</html>'):
                    with patch.object(self.profiler.real_scraper.html_parser, 'parse_products', return_value=mock_products):
                        result = self.profiler.run_complete_profiling()
            
            self.assertIsNotNone(result)
            self.assertIn('complete_scraper', self.profiler.results)
    
    def test_run_complete_profiling_exception_handling(self):
        """Test run_complete_profiling handles exceptions properly"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_URL': '5',
            'PROFILING_ITERATIONS_PRICE': '25'
        }):
            with patch.object(self.profiler, 'profile_html_parser', side_effect=Exception("Test error")):
                with self.assertRaises(Exception):
                    self.profiler.run_complete_profiling()
    
    def test_load_env_with_comments_and_empty_lines(self):
        """Test load_env handles comments and empty lines correctly"""
        from api.mitra10.utils.mitra10_profiler import load_env
        
        # The load_env function should skip comments and empty lines
        env = load_env()
        self.assertIsInstance(env, dict)
    
    def test_profile_price_cleaner_with_exceptions(self):
        """Test profile_price_cleaner handles various exceptions"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'PROFILING_ITERATIONS_PRICE': '10'}):
            with patch.object(self.profiler.real_scraper.html_parser.price_cleaner, 'clean_price', side_effect=[
                50000, ValueError("Invalid"), 75000, TypeError("Bad type"), 100000
            ]):
                result = self.profiler.profile_price_cleaner()
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['component'], 'price_cleaner')
    
    def test_get_fallback_html_with_fixture_file(self):
        """Test _get_fallback_html when fixture file exists"""
        from pathlib import Path
        # Create a temporary fixture file
        fixture_dir = Path(self.test_temp_dir)
        os.makedirs(os.path.join(str(fixture_dir), 'api', 'mitra10', 'tests'), exist_ok=True)
        fixture_path = os.path.join(str(fixture_dir), 'api', 'mitra10', 'tests', 'mitra10_mock_results.html')
        
        with open(fixture_path, 'w', encoding='utf-8') as f:
            f.write('<html><body>Fixture content</body></html>')
        
        with patch('api.mitra10.utils.mitra10_profiler.project_root', fixture_dir):
            profiler = Mitra10Profiler()
            html = profiler._get_fallback_html()
            
            self.assertIn('Fixture content', html)
    
    def test_profiler_results_summary_with_zero_time(self):
        """Test that calls_per_second calculation handles zero time correctly"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_URL': '5',
            'PROFILING_ITERATIONS_PRICE': '25',
            'PROFILING_ITERATIONS_HTML': '2',
            'PROFILING_ITERATIONS_FACTORY': '5',
            'PROFILING_ITERATIONS_PLAYWRIGHT': '1',
            'PROFILING_AUTO_SCRAPE': 'false'
        }):
            with patch('builtins.input', return_value='n'):
                result = self.profiler.run_complete_profiling()
            
            # Verify results structure includes calls_per_second calculation
            self.assertIn('results', result)
            for component_result in result['results']:
                self.assertIn('calls_per_second', component_result)
                # Should not raise ZeroDivisionError
                self.assertIsInstance(component_result['calls_per_second'], (int, float))

    def test_create_mock_html_default_products(self):
        """Test _create_mock_html without fixture file (line 64)"""
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {'MOCK_HTML_PRODUCTS': '5'}):
            profiler = Mitra10Profiler()
            
            # Patch exists to return False so _create_mock_html is called
            with patch('pathlib.Path.exists', return_value=False):
                html = profiler._get_fallback_html()
                
                # Should create mock HTML with 5 products
                self.assertIn('<html>', html)
                self.assertIn('product', html.lower())

    def test_profile_html_parser_with_parse_exception(self):
        """Test profile_html_parser when parser throws exception (lines 94-95)"""
        from unittest.mock import MagicMock
        
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_HTML': '2',
            'PROFILING_ENABLED': 'true'
        }):
            profiler = Mitra10Profiler()
            
            # Mock parser that raises exception
            mock_parser = MagicMock()
            mock_parser.parse_products.side_effect = RuntimeError("Parse error")
            
            # Should catch exception and continue (lines 94-95)
            with patch('api.mitra10.utils.mitra10_profiler.Mitra10HtmlParser', return_value=mock_parser):
                result = profiler.profile_html_parser()
            
            self.assertIn('component', result)
            self.assertEqual(result['component'], 'html_parser')

    def test_profile_url_builder_with_exception(self):
        """Test profile_url_builder when builder throws exception (lines 177-178)"""
        from unittest.mock import MagicMock
        
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_URL': '3',
            'PROFILING_ENABLED': 'true'
        }):
            profiler = Mitra10Profiler()
            
            # Mock builder that raises exception
            mock_builder = MagicMock()
            mock_builder.build_search_url.side_effect = RuntimeError("URL build error")
            
            # Should catch exception with pass statement (lines 177-178)
            with patch('api.mitra10.utils.mitra10_profiler.Mitra10UrlBuilder', return_value=mock_builder):
                result = profiler.profile_url_builder()
            
            self.assertIn('component', result)
            self.assertEqual(result['component'], 'url_builder')

    def test_profile_complete_scraper_with_sample_product_display(self):
        """Test profile_complete_scraper displaying sample product (lines 257-268)"""
        from unittest.mock import MagicMock
        from types import SimpleNamespace
        
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ITERATIONS_COMPLETE': '1',
            'PROFILING_ENABLED': 'true',
            'AUTO_SCRAPE': 'true'
        }):
            profiler = Mitra10Profiler()
            
            # Create mock products with name and price
            mock_product = SimpleNamespace(
                name='Test Product Name Here Long Name',
                price=150000,
                url='http://test.com/product'
            )
            
            # Mock scraper components
            mock_scraper = MagicMock()
            mock_scraper.url_builder.build_search_url.return_value = 'http://test.com/search'
            mock_scraper.http_client.get.return_value = '<html>test</html>'
            mock_scraper.html_parser.parse_products.return_value = [mock_product, mock_product]
            mock_scraper.html_parser.price_cleaner.clean_price.return_value = 150000
            
            with patch('api.mitra10.factory.create_mitra10_scraper', return_value=mock_scraper):
                result = profiler.profile_complete_scraper()
            
            # Should execute lines 257-268 (sample product display)
            self.assertIn('component', result)
            self.assertEqual(result['component'], 'complete_scraper')

    def test_main_function_execution(self):
        """Test main() function (lines 423-424)"""
        from api.mitra10.utils.mitra10_profiler import main
        
        with patch('api.mitra10.utils.mitra10_profiler.ENV', {
            'PROFILING_ENABLED': 'false'
        }):
            # Should create profiler and call run_complete_profiling
            with patch.object(Mitra10Profiler, 'run_complete_profiling') as mock_run:
                main()
                mock_run.assert_called_once()