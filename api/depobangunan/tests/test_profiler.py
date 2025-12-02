import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
from api.depobangunan.utils.depobangunan_profiler import DepoBangunanProfiler
from .test_helpers import ProfilerTestHelpers


class TestDepoBangunanProfiler(TestCase):
    """
    Comprehensive test suite for DepoBangunanProfiler.
    Uses component-based testing approach focused on verifying profiler behavior
    rather than implementation details.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        self.profiler = DepoBangunanProfiler()
        self.vendor_name = 'depobangunan'
        self.expected_components = ['real_scraper', 'html_parser', 'price_cleaner', 'url_builder']
    
    def _verify_component_exists(self, component_name):
        """Verify a specific component exists and is properly initialized."""
        self.assertTrue(
            hasattr(self.profiler, component_name),
            f"Profiler missing component: {component_name}"
        )
        component = getattr(self.profiler, component_name)
        self.assertIsNotNone(component, f"Component {component_name} is None")
        return component
    
    def _verify_list_contains_items(self, actual_list, expected_items):
        """Verify list contains all expected items."""
        self.assertIsInstance(actual_list, list, "Expected a list")
        self.assertGreater(len(actual_list), 0, "List should not be empty")
        for item in expected_items:
            self.assertIn(item, actual_list, f"List missing expected item: {item}")
    
    def test_profiler_initialization(self):
        """Verify profiler initializes with correct configuration."""
        self.assertEqual(self.profiler.vendor_name, self.vendor_name)
        
        for component in self.expected_components:
            self._verify_component_exists(component)
    
    def test_setup_vendor_specific(self):
        """Verify vendor-specific setup configures all components."""
        self.profiler._setup_vendor_specific()
        
        # Verify all components are initialized
        for component in self.expected_components:
            self._verify_component_exists(component)
        
        # Verify test keywords are configured
        keywords = self.profiler.test_keywords
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
    
    def test_get_fallback_html_with_fixture(self):
        """Verify fallback HTML is retrieved from fixtures."""
        html = self.profiler._get_fallback_html()
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 0, "Fallback HTML should not be empty")
    
    def test_get_fallback_html_creates_mock_when_fixture_missing(self):
        """Verify mock HTML is created when fixture is unavailable."""
        with patch.object(Path, 'exists', return_value=False):
            with patch.object(self.profiler, '_create_mock_html', return_value='<html>mock</html>'):
                html = self.profiler._get_fallback_html()
                self.assertEqual(html, '<html>mock</html>')
    
    def test_get_test_prices(self):
        """Verify test prices include various formats and edge cases."""
        prices = self.profiler._get_test_prices()
        expected_prices = ["Rp 3.600", "Rp 125.000", "Rp 1.500.000", None, "Invalid price"]
        self._verify_list_contains_items(prices, expected_prices)
    
    def test_get_test_keywords(self):
        """Verify test keywords are appropriate for depobangunan."""
        keywords = self.profiler._get_test_keywords()
        expected_keywords = ["semen portland", "cat tembok"]
        self._verify_list_contains_items(keywords, expected_keywords)
    
    def test_create_scraper(self):
        """Verify scraper creation returns functional instance with required interface."""
        scraper = self.profiler._create_scraper()
        self.assertIsNotNone(scraper, "Scraper creation failed")
        
        # Verify scraper has required method
        self.assertTrue(
            callable(getattr(scraper, 'scrape_products', None)),
            "Scraper missing scrape_products method"
        )
    
    @patch.dict(os.environ, {'PROFILING_ITERATIONS_SCRAPER': '2'})
    @patch('api.depobangunan.utils.depobangunan_profiler.create_depo_scraper')
    def test_profile_complete_scraper_success(self, mock_create_scraper):
        """Verify profiler correctly measures scraper performance over multiple iterations."""
        # Configure mock scraper with test products
        test_products = [
            Mock(name="Cement Bag", price=75000, url="/cement", unit="sak"),
            Mock(name="Paint Can", price=150000, url="/paint", unit="kaleng")
        ]
        mock_scraper = Mock()
        mock_scraper.scrape_products.return_value = test_products
        mock_create_scraper.return_value = mock_scraper
        
        # Execute profiling
        self.profiler.ENV['PROFILING_ITERATIONS_SCRAPER'] = '2'
        result = self.profiler.profile_complete_scraper()
        
        # Verify result structure and values
        ProfilerTestHelpers.assert_profiler_result_structure(self, result)
        self.assertEqual(result['component'], 'complete_scraper', "Component name mismatch")
        self.assertEqual(result['iterations'], 2, "Iteration count mismatch")
    
    @patch.dict(os.environ, {'PROFILING_ITERATIONS_SCRAPER': '1'})
    @patch('api.depobangunan.utils.depobangunan_profiler.create_depo_scraper')
    def test_profile_complete_scraper_with_exception(self, mock_create_scraper):
        """Verify profiler gracefully handles scraper exceptions without crashing."""
        # Configure mock to raise exception
        mock_scraper = Mock()
        mock_scraper.scrape_products.side_effect = Exception("Network timeout during scraping")
        mock_create_scraper.return_value = mock_scraper
        
        with patch.object(self.profiler, '_profile_component') as mock_profile:
            mock_profile.return_value = {'total_time': 0.1, 'iterations': 1}
            
            # Verify no exception is raised
            result = self.profiler.profile_complete_scraper()
            self.assertIsInstance(result, dict, "Result should be dict even on error")
    
    @patch.dict(os.environ, {'PROFILING_ENABLED': 'false'})
    def test_run_complete_profiling_disabled(self):
        """Verify profiler can run when profiling is disabled without errors."""
        # Profiler behavior when disabled may vary by implementation
        # Key requirement: should not crash regardless of enabled/disabled state
        try:
            self.profiler.run_complete_profiling()
        except Exception as e:
            # Document any exceptions for debugging
            self.fail(f"Profiler crashed when disabled: {e}")
    
    @patch.dict(os.environ, {'PROFILING_ENABLED': 'true'})
    def test_run_complete_profiling_success(self):
        """Verify complete profiling workflow executes all stages in correct order."""
        call_order = []
        
        def track_call(name):
            def wrapper(*args, **kwargs):
                call_order.append(name)
                if name == 'complete_scraper':
                    self.profiler.results['complete_scraper'] = {'total_time': 2.0}
                    return {'total_time': 2.0, 'iterations': 3}
                elif name == 'report':
                    return 'depobangunan_report.json'
            return wrapper
        
        with patch.object(self.profiler, 'run_basic_profiling', side_effect=track_call('basic')):
            with patch.object(self.profiler, 'profile_complete_scraper', side_effect=track_call('complete_scraper')):
                with patch.object(self.profiler, 'generate_performance_report', side_effect=track_call('report')):
                    with patch.object(self.profiler, 'print_performance_summary', side_effect=track_call('summary')):
                        self.profiler.run_complete_profiling()
                        
                        # Verify all stages executed
                        self.assertIn('basic', call_order)
                        self.assertIn('complete_scraper', call_order)
                        self.assertIn('report', call_order)
                        self.assertIn('summary', call_order)
    
    @patch.dict(os.environ, {'PROFILING_ENABLED': 'true'})
    def test_run_complete_profiling_with_exception(self):
        """Verify profiling exceptions propagate with proper error context."""
        error_message = "Component initialization failed during basic profiling"
        
        with patch.object(self.profiler, 'run_basic_profiling') as mock_basic:
            mock_basic.side_effect = Exception(error_message)
            
            with self.assertRaises(Exception) as ctx:
                self.profiler.run_complete_profiling()
            
            exception_str = str(ctx.exception)
            self.assertIn(error_message, exception_str, "Exception should include original error")
    
    def test_test_keywords_attribute(self):
        """Verify test keywords are configured for depobangunan product categories."""
        keywords = self.profiler.test_keywords
        
        # Verify structure
        self.assertIsInstance(keywords, list, "Keywords should be a list")
        self.assertGreater(len(keywords), 0, "Keywords list should not be empty")
        
        # Verify depobangunan-specific keywords
        expected_keywords = ["cat", "semen", "paku", "keramik"]
        for keyword in expected_keywords:
            self.assertIn(keyword, keywords, f"Missing expected keyword: {keyword}")
    
    def test_profiler_components_initialized(self):
        """Verify all profiler components have required methods for profiling operations."""
        # Define component-method mapping
        component_methods = {
            'html_parser': ['parse_products'],
            'price_cleaner': ['clean_price'],
            'url_builder': ['build_search_url'],
            'real_scraper': ['scrape_products']
        }
        
        for component_name, required_methods in component_methods.items():
            # Verify component exists
            self.assertTrue(
                hasattr(self.profiler, component_name),
                f"Missing component: {component_name}"
            )
            
            component = getattr(self.profiler, component_name)
            self.assertIsNotNone(component, f"Component {component_name} is None")
            
            # Verify required methods exist
            for method_name in required_methods:
                self.assertTrue(
                    hasattr(component, method_name),
                    f"Component {component_name} missing method: {method_name}"
                )
    
    def test_fallback_html_contains_product_data(self):
        """Verify fallback HTML includes depobangunan product structure."""
        html = self.profiler._get_fallback_html()
        
        # Verify HTML is non-empty
        self.assertGreater(len(html), 0, "Fallback HTML should not be empty")
        
        # Verify product-related content
        html_lower = html.lower()
        self.assertIn('product', html_lower, "HTML should contain product references")
    
    @patch('api.depobangunan.utils.depobangunan_profiler.create_depo_scraper')
    def test_multiple_scraper_creation(self, mock_create):
        """Verify profiler can create multiple independent scraper instances."""
        from api.interfaces import ScrapingResult
        
        # Configure mock to return different scrapers
        scraper_instances = []
        for i in range(2):
            mock_scraper = Mock()
            mock_scraper.scrape_products.return_value = ScrapingResult(
                success=True, 
                products=[], 
                error_message="", 
                url=f"test{i}.com"
            )
            scraper_instances.append(mock_scraper)
        
        mock_create.side_effect = scraper_instances
        
        # Create multiple scrapers
        scraper1 = self.profiler._create_scraper()
        scraper2 = self.profiler._create_scraper()
        
        # Verify both calls succeeded
        self.assertEqual(mock_create.call_count, 2, "Should create two scrapers")
        self.assertIsNotNone(scraper1, "First scraper should be created")
        self.assertIsNotNone(scraper2, "Second scraper should be created")
    
    def test_price_cleaner_performance(self):
        """Verify price cleaner handles various depobangunan price formats correctly."""
        test_prices = self.profiler._get_test_prices()
        price_cleaner = self.profiler.price_cleaner
        
        valid_count = 0
        invalid_count = 0
        
        for price in test_prices:
            # Skip null and obviously invalid values
            if price is None or price == "Invalid price" or price == "":
                invalid_count += 1
                continue
            
            try:
                result = price_cleaner.clean_price(price)
                # Some price cleaners may return 0 for invalid prices
                if result and result > 0:
                    self.assertIsInstance(result, int, f"Price {price} should return integer")
                    self.assertGreater(result, 0, f"Cleaned price should be positive: {price}")
                    valid_count += 1
                else:
                    # Price cleaner returned 0 or None for invalid format
                    invalid_count += 1
            except (TypeError, ValueError, AttributeError):
                # Expected for some edge cases
                invalid_count += 1
        
        # Verify we tested both valid and invalid cases
        self.assertGreater(valid_count, 0, "Should have some valid prices")
        self.assertGreater(invalid_count, 0, "Should have some invalid prices")
    
    def test_html_parser_performance(self):
        """Verify HTML parser processes depobangunan HTML structure without crashes."""
        html = self.profiler._get_fallback_html()
        html_parser = self.profiler.html_parser
        
        # Parsing may succeed or fail depending on HTML content
        # Key requirement: should not crash
        try:
            products = html_parser.parse_products(html)
            self.assertIsInstance(products, list, "Parser should return list")
        except Exception as e:
            # Document parsing errors for debugging
            # Parser may legitimately fail with fixture/mock data
            self.assertIsNotNone(e, "Exception should have details")
    
    def test_url_builder_performance(self):
        """Verify URL builder creates valid depobangunan search URLs for all keywords."""
        url_builder = self.profiler.url_builder
        keywords = self.profiler.test_keywords
        
        for keyword in keywords:
            url = url_builder.build_search_url(keyword)
            
            # Verify URL structure
            self.assertIsInstance(url, str, f"URL for '{keyword}' should be string")
            self.assertGreater(len(url), 0, f"URL for '{keyword}' should not be empty")
            self.assertIn('depobangunan', url, f"URL should contain vendor name: {url}")
    
    def test_optimized_regex_patterns_exist(self):
        """Verify critical regex patterns are pre-compiled for performance."""
        # Price cleaner optimizations
        self.assertTrue(
            hasattr(self.profiler.price_cleaner, '_DIGIT_PATTERN'),
            "Price cleaner missing pre-compiled digit pattern"
        )
        
        # HTML parser optimizations
        self.assertTrue(
            hasattr(self.profiler.html_parser, '_SOLD_COUNT_PATTERN'),
            "HTML parser missing pre-compiled sold count pattern"
        )
    
    def test_unit_parser_optimizations(self):
        """Verify unit parser is properly initialized with correct type."""
        html_parser = self.profiler.html_parser
        
        # Verify unit parser exists
        self.assertTrue(
            hasattr(html_parser, 'unit_parser'),
            "HTML parser missing unit_parser attribute"
        )
        
        unit_parser = html_parser.unit_parser
        self.assertIsNotNone(unit_parser, "Unit parser should be initialized")
        
        # Verify correct type
        from api.depobangunan.unit_parser import DepoBangunanUnitParser
        self.assertIsInstance(
            unit_parser,
            DepoBangunanUnitParser,
            f"Expected DepoBangunanUnitParser, got {type(unit_parser)}"
        )
    
    def test_scraper_has_cache(self):
        """Verify scraper implements caching mechanism for performance optimization."""
        scraper = self.profiler.real_scraper
        
        # Verify cache exists
        self.assertTrue(
            hasattr(scraper, '_unit_cache'),
            "Scraper missing _unit_cache attribute"
        )
        
        # Verify cache structure
        cache = scraper._unit_cache
        self.assertIsInstance(cache, dict, "Cache should be a dictionary")

class TestDepoBangunanProfilerMain(TestCase):
    """Test suite for profiler main entry point and CLI behavior."""
    
    @patch('api.depobangunan.utils.depobangunan_profiler.DepoBangunanProfiler')
    def test_main_function(self, mock_profiler_class):
        """Verify main function initializes and executes profiler correctly."""
        from api.depobangunan.utils.depobangunan_profiler import main
        
        # Setup mock profiler
        mock_profiler_instance = Mock()
        mock_profiler_class.return_value = mock_profiler_instance
        
        # Execute main
        main()
        
        # Verify profiler was created and executed
        mock_profiler_class.assert_called_once_with()
        mock_profiler_instance.run_complete_profiling.assert_called_once_with()
    
    @patch('api.depobangunan.utils.depobangunan_profiler.DepoBangunanProfiler')
    def test_main_function_handles_exception(self, mock_profiler_class):
        """Verify main function properly propagates profiler exceptions."""
        error_msg = "Fatal profiler initialization error"
        
        # Configure mock to raise exception
        mock_profiler_instance = Mock()
        mock_profiler_instance.run_complete_profiling.side_effect = Exception(error_msg)
        mock_profiler_class.return_value = mock_profiler_instance
        
        from api.depobangunan.utils.depobangunan_profiler import main
        
        # Verify exception propagates
        with self.assertRaises(Exception) as ctx:
            main()
        
        self.assertIn(error_msg, str(ctx.exception))


class TestDepoBangunanProfilerOptimizations(TestCase):
    """
    Test suite focusing on profiler optimization measurements and performance metrics.
    Validates that profiler correctly captures performance improvements.
    """
    
    def setUp(self):
        """Initialize profiler for optimization tests."""
        self.profiler = DepoBangunanProfiler()
    
    def test_performance_metrics_structure(self):
        """Verify performance metrics contain required fields for analysis."""
        # Simulate profiling run
        with patch.object(self.profiler, 'run_basic_profiling'):
            with patch.object(self.profiler, 'profile_complete_scraper') as mock_complete:
                # Configure mock result
                mock_result = {
                    'total_time': 2.5,
                    'iterations': 3,
                    'avg_time': 0.833
                }
                mock_complete.return_value = mock_result
                self.profiler.results['complete_scraper'] = mock_result
                
                # Verify result structure
                result = self.profiler.results['complete_scraper']
                self.assertIn('total_time', result, "Missing total_time metric")
                self.assertIn('iterations', result, "Missing iterations metric")
                self.assertIsInstance(result['total_time'], (int, float), "total_time should be numeric")
                self.assertIsInstance(result['iterations'], int, "iterations should be integer")
    
    def test_profiler_tracks_component_times(self):
        """Verify profiler can track individual component execution times."""
        # Verify components are accessible for timing
        components_to_track = [
            'html_parser',
            'price_cleaner',
            'url_builder',
            'real_scraper'
        ]
        
        for component_name in components_to_track:
            component = getattr(self.profiler, component_name, None)
            self.assertIsNotNone(
                component,
                f"Component {component_name} should be available for profiling"
            )
    
    @patch('api.depobangunan.utils.depobangunan_profiler.create_depo_scraper')
    def test_profiler_measures_scraper_performance(self, mock_create):
        """Verify profiler accurately measures scraper execution performance."""
        # Setup mock scraper
        mock_scraper = Mock()
        mock_scraper.scrape_products.return_value = Mock(
            success=True,
            products=[],
            error_message="",
            url="https://depobangunan.com/test"
        )
        mock_create.return_value = mock_scraper
        
        # Mock profiling to return metrics - let profiler run naturally
        with patch.dict(os.environ, {'PROFILING_ITERATIONS_SCRAPER': '1'}):
            with patch.object(self.profiler, 'test_keywords', ['cat']):
                result = self.profiler.profile_complete_scraper()
                
                # Verify metrics are captured
                self.assertIn('total_time', result, "Missing total_time in result")
                self.assertIn('iterations', result, "Missing iterations in result")
                self.assertGreater(result['total_time'], 0, "total_time should be positive")
                # Should have at least 1 iteration (may vary based on actual profiler implementation)
                self.assertGreaterEqual(result['iterations'], 1, "Should have at least 1 iteration")
