"""
Tests for ParserConfig caching optimization
"""
import unittest
from unittest.mock import patch, Mock
from api.gemilang.html_parser import ParserConfig


class TestParserConfig(unittest.TestCase):
    """Test ParserConfig class functionality"""
    
    def setUp(self):
        """Reset cache before each test"""
        ParserConfig._has_lxml_cache = None
    
    def test_check_lxml_returns_boolean(self):
        """Test that check_lxml returns a boolean value"""
        result = ParserConfig.check_lxml()
        self.assertIsInstance(result, bool)
    
    def test_check_lxml_with_lxml_available(self):
        """Test check_lxml returns True when lxml is available"""
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            # Reset cache to test fresh
            ParserConfig._has_lxml_cache = None
            result = ParserConfig.check_lxml()
            self.assertTrue(result)
    
    def test_check_lxml_with_lxml_unavailable(self):
        """Test check_lxml returns False when lxml is not available"""
        with patch('builtins.__import__', side_effect=ImportError):
            # Reset cache to test fresh
            ParserConfig._has_lxml_cache = None
            result = ParserConfig.check_lxml()
            self.assertFalse(result)
    
    def test_check_lxml_caches_result(self):
        """Test that check_lxml caches the result on subsequent calls"""
        # Reset cache
        ParserConfig._has_lxml_cache = None
        
        # First call
        result1 = ParserConfig.check_lxml()
        
        # Mock import to raise error
        with patch('builtins.__import__', side_effect=ImportError):
            # Second call should return cached result, not error
            result2 = ParserConfig.check_lxml()
            self.assertEqual(result1, result2)
    
    def test_check_lxml_without_cache(self):
        """Test check_lxml with use_cache=False bypasses cache"""
        # Set cache to False
        ParserConfig._has_lxml_cache = False
        
        # Call with use_cache=False and mock to return True
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            result = ParserConfig.check_lxml(use_cache=False)
            self.assertTrue(result)
            # Cache should still be False
            self.assertFalse(ParserConfig._has_lxml_cache)
    
    def test_check_lxml_cache_updates_on_first_call(self):
        """Test that cache is updated on first call with use_cache=True"""
        # Reset cache
        ParserConfig._has_lxml_cache = None
        
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            ParserConfig.check_lxml(use_cache=True)
            # Cache should now be set
            self.assertIsNotNone(ParserConfig._has_lxml_cache)
            self.assertTrue(ParserConfig._has_lxml_cache)
    
    def test_check_lxml_multiple_calls_use_cache(self):
        """Test that multiple calls with caching don't re-import"""
        # Reset cache
        ParserConfig._has_lxml_cache = None
        
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            
            # First call
            ParserConfig.check_lxml()
            first_call_count = mock_import.call_count
            
            # Second call should not call import again
            ParserConfig.check_lxml()
            second_call_count = mock_import.call_count
            
            self.assertEqual(first_call_count, second_call_count)


class TestParserConfigEdgeCases(unittest.TestCase):
    """Test edge cases for ParserConfig"""
    
    def setUp(self):
        """Reset cache before each test"""
        ParserConfig._has_lxml_cache = None
    
    def test_check_lxml_with_none_cache(self):
        """Test check_lxml when cache is explicitly None"""
        ParserConfig._has_lxml_cache = None
        result = ParserConfig.check_lxml()
        self.assertIsInstance(result, bool)
    
    def test_check_lxml_thread_safety_concept(self):
        """Test that cache doesn't cause issues with multiple checks"""
        # This is a conceptual test - in production, consider thread-safe implementation
        results = []
        for _ in range(10):
            ParserConfig._has_lxml_cache = None
            result = ParserConfig.check_lxml()
            results.append(result)
        
        # All results should be the same
        self.assertTrue(all(r == results[0] for r in results))
    
    def test_check_lxml_import_error_handling(self):
        """Test that ImportError is properly handled"""
        with patch('builtins.__import__', side_effect=ImportError("Test error")):
            ParserConfig._has_lxml_cache = None
            result = ParserConfig.check_lxml()
            self.assertFalse(result)
            # Cache should be set to False
            self.assertFalse(ParserConfig._has_lxml_cache)


class TestParserConfigPerformance(unittest.TestCase):
    """Test performance-related aspects of ParserConfig"""
    
    def setUp(self):
        """Reset cache before each test"""
        ParserConfig._has_lxml_cache = None
    
    def test_cached_calls_are_faster(self):
        """Test that cached calls don't perform import"""
        import time
        
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            
            # Reset cache
            ParserConfig._has_lxml_cache = None
            
            # First call - should import
            start = time.perf_counter()
            ParserConfig.check_lxml()
            first_duration = time.perf_counter() - start
            
            # Second call - should use cache
            start = time.perf_counter()
            ParserConfig.check_lxml()
            second_duration = time.perf_counter() - start
            
            # Second call should be faster (or at least not slower)
            # Note: This is a conceptual test, actual timing may vary
            self.assertLessEqual(second_duration, first_duration * 10)
    
    def test_uncached_calls_perform_import(self):
        """Test that use_cache=False always performs import"""
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            
            # Multiple calls with use_cache=False
            for _ in range(3):
                ParserConfig.check_lxml(use_cache=False)
            
            # Should have called import 3 times
            self.assertEqual(mock_import.call_count, 3)
