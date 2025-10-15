from django.test import TestCase
import unittest
from unittest.mock import Mock, patch
from api.tokopedia.price_cleaner import TokopediaPriceCleaner


class TestTokopediaPriceCleaner(TestCase):
    
    def setUp(self):
        self.price_cleaner = TokopediaPriceCleaner()
    
    def test_basic_price_cleaning(self):
        """Test basic price string cleaning"""
        test_cases = [
            ("Rp62.500", 62500),
            ("Rp6.370.275", 6370275),
            ("Rp55.670", 55670),
            ("Rp1.234.567", 1234567),
            ("Rp100", 100),
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
    
    def test_price_with_whitespace(self):
        """Test price cleaning with various whitespace patterns"""
        test_cases = [
            ("Rp 62.500", 62500),
            ("  Rp62.500  ", 62500),
            ("Rp  6.370.275", 6370275),
            ("\tRp55.670\n", 55670),
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
    
    def test_price_case_insensitive(self):
        """Test that price cleaning is case insensitive"""
        test_cases = [
            ("rp62.500", 62500),
            ("RP62.500", 62500),
            ("Rp62.500", 62500),
            ("rP62.500", 62500),
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
    
    def test_price_with_commas(self):
        """Test price cleaning with comma separators"""
        test_cases = [
            ("Rp62,500", 62500),
            ("Rp6,370,275", 6370275),
            ("Rp1,234,567", 1234567),
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
    
    def test_price_mixed_separators(self):
        """Test price cleaning with mixed dot and comma separators"""
        test_cases = [
            ("Rp6.370,275", 6370275),
            ("Rp1,234.567", 1234567),
            ("Rp62.500,00", 6250000),  # Treating as Indonesian format
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
    
    def test_numbers_only_fallback(self):
        """Test fallback to numbers-only extraction when Rp pattern fails"""
        test_cases = [
            ("62.500", 62500),
            ("6.370.275", 6370275),
            ("Price: 55.670", 55670),
            ("Total 1.234.567 rupiah", 1234567),
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
    
    def test_invalid_price_strings(self):
        """Test handling of invalid price strings"""
        invalid_cases = [
            "Invalid price",
            "No numbers here",
            "Rp",
            "Price TBD",
            "Free",
            "Contact for price",
            "",
            "   ",
            "Rp abc",
        ]
        
        for price_text in invalid_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertIsNone(result)
    
    def test_none_and_non_string_inputs(self):
        """Test handling of None and non-string inputs"""
        invalid_inputs = [
            None,
            123,
            [],
            {},
            True,
            False,
        ]
        
        for input_value in invalid_inputs:
            with self.subTest(input_value=input_value):
                result = self.price_cleaner.clean_price_string(input_value)
                self.assertIsNone(result)
    
    def test_very_large_prices(self):
        """Test handling of very large price values"""
        test_cases = [
            ("Rp999.999.999", 999999999),
            ("Rp100.000.000", 100000000),
            ("Rp50.000.000", 50000000),
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
    
    def test_very_small_prices(self):
        """Test handling of very small price values"""
        test_cases = [
            ("Rp1", 1),
            ("Rp10", 10),
            ("Rp100", 100),
            ("Rp1.000", 1000),
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
    
    def test_price_validation_valid_prices(self):
        """Test price validation for valid construction material prices"""
        valid_prices = [
            100,        # Minimum valid
            1000,       # Small item
            50000,      # Medium item
            500000,     # Expensive item
            5000000,    # Very expensive item
            50000000,   # Bulk order
            100000000,  # Maximum valid
        ]
        
        for price in valid_prices:
            with self.subTest(price=price):
                result = self.price_cleaner.validate_price(price)
                self.assertTrue(result)
    
    def test_price_validation_invalid_prices(self):
        """Test price validation for invalid prices"""
        invalid_prices = [
            -1,           # Negative
            0,            # Zero
            50,           # Too small
            99,           # Below minimum
            100000001,    # Above maximum
            999999999,    # Way too high
        ]
        
        for price in invalid_prices:
            with self.subTest(price=price):
                result = self.price_cleaner.validate_price(price)
                self.assertFalse(result)
    
    def test_price_validation_non_integer_inputs(self):
        """Test price validation with non-integer inputs"""
        invalid_inputs = [
            "100",        # String
            100.5,        # Float
            None,         # None
            [],           # List
            {},           # Dict
            True,         # Boolean
        ]
        
        for input_value in invalid_inputs:
            with self.subTest(input_value=input_value):
                result = self.price_cleaner.validate_price(input_value)
                self.assertFalse(result)
    
    def test_regex_patterns(self):
        """Test the regex patterns used for price extraction"""
        # Test price pattern
        price_pattern = self.price_cleaner.price_pattern
        test_strings = [
            ("Rp62.500", "62.500"),
            ("rp6.370.275", "6.370.275"),
            ("Price: Rp55.670", "55.670"),
            ("Total Rp 1.234.567 rupiah", "1.234.567"),
        ]
        
        for text, expected_match in test_strings:
            with self.subTest(text=text):
                match = price_pattern.search(text)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), expected_match)
        
        # Test number pattern
        number_pattern = self.price_cleaner.number_pattern
        number_test_strings = [
            ("Price: 62.500", "62.500"),
            ("Total 6,370,275 rupiah", "6,370,275"),
            ("Cost 55.670", "55.670"),
        ]
        
        for text, expected_match in number_test_strings:
            with self.subTest(text=text):
                match = number_pattern.search(text)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(), expected_match)
    
    def test_edge_cases(self):
        """Test edge cases and unusual price formats"""
        edge_cases = [
            ("Rp0", 0),          # Zero price (invalid but parseable)
            ("Rp000", 0),        # Leading zeros
            ("Rp001.000", 1000), # Leading zeros with separators
            ("Rp62.500.", 62500), # Trailing dot
            ("Rp.62.500", 62500), # Leading dot
        ]
        
        for price_text, expected in edge_cases:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                if expected == 0:
                    # Zero prices should parse but not validate
                    self.assertEqual(result, expected)
                    self.assertFalse(self.price_cleaner.validate_price(result))
                else:
                    self.assertEqual(result, expected)
    
    def test_realistic_tokopedia_prices(self):
        """Test with realistic Tokopedia construction material prices"""
        realistic_prices = [
            ("Rp62.500", 62500),      # Cement price
            ("Rp6.370.275", 6370275), # Bulk order
            ("Rp55.670", 55670),      # Smaller items
            ("Rp450.000", 450000),    # Mid-range materials
            ("Rp89.900", 89900),      # Common price ending
            ("Rp1.250.000", 1250000), # Premium materials
        ]
        
        for price_text, expected in realistic_prices:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertEqual(result, expected)
                self.assertTrue(self.price_cleaner.validate_price(result))
    
    def test_clean_price_method_returns_zero_on_none(self):
        """Test that clean_price method returns 0 when clean_price_string returns None"""
        invalid_prices = [
            "Invalid price",
            "No numbers here",
            "",
            None,
        ]
        
        for price_text in invalid_prices:
            with self.subTest(price_text=price_text):
                # clean_price should return 0 instead of None
                result = self.price_cleaner.clean_price(price_text)
                self.assertEqual(result, 0)
    
    def test_validate_price_with_non_integer(self):
        """Test validate_price with non-integer inputs"""
        invalid_inputs = [
            "62500",     # String
            62500.5,     # Float
            None,        # None
            [],          # List
            {},          # Dict
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(invalid_input=invalid_input):
                result = self.price_cleaner.validate_price(invalid_input)
                self.assertFalse(result)
    
    def test_is_valid_price_alias(self):
        """Test that is_valid_price is an alias for validate_price"""
        # Test valid prices
        valid_prices = [1000, 50000, 100000, 1000000]
        for price in valid_prices:
            with self.subTest(price=price):
                result = self.price_cleaner.is_valid_price(price)
                self.assertTrue(result)
                # Should be same as validate_price
                self.assertEqual(result, self.price_cleaner.validate_price(price))
        
        # Test invalid prices
        invalid_prices = [50, 100_000_001, 0, -1000]
        for price in invalid_prices:
            with self.subTest(price=price):
                result = self.price_cleaner.is_valid_price(price)
                self.assertFalse(result)
                # Should be same as validate_price
                self.assertEqual(result, self.price_cleaner.validate_price(price))
    
    def test_clean_price_string_with_attribute_error(self):
        """Test clean_price_string handles AttributeError when text is None"""
        # When price_text is None, it will raise AttributeError on .upper()
        result = self.price_cleaner.clean_price_string(None)
        self.assertIsNone(result)
    
    def test_clean_price_string_with_value_error(self):
        """Test clean_price_string handles ValueError when conversion fails"""
        # Create a string that will pass regex but fail int conversion
        # This is tricky because most strings that match will convert successfully
        # But we can test with empty string after cleaning
        invalid_prices = [
            "Rp",  # Will match Rp pattern but have no digits
            "Price: Rp only",  # Will match but no valid price
        ]
        
        for price_text in invalid_prices:
            with self.subTest(price_text=price_text):
                result = self.price_cleaner.clean_price_string(price_text)
                self.assertIsNone(result)
    
    def test_clean_price_string_exception_handling_value_error(self):
        """Test that ValueError is caught and None is returned"""
        # Mock the int() conversion to raise ValueError
        with patch('builtins.int', side_effect=ValueError("Invalid conversion")):
            result = self.price_cleaner.clean_price_string("Rp50.000")
            self.assertIsNone(result)
    
    def test_clean_price_string_exception_handling_attribute_error(self):
        """Test that AttributeError is caught and None is returned"""
        # Create a mock object that will raise AttributeError
        class BadString:
            def __str__(self):
                return "Rp50.000"
            
            def strip(self):
                raise AttributeError("strip not available")
        
        # Pass the bad string object (not a real string)
        # First check should fail on isinstance check
        result = self.price_cleaner.clean_price_string(BadString())
        self.assertIsNone(result)
    
    def test_clean_price_string_catches_attribute_error_in_processing(self):
        """Test that AttributeError during string processing is caught"""
        # Create a custom string class that will cause AttributeError during replace
        class BadStringReplace(str):
            def replace(self, old, new):
                raise AttributeError("Replace not available")
        
        # We need to pass the isinstance check, so we'll mock int() instead
        with patch('builtins.int', side_effect=AttributeError("Attribute error")):
            result = self.price_cleaner.clean_price_string("Rp50.000")
            self.assertIsNone(result)
