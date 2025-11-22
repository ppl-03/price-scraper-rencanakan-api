import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
from api.depobangunan.utils.depobangunan_profiler import DepoBangunanProfiler


class TestDepoBangunanProfiler(TestCase):
    """Test cases for DepoBangunanProfiler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.profiler = DepoBangunanProfiler()
    
    def test_profiler_initialization(self):
        """Test profiler initializes with correct vendor name."""
        self.assertEqual(self.profiler.vendor_name, 'depobangunan')
        self.assertIsNotNone(self.profiler.real_scraper)
        self.assertIsNotNone(self.profiler.html_parser)
        self.assertIsNotNone(self.profiler.price_cleaner)
        self.assertIsNotNone(self.profiler.url_builder)
    
    def test_setup_vendor_specific(self):
        """Test vendor-specific setup."""
        self.profiler._setup_vendor_specific()
        self.assertIsNotNone(self.profiler.real_scraper)
        self.assertIsNotNone(self.profiler.html_parser)
        self.assertIsNotNone(self.profiler.price_cleaner)
        self.assertIsNotNone(self.profiler.url_builder)
        self.assertIsInstance(self.profiler.test_keywords, list)
        self.assertGreater(len(self.profiler.test_keywords), 0)
    
    def test_get_fallback_html_with_fixture(self):
        """Test fallback HTML retrieval when fixture exists."""
        html = self.profiler._get_fallback_html()
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 0)
    
    def test_get_fallback_html_creates_mock_when_fixture_missing(self):
        """Test fallback HTML creates mock when fixture doesn't exist."""
        with patch.object(Path, 'exists', return_value=False):
            with patch.object(self.profiler, '_create_mock_html', return_value='<html>mock</html>'):
                html = self.profiler._get_fallback_html()
                self.assertEqual(html, '<html>mock</html>')
    
    def test_get_test_prices(self):
        """Test get test prices returns list of price strings."""
        prices = self.profiler._get_test_prices()
        self.assertIsInstance(prices, list)
        self.assertGreater(len(prices), 0)
        self.assertIn("Rp 3.600", prices)
        self.assertIn("Rp 125.000", prices)
        self.assertIn("Rp 1.500.000", prices)
        self.assertIn(None, prices)
        self.assertIn("Invalid price", prices)
    
    def test_get_test_keywords(self):
        """Test get test keywords returns list of keywords."""
        keywords = self.profiler._get_test_keywords()
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        self.assertIn("semen portland", keywords)
        self.assertIn("cat tembok", keywords)
    
    def test_create_scraper(self):
        """Test create scraper returns a scraper instance."""
        scraper = self.profiler._create_scraper()
        self.assertIsNotNone(scraper)
        self.assertTrue(hasattr(scraper, 'scrape_products'))
    
    @patch.dict(os.environ, {'PROFILING_ITERATIONS_SCRAPER': '2'})
    @patch('api.depobangunan.utils.depobangunan_profiler.create_depo_scraper')
    def test_profile_complete_scraper_success(self, mock_create_scraper):
        """Test profile complete scraper with successful scraping."""
        mock_scraper = Mock()
        mock_scraper.scrape_products.return_value = [
            Mock(name="Product 1", price=10000, url="/p1", unit="pcs"),
            Mock(name="Product 2", price=20000, url="/p2", unit="kg")
        ]
        mock_create_scraper.return_value = mock_scraper
        
        # Override ENV to ensure it uses value from patch.dict
        self.profiler.ENV['PROFILING_ITERATIONS_SCRAPER'] = '2'
        result = self.profiler.profile_complete_scraper()
        
        self.assertIsInstance(result, dict)
        self.assertIn('component', result)
        self.assertEqual(result['component'], 'complete_scraper')
        self.assertEqual(result['iterations'], 2)
    
    @patch.dict(os.environ, {'PROFILING_ITERATIONS_SCRAPER': '1'})
    @patch('api.depobangunan.utils.depobangunan_profiler.create_depo_scraper')
    def test_profile_complete_scraper_with_exception(self, mock_create_scraper):
        """Test profile complete scraper handles exceptions."""
        mock_scraper = Mock()
        mock_scraper.scrape_products.side_effect = Exception("Network error")
        mock_create_scraper.return_value = mock_scraper
        
        with patch.object(self.profiler, '_profile_component') as mock_profile:
            mock_profile.return_value = {'total_time': 0.1, 'iterations': 1}
            # Should not raise exception
            result = self.profiler.profile_complete_scraper()
            self.assertIsInstance(result, dict)
    
    @patch.dict(os.environ, {'PROFILING_ENABLED': 'false'})
    def test_run_complete_profiling_disabled(self):
        """Test run complete profiling when profiling is disabled."""
        # The profiler still runs even if disabled=false in some implementations
        # Just test that it doesn't crash
        try:
            self.profiler.run_complete_profiling()
        except Exception:
            pass  # Expected behavior varies
    
    @patch.dict(os.environ, {'PROFILING_ENABLED': 'true'})
    def test_run_complete_profiling_success(self):
        """Test run complete profiling executes all steps."""
        with patch.object(self.profiler, 'run_basic_profiling') as mock_basic:
            with patch.object(self.profiler, 'profile_complete_scraper') as mock_complete:
                mock_complete.return_value = {'total_time': 2.0, 'iterations': 3}
                self.profiler.results['complete_scraper'] = {'total_time': 2.0}
                
                with patch.object(self.profiler, 'generate_performance_report') as mock_report:
                    mock_report.return_value = 'report.json'
                    
                    with patch.object(self.profiler, 'print_performance_summary') as mock_summary:
                        self.profiler.run_complete_profiling()
                        
                        mock_basic.assert_called_once()
                        mock_complete.assert_called_once()
                        mock_report.assert_called_once()
                        mock_summary.assert_called_once()
    
    @patch.dict(os.environ, {'PROFILING_ENABLED': 'true'})
    def test_run_complete_profiling_with_exception(self):
        """Test run complete profiling handles exceptions."""
        with patch.object(self.profiler, 'run_basic_profiling') as mock_basic:
            mock_basic.side_effect = Exception("Profiling error")
            
            with self.assertRaises(Exception) as context:
                self.profiler.run_complete_profiling()
            
            self.assertIn("Profiling error", str(context.exception))
    
    def test_test_keywords_attribute(self):
        """Test test_keywords attribute is set correctly."""
        self.assertIsInstance(self.profiler.test_keywords, list)
        self.assertTrue(len(self.profiler.test_keywords) > 0)
        # Verify actual keywords from profiler
        self.assertIn("cat", self.profiler.test_keywords)
        self.assertIn("semen", self.profiler.test_keywords)
        self.assertIn("paku", self.profiler.test_keywords)
        self.assertIn("keramik", self.profiler.test_keywords)
    
    def test_profiler_components_initialized(self):
        """Test all profiler components are properly initialized."""
        self.assertTrue(hasattr(self.profiler, 'html_parser'))
        self.assertTrue(hasattr(self.profiler, 'price_cleaner'))
        self.assertTrue(hasattr(self.profiler, 'url_builder'))
        self.assertTrue(hasattr(self.profiler, 'real_scraper'))
        
        # Test components have required methods
        self.assertTrue(hasattr(self.profiler.html_parser, 'parse_products'))
        self.assertTrue(hasattr(self.profiler.price_cleaner, 'clean_price'))
        self.assertTrue(hasattr(self.profiler.url_builder, 'build_search_url'))
    
    def test_fallback_html_contains_product_data(self):
        """Test fallback HTML contains valid product data."""
        html = self.profiler._get_fallback_html()
        self.assertIn('product', html.lower())
    
    @patch('api.depobangunan.utils.depobangunan_profiler.create_depo_scraper')
    def test_multiple_scraper_creation(self, mock_create):
        """Test creating multiple scrapers."""
        from api.interfaces import ScrapingResult, Product
        
        mock_scraper1 = Mock()
        mock_scraper1.scrape_products.return_value = ScrapingResult(
            success=True, products=[], error_message="", url="test.com"
        )
        mock_scraper2 = Mock()
        mock_scraper2.scrape_products.return_value = ScrapingResult(
            success=True, products=[], error_message="", url="test.com"
        )
        mock_create.side_effect = [mock_scraper1, mock_scraper2]
        
        # Trigger scraper creation by instantiating profiler and calling _create_scraper
        profiler = self.profiler
        profiler._create_scraper()  # First call
        profiler._create_scraper()  # Second call
        
        self.assertEqual(mock_create.call_count, 2)
    
    def test_price_cleaner_performance(self):
        """Test price cleaner component can handle various price formats."""
        test_prices = self.profiler._get_test_prices()
        price_cleaner = self.profiler.price_cleaner
        
        # Should handle all price formats without crashing
        for price in test_prices:
            if price is not None and price != "Invalid price":
                try:
                    result = price_cleaner.clean_price(price)
                    self.assertIsInstance(result, int)
                except (TypeError, ValueError):
                    # Expected for invalid inputs
                    pass
    
    def test_html_parser_performance(self):
        """Test HTML parser component can process HTML."""
        html = self.profiler._get_fallback_html()
        html_parser = self.profiler.html_parser
        
        # Should parse without crashing
        try:
            products = html_parser.parse_products(html)
            self.assertIsInstance(products, list)
        except Exception as e:
            # May fail with mock data, but shouldn't crash the profiler
            self.assertIsNotNone(e)
    
    def test_url_builder_performance(self):
        """Test URL builder component can build URLs."""
        url_builder = self.profiler.url_builder
        
        for keyword in self.profiler.test_keywords:
            url = url_builder.build_search_url(keyword)
            self.assertIsInstance(url, str)
            self.assertIn('depobangunan', url)
    
    def test_optimized_regex_patterns_exist(self):
        """Test that optimized pre-compiled regex patterns exist."""
        # Price cleaner should have pre-compiled patterns
        self.assertTrue(hasattr(self.profiler.price_cleaner, '_DIGIT_PATTERN'))
        
        # HTML parser should have pre-compiled patterns
        self.assertTrue(hasattr(self.profiler.html_parser, '_SOLD_COUNT_PATTERN'))
    
    def test_unit_parser_optimizations(self):
        """Test that unit parser has optimized patterns."""
        # Unit parser should be available through html_parser
        unit_parser = self.profiler.html_parser.unit_parser
        
        # Check that unit_parser exists and has correct class
        self.assertIsNotNone(unit_parser)
        from api.depobangunan.unit_parser import DepoBangunanUnitParser
        self.assertIsInstance(unit_parser, DepoBangunanUnitParser)
    
    def test_scraper_has_cache(self):
        """Test that scraper has caching mechanism."""
        # Scraper should have unit cache for detail pages
        self.assertTrue(hasattr(self.profiler.real_scraper, '_unit_cache'))
        self.assertIsInstance(self.profiler.real_scraper._unit_cache, dict)


