from django.test import TestCase
from api.mitra10.price_cleaner import Mitra10PriceCleaner


class TestMitra10PriceCleaner(TestCase):

    def test_clean_price_mitra10_standard_format(self):
        result = Mitra10PriceCleaner.clean_price("IDR 12,000")
        self.assertEqual(result, 12000)

    def test_clean_price_mitra10_no_commas(self):
        result = Mitra10PriceCleaner.clean_price("IDR 12000")
        self.assertEqual(result, 12000)

    def test_clean_price_mitra10_with_dots(self):
        result = Mitra10PriceCleaner.clean_price("IDR 12.000")
        self.assertEqual(result, 12000)

    def test_clean_price_mitra10_mixed_separators(self):
        result = Mitra10PriceCleaner.clean_price("IDR 1.250,500")
        self.assertEqual(result, 1250500)

    def test_clean_price_mitra10_no_currency(self):
        result = Mitra10PriceCleaner.clean_price("12000")
        self.assertEqual(result, 12000)

    def test_clean_price_mitra10_empty_string(self):
        result = Mitra10PriceCleaner.clean_price("")
        self.assertEqual(result, 0)

    def test_clean_price_mitra10_no_digits(self):
        result = Mitra10PriceCleaner.clean_price("IDR")
        self.assertEqual(result, 0)

    def test_clean_price_mitra10_whitespace(self):
        result = Mitra10PriceCleaner.clean_price("  IDR 12,000  ")
        self.assertEqual(result, 12000)

    def test_clean_price_mitra10_large_numbers(self):
        result = Mitra10PriceCleaner.clean_price("IDR 1,500,000")
        self.assertEqual(result, 1500000)

    def test_clean_price_mitra10_returns_integer(self):
        result = Mitra10PriceCleaner.clean_price("IDR 100")
        self.assertIsInstance(result, int)

    def test_clean_price_mitra10_none_input(self):
        with self.assertRaises(TypeError) as context:
            Mitra10PriceCleaner.clean_price(None)
        self.assertEqual(str(context.exception), "price_string cannot be None")

    def test_clean_price_mitra10_non_string_input(self):
        """Test clean_price with non-string input"""
        with self.assertRaises(TypeError) as context:
            Mitra10PriceCleaner.clean_price(12345)
        self.assertEqual(str(context.exception), "price_string must be a string")

    def test_clean_price_mitra10_cache_functionality(self):
        """Test that caching works correctly"""
        # Clear cache first
        Mitra10PriceCleaner.clear_cache()
        
        # First call should compute and cache
        result1 = Mitra10PriceCleaner.clean_price("IDR 50,000")
        self.assertEqual(result1, 50000)
        
        # Second call should use cache
        result2 = Mitra10PriceCleaner.clean_price("IDR 50,000")
        self.assertEqual(result2, 50000)
        
        # Verify cache contains the value
        self.assertIn("IDR 50,000", Mitra10PriceCleaner._price_cache)

    def test_clean_price_mitra10_cache_clearing(self):
        """Test cache clearing functionality"""
        Mitra10PriceCleaner.clean_price("IDR 25,000")
        self.assertTrue(len(Mitra10PriceCleaner._price_cache) > 0)
        
        Mitra10PriceCleaner.clear_cache()
        self.assertEqual(len(Mitra10PriceCleaner._price_cache), 0)

    def test_is_valid_price_positive(self):
        """Test is_valid_price with positive price"""
        self.assertTrue(Mitra10PriceCleaner.is_valid_price(1000))
        self.assertTrue(Mitra10PriceCleaner.is_valid_price(1))

    def test_is_valid_price_zero_negative(self):
        """Test is_valid_price with zero and negative prices"""
        self.assertFalse(Mitra10PriceCleaner.is_valid_price(0))
        self.assertFalse(Mitra10PriceCleaner.is_valid_price(-1000))

    def test_clean_price_cache_size_limit(self):
        """Test that cache respects max size limit"""
        Mitra10PriceCleaner.clear_cache()
        original_max_size = Mitra10PriceCleaner._max_cache_size
        
        # Temporarily set a small cache size for testing
        Mitra10PriceCleaner._max_cache_size = 2
        
        try:
            Mitra10PriceCleaner.clean_price("IDR 1000")
            Mitra10PriceCleaner.clean_price("IDR 2000")
            self.assertEqual(len(Mitra10PriceCleaner._price_cache), 2)
            
            # Adding third item should not increase cache size beyond limit
            Mitra10PriceCleaner.clean_price("IDR 3000")
            self.assertEqual(len(Mitra10PriceCleaner._price_cache), 2)
            
        finally:
            # Restore original max size
            Mitra10PriceCleaner._max_cache_size = original_max_size
            Mitra10PriceCleaner.clear_cache()

    def test_clean_price_mitra10_non_string_input(self):
        with self.assertRaises(TypeError) as context:
            Mitra10PriceCleaner.clean_price(123)
        self.assertEqual(str(context.exception), "price_string must be a string")