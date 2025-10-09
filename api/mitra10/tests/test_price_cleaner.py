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
        with self.assertRaises(TypeError) as context:
            Mitra10PriceCleaner.clean_price(123)
        self.assertEqual(str(context.exception), "price_string must be a string")