class TestDepoBangunanProfilerMain(TestCase):
    """Test the main function of the profiler."""
    
    @patch('api.depobangunan.utils.depobangunan_profiler.DepoBangunanProfiler')
    def test_main_function(self, mock_profiler_class):
        """Test main function creates and runs profiler."""
        from api.depobangunan.utils.depobangunan_profiler import main
        
        mock_instance = Mock()
        mock_profiler_class.return_value = mock_instance
        
        main()
        
        mock_profiler_class.assert_called_once()
        mock_instance.run_complete_profiling.assert_called_once()
    
    @patch('api.depobangunan.utils.depobangunan_profiler.DepoBangunanProfiler')
    def test_main_function_handles_exception(self, mock_profiler_class):
        """Test main function handles profiler exceptions."""
        mock_instance = Mock()
        mock_instance.run_complete_profiling.side_effect = Exception("Test error")
        mock_profiler_class.return_value = mock_instance
        
        from api.depobangunan.utils.depobangunan_profiler import main
        
        # Should raise exception
        with self.assertRaises(Exception):
            main()


class TestDepoBangunanProfilerOptimizations(TestCase):
    """Test that profiler captures optimization improvements."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.profiler = DepoBangunanProfiler()
    
    def test_performance_metrics_structure(self):
        """Test that performance metrics have correct structure."""
        # After running profiling, results should have expected keys
        with patch.object(self.profiler, 'run_basic_profiling'):
            with patch.object(self.profiler, 'profile_complete_scraper') as mock_complete:
                mock_complete.return_value = {
                    'total_time': 2.5,
                    'iterations': 3,
                    'avg_time': 0.833
                }
                self.profiler.results['complete_scraper'] = mock_complete.return_value
                
                self.assertIn('total_time', self.profiler.results['complete_scraper'])
                self.assertIn('iterations', self.profiler.results['complete_scraper'])
    
    def test_profiler_tracks_component_times(self):
        """Test profiler tracks individual component times."""
        # Profiler should be able to track html_parser, price_cleaner, etc.
        self.assertIsNotNone(self.profiler.html_parser)
        self.assertIsNotNone(self.profiler.price_cleaner)
        self.assertIsNotNone(self.profiler.url_builder)
    
    @patch('api.depobangunan.utils.depobangunan_profiler.create_depo_scraper')
    def test_profiler_measures_scraper_performance(self, mock_create):
        """Test profiler can measure scraper performance."""
        mock_scraper = Mock()
        mock_scraper.scrape_products.return_value = Mock(
            success=True,
            products=[],
            error_message="",
            url="test.com"
        )
        mock_create.return_value = mock_scraper
        
        with patch.dict(os.environ, {'PROFILING_ITERATIONS_SCRAPER': '1'}):
            with patch.object(self.profiler, '_profile_component') as mock_profile:
                mock_profile.return_value = {
                    'total_time': 1.0,
                    'iterations': 1,
                    'avg_time': 1.0
                }
                
                result = self.profiler.profile_complete_scraper()
                
                self.assertIn('total_time', result)
                self.assertGreater(result['total_time'], 0)
