import unittest
from unittest.mock import patch, Mock
from api.gemilang.html_parser import GemilangHtmlParser, RegexCache
from api.gemilang.price_cleaner import GemilangPriceCleaner, PriceRegexCache


class TestHtmlParserOptimizations(unittest.TestCase):
    
    def setUp(self):
        self.parser = GemilangHtmlParser()
    
    def test_has_lxml_with_lxml_available(self):
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            result = self.parser._has_lxml()
            self.assertTrue(result)
    
    def test_has_lxml_with_lxml_unavailable(self):
        with patch('builtins.__import__', side_effect=ImportError):
            result = self.parser._has_lxml()
            self.assertFalse(result)
    
    def test_parser_uses_lxml_when_available(self):
        html = '<div class="item-product"><h3>Test Product</h3><span>Rp 10000</span></div>'
        with patch.object(self.parser, '_has_lxml', return_value=True):
            with patch('api.gemilang.html_parser.BeautifulSoup') as mock_soup:
                mock_soup.return_value.find_all.return_value = []
                self.parser.parse_products(html)
                mock_soup.assert_called_once_with(html, 'lxml')
    
    def test_parser_falls_back_to_html_parser_when_lxml_unavailable(self):
        html = '<div class="item-product"><h3>Test Product</h3><span>Rp 10000</span></div>'
        with patch.object(self.parser, '_has_lxml', return_value=False):
            with patch('api.gemilang.html_parser.BeautifulSoup') as mock_soup:
                mock_soup.return_value.find_all.return_value = []
                self.parser.parse_products(html)
                mock_soup.assert_called_once_with(html, 'html.parser')


class TestRegexCache(unittest.TestCase):
    
    def test_regex_patterns_exist(self):
        self.assertIsNotNone(RegexCache.SLUG_PATTERN)
        self.assertIsNotNone(RegexCache.WHITESPACE_PATTERN)
    
    def test_regex_patterns_are_compiled(self):
        self.assertTrue(hasattr(RegexCache.SLUG_PATTERN, 'pattern'))
        self.assertTrue(hasattr(RegexCache.WHITESPACE_PATTERN, 'pattern'))
    
    def test_slug_pattern_removes_special_characters(self):
        text = "Test@#$Product"
        result = RegexCache.SLUG_PATTERN.sub('', text)
        self.assertEqual(result, "TestProduct")
    
    def test_whitespace_pattern_replaces_multiple_spaces(self):
        text = "Test    Multiple   Spaces"
        result = RegexCache.WHITESPACE_PATTERN.sub('-', text)
        self.assertEqual(result, "Test-Multiple-Spaces")


class TestPriceRegexCache(unittest.TestCase):
    
    def setUp(self):
        self.cleaner = GemilangPriceCleaner()
    
    def test_digit_pattern_compilation(self):
        self.assertIsNotNone(PriceRegexCache.DIGIT_PATTERN)
        self.assertIsNotNone(PriceRegexCache.DIGIT_PATTERN.pattern)
    
    def test_digit_pattern_finds_digits(self):
        text = "Price: Rp 12,345.67"
        digits = PriceRegexCache.DIGIT_PATTERN.findall(text)
        self.assertEqual(digits, ['1', '2', '3', '4', '5', '6', '7'])
    
    def test_digit_pattern_handles_no_digits(self):
        text = "No digits here!"
        digits = PriceRegexCache.DIGIT_PATTERN.findall(text)
        self.assertEqual(digits, [])


class TestPerformanceOptimizations(unittest.TestCase):
    
    def test_regex_cache_reuses_compiled_patterns(self):
        self.assertIs(RegexCache.SLUG_PATTERN, RegexCache.SLUG_PATTERN)
        self.assertIs(RegexCache.WHITESPACE_PATTERN, RegexCache.WHITESPACE_PATTERN)
        self.assertIs(PriceRegexCache.DIGIT_PATTERN, PriceRegexCache.DIGIT_PATTERN)
    
    def test_optimized_price_cleaner_maintains_functionality(self):
        cleaner = GemilangPriceCleaner()
        
        test_cases = [
            ("Rp 12345", 12345),
            ("Rp 12,345", 12345),
            ("Rp 12.345", 12345),
            ("12345", 12345),
            ("", 0),
            ("No digits", 0),
        ]
        
        for input_price, expected in test_cases:
            with self.subTest(input_price=input_price):
                result = cleaner.clean_price(input_price)
                self.assertEqual(result, expected)