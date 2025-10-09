from unittest import TestCase
from api.juragan_material.price_cleaner import JuraganMaterialPriceCleaner


class TestJuraganMaterialPriceCleaner(TestCase):
    """Test cases for JuraganMaterialPriceCleaner."""
    
    def setUp(self):
        self.cleaner = JuraganMaterialPriceCleaner()
    
    def test_clean_price_valid_juragan_format(self):
        """Test cleaning price in typical Juragan Material format."""
        result = self.cleaner.clean_price("Rp 60.500")
        self.assertEqual(result, 60500)
    
    def test_clean_price_with_different_formats(self):
        """Test cleaning prices in various formats."""
        test_cases = [
            ("Rp 120.000", 120000),
            ("Rp. 1,000", 1000),
            ("IDR 50000", 50000),
            ("125.000", 125000),
            ("Rp 1.234.567", 1234567),
        ]
        for price_string, expected in test_cases:
            with self.subTest(price_string=price_string):
                result = self.cleaner.clean_price(price_string)
                self.assertEqual(result, expected)
    
    def test_clean_price_empty_string(self):
        """Test cleaning empty price string."""
        result = self.cleaner.clean_price("")
        self.assertEqual(result, 0)
    
    def test_clean_price_no_digits(self):
        """Test cleaning price string with no digits."""
        result = self.cleaner.clean_price("No price available")
        self.assertEqual(result, 0)
    
    def test_clean_price_none_input(self):
        """Test that None input raises TypeError."""
        with self.assertRaises(TypeError) as context:
            self.cleaner.clean_price(None)
        self.assertIn("price_string cannot be None", str(context.exception))
    
    def test_clean_price_non_string_input(self):
        """Test that non-string input raises TypeError."""
        with self.assertRaises(TypeError) as context:
            self.cleaner.clean_price(12345)
        self.assertIn("price_string must be a string", str(context.exception))
    
    def test_is_valid_price_positive(self):
        """Test validation of positive prices."""
        self.assertTrue(self.cleaner.is_valid_price(100))
        self.assertTrue(self.cleaner.is_valid_price(1))
        self.assertTrue(self.cleaner.is_valid_price(999999))
    
    def test_is_valid_price_zero_or_negative(self):
        """Test validation of zero or negative prices."""
        self.assertFalse(self.cleaner.is_valid_price(0))
        self.assertFalse(self.cleaner.is_valid_price(-100))
        self.assertFalse(self.cleaner.is_valid_price(-1))