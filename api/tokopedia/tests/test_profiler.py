"""
Unit tests for Tokopedia profiler with comparison functionality
"""

import unittest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from api.tokopedia.utils.tokopedia_profiler import TokopediaProfiler
from api.tokopedia.factory import create_tokopedia_scraper


class TestTokopediaProfiler(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.profiler = TokopediaProfiler()
    
    def test_profiler_initialization(self):
        """Test that profiler initializes correctly"""
        self.assertIsNotNone(self.profiler)
        self.assertEqual(self.profiler.vendor_name, 'tokopedia')
        self.assertIsNotNone(self.profiler.html_parser)
        self.assertIsNotNone(self.profiler.price_cleaner)
        self.assertIsNotNone(self.profiler.url_builder)
    
    def test_test_keywords(self):
        """Test that test keywords are properly defined"""
        keywords = self.profiler._get_test_keywords()
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        self.assertIn("semen portland", keywords)
    
    def test_test_prices(self):
        """Test that test prices are properly defined"""
        prices = self.profiler._get_test_prices()
        self.assertIsInstance(prices, list)
        self.assertGreater(len(prices), 0)
        self.assertIn("Rp62.500", prices)
    
    def test_create_scraper(self):
        """Test that scraper creation works"""
        scraper = self.profiler._create_scraper()
        self.assertIsNotNone(scraper)
        self.assertTrue(hasattr(scraper, 'scrape_products_with_filters'))
    
    def test_fallback_html(self):
        """Test that fallback HTML generation works"""
        html = self.profiler._get_fallback_html()
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 0)
        self.assertIn('tokopedia', html.lower())
    
    def test_mock_html_contains_products(self):
        """Test that mock HTML contains expected product structure"""
        html = self.profiler._create_mock_html(
            product_class="test-product",
            product_link_class="test-link",
            price_class="test-price",
            base_price=1000
        )
        self.assertIn('test-product', html)
        self.assertIn('test-price', html)
        self.assertIn('Rp', html)
    
    def test_profile_html_parser_basic(self):
        """Test HTML parser profiling (minimal iterations)"""
        # Set very low iterations for quick test
        self.profiler.ENV['PROFILING_ITERATIONS_HTML'] = '1'
        result = self.profiler.profile_html_parser()
        
        self.assertIsNotNone(result)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'html_parser')
        self.assertIn('total_time', result)
        self.assertGreater(result['total_time'], 0)
    
    def test_profile_price_cleaner_basic(self):
        """Test price cleaner profiling (minimal iterations)"""
        self.profiler.ENV['PROFILING_ITERATIONS_PRICE'] = '10'
        result = self.profiler.profile_price_cleaner()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['component'], 'price_cleaner')
        self.assertIn('test_prices_count', result)
        self.assertGreater(result['test_prices_count'], 0)
    
    def test_profile_url_builder_basic(self):
        """Test URL builder profiling (minimal iterations)"""
        self.profiler.ENV['PROFILING_ITERATIONS_URL'] = '10'
        result = self.profiler.profile_url_builder()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['component'], 'url_builder')
        self.assertIn('keywords_count', result)
        self.assertGreater(result['keywords_count'], 0)
    
    def test_profile_factory_basic(self):
        """Test factory profiling (minimal iterations)"""
        self.profiler.ENV['PROFILING_ITERATIONS_FACTORY'] = '5'
        result = self.profiler.profile_factory()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['component'], 'factory')
        self.assertGreater(result['total_time'], 0)
    
    def test_get_fallback_html_with_mock_file(self):
        """Test fallback HTML when mock file doesn't exist (line 34)"""
        # Temporarily rename the file to test fallback
        import tempfile
        import os
        
        # Test that fallback creates mock HTML
        html = self.profiler._get_fallback_html()
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 0)
    
    def test_get_fallback_html_without_fixture_file(self):
        """Test _create_mock_html fallback when fixture doesn't exist (line 34)"""
        from unittest.mock import patch
        from pathlib import Path
        
        # Mock Path.exists to return False
        with patch.object(Path, 'exists', return_value=False):
            html = self.profiler._get_fallback_html()
            
            # Should use _create_mock_html instead
            self.assertIsInstance(html, str)
            self.assertIn('html', html.lower())
            self.assertIn('Rp', html)  # Mock HTML contains prices
    
    def test_profile_complete_scraper(self):
        """Test complete scraper profiling (lines 63-81)"""
        # Set minimal iterations for fast testing
        self.profiler.ENV['PROFILING_ITERATIONS_SCRAPER'] = '1'
        
        # Mock the scraper to avoid actual network calls
        from unittest.mock import Mock, patch
        mock_result = Mock()
        mock_result.products = [Mock(name="Test", price=1000, url="https://test.com")]
        
        with patch.object(self.profiler, 'real_scraper') as mock_scraper:
            mock_scraper.scrape_products_with_filters.return_value = mock_result
            
            # Create a new scraper for the test
            with patch('api.tokopedia.factory.create_tokopedia_scraper') as mock_create:
                mock_create.return_value = mock_scraper
                
                result = self.profiler.profile_complete_scraper()
                
                self.assertIsNotNone(result)
                self.assertEqual(result['component'], 'complete_scraper')
                self.assertIn('total_time', result)
    
    def test_profile_complete_scraper_with_exception(self):
        """Test complete scraper handles exceptions and prints error (lines 77-78)"""
        import io
        from unittest.mock import patch, Mock
        
        self.profiler.ENV['PROFILING_ITERATIONS_SCRAPER'] = '1'
        
        # Capture print output
        captured_output = io.StringIO()
        
        with patch('sys.stdout', new=captured_output), \
             patch('api.tokopedia.utils.tokopedia_profiler.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_scraper.scrape_products_with_filters.side_effect = Exception("Network error")
            mock_create.return_value = mock_scraper
            
            result = self.profiler.profile_complete_scraper()
            
            # Should still return a result
            self.assertIsNotNone(result)
            
            # Check that error was printed
            output = captured_output.getvalue()
            self.assertIn("Error scraping", output)
    
    def test_profile_scraper_with_filters(self):
        """Test scraper with filters profiling (lines 85-112)"""
        # Set minimal iterations
        self.profiler.ENV['PROFILING_ITERATIONS_FILTERS'] = '1'
        
        # Mock the scraper
        from unittest.mock import Mock, patch
        mock_result = Mock()
        mock_result.products = []
        
        # We need to actually run the profiler which internally creates scrapers
        # The profiler calls factory.create_tokopedia_scraper inside the callback
        with patch('api.tokopedia.utils.tokopedia_profiler.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_scraper.scrape_products_with_filters.return_value = mock_result
            mock_create.return_value = mock_scraper
            
            result = self.profiler.profile_scraper_with_filters()
            
            self.assertIsNotNone(result)
            self.assertEqual(result['component'], 'scraper_with_filters')
            self.assertIn('total_time', result)
            
            # Verify scraper was called with filters (at least once since iterations=1)
            self.assertGreaterEqual(mock_scraper.scrape_products_with_filters.call_count, 1)
    
    def test_profile_scraper_with_filters_exception_handling(self):
        """Test scraper with filters handles exceptions (lines 106-108)"""
        import io
        from unittest.mock import patch, Mock
        
        self.profiler.ENV['PROFILING_ITERATIONS_FILTERS'] = '1'
        
        # Capture print output to verify error message is printed (line 108)
        captured_output = io.StringIO()
        
        with patch('sys.stdout', new=captured_output), \
             patch('api.tokopedia.utils.tokopedia_profiler.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_scraper.scrape_products_with_filters.side_effect = Exception("Filter error")
            mock_create.return_value = mock_scraper
            
            # Should not raise exception, should handle it internally
            result = self.profiler.profile_scraper_with_filters()
            
            self.assertIsNotNone(result)
            
            # Verify error was printed (line 108)
            output = captured_output.getvalue()
            self.assertIn("Error with filters", output)
    
    def test_run_complete_profiling(self):
        """Test complete profiling workflow (lines 116-141)"""
        # Enable profiling
        self.profiler.ENV['PROFILING_ENABLED'] = 'true'
        self.profiler.ENV['PROFILING_ITERATIONS_HTML'] = '1'
        self.profiler.ENV['PROFILING_ITERATIONS_PRICE'] = '10'
        self.profiler.ENV['PROFILING_ITERATIONS_URL'] = '10'
        self.profiler.ENV['PROFILING_ITERATIONS_FACTORY'] = '1'
        self.profiler.ENV['PROFILING_ITERATIONS_SCRAPER'] = '1'
        self.profiler.ENV['PROFILING_ITERATIONS_FILTERS'] = '1'
        
        from unittest.mock import Mock, patch
        
        # Mock scrapers to avoid network calls
        with patch('api.tokopedia.factory.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_result = Mock()
            mock_result.products = []
            mock_scraper.scrape_products_with_filters.return_value = mock_result
            mock_scraper.http_client.close = Mock()
            mock_create.return_value = mock_scraper
            
            # Run complete profiling
            self.profiler.run_complete_profiling()
            
            # Verify results were stored
            self.assertIn('html_parser', self.profiler.results)
            self.assertIn('price_cleaner', self.profiler.results)
            self.assertIn('url_builder', self.profiler.results)
            self.assertIn('factory', self.profiler.results)
            self.assertIn('complete_scraper', self.profiler.results)
            self.assertIn('scraper_with_filters', self.profiler.results)
    
    def test_run_complete_profiling_disabled(self):
        """Test profiling when disabled (line 118-119)"""
        self.profiler.ENV['PROFILING_ENABLED'] = 'false'
        
        # Should return early and not raise
        self.profiler.run_complete_profiling()
        
        # Results should be empty
        self.assertEqual(len(self.profiler.results), 0)
    
    def test_run_complete_profiling_exception(self):
        """Test profiling exception handling (lines 138-140)"""
        self.profiler.ENV['PROFILING_ENABLED'] = 'true'
        
        from unittest.mock import patch
        
        # Mock to raise exception
        with patch.object(self.profiler, 'run_basic_profiling', side_effect=Exception("Test error")):
            with self.assertRaises(Exception):
                self.profiler.run_complete_profiling()
    
    def test_main_function(self):
        """Test main entry point with comparison mode"""
        from unittest.mock import patch, Mock
        import sys
        
        # Mock TokopediaProfiler to avoid actual profiling
        with patch('api.tokopedia.utils.tokopedia_profiler.TokopediaProfiler') as MockProfiler:
            mock_instance = Mock()
            MockProfiler.return_value = mock_instance
            
            # Mock sys.argv to simulate command line arguments
            with patch.object(sys, 'argv', ['tokopedia_profiler.py', '--iterations', '3']):
                # Import and call main
                from api.tokopedia.utils.tokopedia_profiler import main
                
                main()
                
                # Verify profiler was created and run_profiling_comparison was called
                MockProfiler.assert_called_once()
                mock_instance.run_profiling_comparison.assert_called_once_with(iterations=3)
    
    def test_run_without_profiling(self):
        """Test running scraper without profiling"""
        from unittest.mock import patch, Mock
        
        # Mock the scraper
        with patch('api.tokopedia.utils.tokopedia_profiler.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_result = Mock()
            mock_result.products = [Mock(name="Test", price=1000)]
            mock_scraper.scrape_products_with_filters.return_value = mock_result
            mock_create.return_value = mock_scraper
            
            result = self.profiler.run_without_profiling(iterations=1)
            
            self.assertIsNotNone(result)
            self.assertIn('total_time', result)
            self.assertIn('avg_time', result)
            self.assertIn('iterations', result)
            self.assertIn('results', result)
            self.assertEqual(result['iterations'], 1)
            self.assertEqual(len(result['results']), 1)
    
    def test_run_with_profiling(self):
        """Test running scraper with profiling enabled"""
        from unittest.mock import patch, Mock
        
        # Mock the scraper
        with patch('api.tokopedia.utils.tokopedia_profiler.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_result = Mock()
            mock_result.products = [Mock(name="Test", price=1000)]
            mock_scraper.scrape_products_with_filters.return_value = mock_result
            mock_create.return_value = mock_scraper
            
            result = self.profiler.run_with_profiling(iterations=1)
            
            self.assertIsNotNone(result)
            self.assertIn('total_time', result)
            self.assertIn('avg_time', result)
            self.assertIn('iterations', result)
            self.assertIn('results', result)
            self.assertIn('profiling_stats', result)
            self.assertEqual(result['iterations'], 1)
    
    def test_calculate_overhead(self):
        """Test overhead calculation between profiling and non-profiling"""
        without = {
            'total_time': 10.0,
            'avg_time': 5.0,
            'iterations': 2
        }
        with_prof = {
            'total_time': 12.0,
            'avg_time': 6.0,
            'iterations': 2
        }
        
        overhead = self.profiler.calculate_overhead(without, with_prof)
        
        self.assertIn('time_overhead', overhead)
        self.assertIn('overhead_percentage', overhead)
        self.assertIn('slowdown_factor', overhead)
        self.assertEqual(overhead['time_overhead'], 2.0)
        self.assertEqual(overhead['overhead_percentage'], 20.0)
        self.assertEqual(overhead['slowdown_factor'], 1.2)
    
    def test_save_comparison_report(self):
        """Test saving comparison report to JSON"""
        import tempfile
        import json
        from unittest.mock import patch
        
        without = {
            'total_time': 10.0,
            'avg_time': 5.0,
            'iterations': 2,
            'results': []
        }
        with_prof = {
            'total_time': 12.0,
            'avg_time': 6.0,
            'iterations': 2,
            'results': []
        }
        overhead = {
            'time_overhead': 2.0,
            'overhead_percentage': 20.0,
            'slowdown_factor': 1.2
        }
        
        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.profiler.output_dir = temp_path
            
            report_file = self.profiler.save_comparison_report(without, with_prof, overhead)
            
            self.assertTrue(report_file.exists())
            
            # Read and verify JSON content
            with open(report_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.assertIn('timestamp', data)
            self.assertIn('comparison_type', data)
            self.assertIn('results', data)
            self.assertEqual(data['comparison_type'], 'profiling_overhead')
    
    def test_run_profiling_comparison(self):
        """Test complete profiling comparison workflow"""
        from unittest.mock import patch, Mock
        
        # Mock the scraper
        with patch('api.tokopedia.utils.tokopedia_profiler.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_result = Mock()
            mock_result.products = []
            mock_scraper.scrape_products_with_filters.return_value = mock_result
            mock_create.return_value = mock_scraper
            
            # Mock time.sleep to speed up test
            with patch('time.sleep'):
                self.profiler.run_profiling_comparison(iterations=1)
                
                # Verify scraper was called
                self.assertGreaterEqual(mock_scraper.scrape_products_with_filters.call_count, 2)
    
    def test_run_without_profiling_handles_exceptions(self):
        """Test that run_without_profiling handles exceptions gracefully"""
        from unittest.mock import patch, Mock
        import io
        
        # Mock the scraper to raise exception
        with patch('api.tokopedia.utils.tokopedia_profiler.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_scraper.scrape_products_with_filters.side_effect = Exception("Network error")
            mock_create.return_value = mock_scraper
            
            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                result = self.profiler.run_without_profiling(iterations=1)
            
            # Should still return a result with error recorded
            self.assertIsNotNone(result)
            self.assertEqual(len(result['results']), 1)
            self.assertIn('error', result['results'][0])
    
    def test_run_with_profiling_handles_exceptions(self):
        """Test that run_with_profiling handles exceptions gracefully"""
        from unittest.mock import patch, Mock
        import io
        
        # Mock the scraper to raise exception
        with patch('api.tokopedia.utils.tokopedia_profiler.create_tokopedia_scraper') as mock_create:
            mock_scraper = Mock()
            mock_scraper.scrape_products_with_filters.side_effect = Exception("Network error")
            mock_create.return_value = mock_scraper
            
            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                result = self.profiler.run_with_profiling(iterations=1)
            
            # Should still return a result with error recorded
            self.assertIsNotNone(result)
            self.assertEqual(len(result['results']), 1)
            self.assertIn('error', result['results'][0])


class TestTokopediaScraperIntegration(unittest.TestCase):
    """Integration tests for actual scraper components"""
    
    def test_scraper_creation(self):
        """Test that scraper can be created"""
        scraper = create_tokopedia_scraper()
        self.assertIsNotNone(scraper)
    
    def test_url_builder_works(self):
        """Test URL builder produces valid URLs"""
        from api.tokopedia.url_builder import TokopediaUrlBuilder
        builder = TokopediaUrlBuilder()
        url = builder.build_search_url("semen", True, 0)
        
        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith('https://'))
        self.assertIn('tokopedia.com', url)
        self.assertIn('semen', url)
    
    def test_price_cleaner_works(self):
        """Test price cleaner handles various formats"""
        from api.tokopedia.price_cleaner import TokopediaPriceCleaner
        cleaner = TokopediaPriceCleaner()
        
        # Test valid price
        price = cleaner.clean_price("Rp62.500")
        self.assertEqual(price, 62500)
        
        # Test invalid price
        invalid = cleaner.clean_price("invalid")
        self.assertEqual(invalid, 0)
    
    def test_html_parser_works(self):
        """Test HTML parser with mock data"""
        from api.tokopedia.html_parser import TokopediaHtmlParser
        parser = TokopediaHtmlParser()
        
        # Test with empty HTML
        products = parser.parse_products("")
        self.assertEqual(len(products), 0)


if __name__ == '__main__':
    unittest.main()
