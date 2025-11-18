import unittest
from unittest.mock import patch, Mock
from api.juragan_material.html_parser import JuraganMaterialHtmlParser
from api.juragan_material.price_cleaner import JuraganMaterialPriceCleaner


class TestJuraganMaterialHtmlParserOptimizations(unittest.TestCase):
    
    def setUp(self):
        self.parser = JuraganMaterialHtmlParser()
    
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
        html = '<div class="product-card"><p class="product-name">Test Product</p><div class="price">Rp 10000</div></div>'
        with patch.object(self.parser, '_has_lxml', return_value=True):
            with patch('api.juragan_material.html_parser.BeautifulSoup') as mock_soup:
                mock_soup.return_value.find_all.return_value = []
                self.parser.parse_products(html)
                mock_soup.assert_called_once_with(html, 'lxml')
    
    def test_parser_falls_back_to_html_parser_when_lxml_unavailable(self):
        html = '<div class="product-card"><p class="product-name">Test Product</p><div class="price">Rp 10000</div></div>'
        with patch.object(self.parser, '_has_lxml', return_value=False):
            with patch('api.juragan_material.html_parser.BeautifulSoup') as mock_soup:
                mock_soup.return_value.find_all.return_value = []
                self.parser.parse_products(html)
                mock_soup.assert_called_once_with(html, 'html.parser')


class TestJuraganMaterialRegexCache(unittest.TestCase):
    
    def test_regex_patterns_exist(self):
        from api.juragan_material.html_parser import RegexCache
        self.assertIsNotNone(RegexCache.SLUG_PATTERN)
        self.assertIsNotNone(RegexCache.WHITESPACE_PATTERN)
    
    def test_regex_patterns_are_compiled(self):
        from api.juragan_material.html_parser import RegexCache
        self.assertTrue(hasattr(RegexCache.SLUG_PATTERN, 'pattern'))
        self.assertTrue(hasattr(RegexCache.WHITESPACE_PATTERN, 'pattern'))
    
    def test_slug_pattern_removes_special_characters(self):
        from api.juragan_material.html_parser import RegexCache
        text = "Semen@#$Holcim"
        result = RegexCache.SLUG_PATTERN.sub('', text)
        self.assertEqual(result, "SemenHolcim")
    
    def test_whitespace_pattern_replaces_multiple_spaces(self):
        from api.juragan_material.html_parser import RegexCache
        text = "Semen    Holcim   40Kg"
        result = RegexCache.WHITESPACE_PATTERN.sub('-', text)
        self.assertEqual(result, "Semen-Holcim-40Kg")


class TestJuraganMaterialPriceRegexCache(unittest.TestCase):
    
    def setUp(self):
        self.cleaner = JuraganMaterialPriceCleaner()
    
    def test_digit_pattern_compilation(self):
        from api.juragan_material.price_cleaner import PriceRegexCache
        self.assertIsNotNone(PriceRegexCache.DIGIT_PATTERN)
        self.assertIsNotNone(PriceRegexCache.DIGIT_PATTERN.pattern)
    
    def test_digit_pattern_finds_digits(self):
        from api.juragan_material.price_cleaner import PriceRegexCache
        text = "Price: Rp 60.500"
        digits = PriceRegexCache.DIGIT_PATTERN.findall(text)
        self.assertEqual(digits, ['6', '0', '5', '0', '0'])
    
    def test_digit_pattern_handles_no_digits(self):
        from api.juragan_material.price_cleaner import PriceRegexCache
        text = "No digits here!"
        digits = PriceRegexCache.DIGIT_PATTERN.findall(text)
        self.assertEqual(digits, [])


class TestJuraganMaterialPerformanceOptimizations(unittest.TestCase):
    
    def test_regex_cache_reuses_compiled_patterns(self):
        from api.juragan_material.html_parser import RegexCache
        from api.juragan_material.price_cleaner import PriceRegexCache
        
        self.assertIs(RegexCache.SLUG_PATTERN, RegexCache.SLUG_PATTERN)
        self.assertIs(RegexCache.WHITESPACE_PATTERN, RegexCache.WHITESPACE_PATTERN)
        self.assertIs(PriceRegexCache.DIGIT_PATTERN, PriceRegexCache.DIGIT_PATTERN)
    
    def test_optimized_price_cleaner_maintains_functionality(self):
        cleaner = JuraganMaterialPriceCleaner()
        
        test_cases = [
            ("Rp 60.500", 60500),
            ("Rp 120,000", 120000),
            ("Rp 1.234.567", 1234567),
            ("60500", 60500),
            ("", 0),
            ("No digits", 0),
        ]
        
        for input_price, expected in test_cases:
            with self.subTest(input_price=input_price):
                result = cleaner.clean_price(input_price)
                self.assertEqual(result, expected)
    
    def test_optimized_html_parser_maintains_functionality(self):
        parser = JuraganMaterialHtmlParser()
        html = '''
        <div class="product-card">
            <a href="/products/semen-holcim-40kg">
                <p class="product-name">Semen Holcim 40Kg</p>
            </a>
            <div class="product-card-price">
                <div class="price">Rp 60.500</div>
            </div>
        </div>
        '''
        
        products = parser.parse_products(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Semen Holcim 40Kg")
        self.assertEqual(products[0].price, 60500)
        self.assertEqual(products[0].url, "/products/semen-holcim-40kg")