import unittest
from api.depobangunan.price_cleaner import DepoPriceCleaner


class TestDepoPriceCleaner(unittest.TestCase):
    
    def setUp(self):
        self.price_cleaner = DepoPriceCleaner()
    
    def test_clean_price_basic_depo_format(self):
        result = self.price_cleaner.clean_price("Rp 3.600")
        self.assertEqual(result, 3600)
    
    def test_clean_price_large_amount(self):
        result = self.price_cleaner.clean_price("Rp 125.000")
        self.assertEqual(result, 125000)
    
    def test_clean_price_discounted_format(self):
        result = self.price_cleaner.clean_price("Rp 59.903")
        self.assertEqual(result, 59903)
    
    def test_clean_price_no_currency_symbol(self):
        result = self.price_cleaner.clean_price("3.600")
        self.assertEqual(result, 3600)
    
    def test_clean_price_with_spaces(self):
        result = self.price_cleaner.clean_price("  Rp 3.600  ")
        self.assertEqual(result, 3600)
    
    def test_clean_price_with_comma_separator(self):
        result = self.price_cleaner.clean_price("Rp 3,600")
        self.assertEqual(result, 3600)
    
    def test_clean_price_mixed_separators(self):
        result = self.price_cleaner.clean_price("Rp 1,234.567")
        self.assertEqual(result, 1234567)
    
    def test_clean_price_empty_string(self):
        result = self.price_cleaner.clean_price("")
        self.assertEqual(result, 0)
    
    def test_clean_price_none_raises_error(self):
        with self.assertRaises(TypeError):
            self.price_cleaner.clean_price(None)
    
    def test_clean_price_non_string_raises_error(self):
        with self.assertRaises(TypeError):
            self.price_cleaner.clean_price(123)
    
    def test_clean_price_no_digits(self):
        result = self.price_cleaner.clean_price("Rp abc")
        self.assertEqual(result, 0)
    
    def test_clean_price_only_currency(self):
        result = self.price_cleaner.clean_price("Rp ")
        self.assertEqual(result, 0)
    
    def test_is_valid_price_positive(self):
        self.assertTrue(self.price_cleaner.is_valid_price(1000))
        self.assertTrue(self.price_cleaner.is_valid_price(1))
    
    def test_is_valid_price_zero(self):
        self.assertFalse(self.price_cleaner.is_valid_price(0))
    
    def test_is_valid_price_negative(self):
        self.assertFalse(self.price_cleaner.is_valid_price(-100))
    
    def test_static_methods_access(self):
        result = DepoPriceCleaner.clean_price("Rp 1.000")
        self.assertEqual(result, 1000)
        
        self.assertTrue(DepoPriceCleaner.is_valid_price(1000))
        self.assertFalse(DepoPriceCleaner.is_valid_price(0))


if __name__ == '__main__':
    unittest.main()