from unittest import TestCase
from unittest.mock import patch
from api.gemilang.price_cleaner import GemilangPriceCleaner
class TestGemilangPriceCleaner(TestCase):
    def setUp(self):
        self.cleaner = GemilangPriceCleaner()
    def test_clean_price_valid_gemilang_format(self):
        result = self.cleaner.clean_price("Rp 55.000")
        self.assertEqual(result, 55000)
    def test_clean_price_with_different_formats(self):
        test_cases = [
            ("Rp 3.600", 3600),
            ("Rp. 125,000", 125000),
            ("IDR 50000", 50000),
            ("125.000", 125000),
            ("Rp 1.234.567", 1234567),
        ]
        for price_string, expected in test_cases:
            with self.subTest(price_string=price_string):
                result = self.cleaner.clean_price(price_string)
                self.assertEqual(result, expected)
    def test_clean_price_empty_string(self):
        result = self.cleaner.clean_price("")
        self.assertEqual(result, 0)
    def test_clean_price_no_digits(self):
        result = self.cleaner.clean_price("No price available")
        self.assertEqual(result, 0)
    def test_clean_price_none_input(self):
        with self.assertRaises(TypeError) as context:
            self.cleaner.clean_price(None)
        self.assertIn("price_string cannot be None", str(context.exception))
    def test_clean_price_non_string_input(self):
        with self.assertRaises(TypeError) as context:
            self.cleaner.clean_price(12345)
        self.assertIn("price_string must be a string", str(context.exception))
    def test_is_valid_price_positive(self):
        self.assertTrue(self.cleaner.is_valid_price(100))
        self.assertTrue(self.cleaner.is_valid_price(1))
        self.assertTrue(self.cleaner.is_valid_price(999999))
    def test_is_valid_price_zero_or_negative(self):
        self.assertFalse(self.cleaner.is_valid_price(0))
        self.assertFalse(self.cleaner.is_valid_price(-100))
        self.assertFalse(self.cleaner.is_valid_price(-1))
    def test_integration_clean_and_validate(self):
        valid_price = self.cleaner.clean_price("Rp 55.000")
        self.assertTrue(self.cleaner.is_valid_price(valid_price))
        invalid_price = self.cleaner.clean_price("No price")
        self.assertFalse(self.cleaner.is_valid_price(invalid_price))
