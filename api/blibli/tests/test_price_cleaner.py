import unittest
from api.blibli.price_cleaner import BlibliPriceCleaner

class TestBlibliPriceCleaner(unittest.TestCase):
    def test_clean_price_basic(self):
        self.assertEqual(BlibliPriceCleaner.clean_price("Rp 12.000"), 12000)
        self.assertEqual(BlibliPriceCleaner.clean_price("IDR 15,000"), 15000)
        self.assertEqual(BlibliPriceCleaner.clean_price("12.000"), 12000)
        self.assertEqual(BlibliPriceCleaner.clean_price("15,000"), 15000)
        self.assertEqual(BlibliPriceCleaner.clean_price("Rp 0"), 0)

    def test_clean_price_empty_and_none(self):
        self.assertEqual(BlibliPriceCleaner.clean_price(""), 0)
        with self.assertRaises(TypeError):
            BlibliPriceCleaner.clean_price(None)

    def test_clean_price_non_string(self):
        with self.assertRaises(TypeError):
            BlibliPriceCleaner.clean_price(12000)
        with self.assertRaises(TypeError):
            BlibliPriceCleaner.clean_price(["Rp 12.000"])

    def test_clean_price_no_digits(self):
        self.assertEqual(BlibliPriceCleaner.clean_price("Harga tidak tersedia"), 0)

    def test_clean_price_unicode(self):
        self.assertEqual(BlibliPriceCleaner.clean_price("Rp １２３４５"), 12345)  # Full-width digits

    def test_is_valid_price(self):
        self.assertTrue(BlibliPriceCleaner.is_valid_price(12000))
        self.assertFalse(BlibliPriceCleaner.is_valid_price(0))
        self.assertFalse(BlibliPriceCleaner.is_valid_price(-100))

if __name__ == '__main__':
    unittest.main()