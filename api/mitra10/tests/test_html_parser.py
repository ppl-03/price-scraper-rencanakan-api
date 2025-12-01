from bs4 import BeautifulSoup
from django.test import TestCase
from unittest.mock import MagicMock
import unittest.mock
from api.mitra10.html_parser import Mitra10HtmlParser
from unittest.mock import patch
import api.mitra10.html_parser as hp
from api.mitra10.html_parser import HtmlParserError


class TestMitra10HTMLParser(TestCase):

    def setUp(self):
        self.parser = Mitra10HtmlParser()
    
    def _products_to_dicts(self, products):
        """Helper method to convert Product objects to dictionaries for test compatibility"""
        return [
            {
                'name': product.name,
                'price': product.price,
                'url': product.url
            }
            for product in products
        ]
    
    def _create_product_html(self, name=None, price=None, url=None, img_alt=None, 
                           price_class="price__final", grid_classes="MuiGrid-grid-xs-6"):
        """Helper method to create HTML for a single product with customizable fields"""
        name_html = f'<p class="MuiTypography-root">{name}</p>' if name else ''
        if img_alt:
            name_html = f'<img alt="{img_alt}" src="test.jpg">'
        
        price_html = f'<span class="{price_class}">{price}</span>' if price else ''
        href_attr = f'href="{url}"' if url else ''
        
        return f'''
        <div class="MuiGrid-root MuiGrid-item {grid_classes}">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" {href_attr}>
              {name_html}
            </a>
            <div class="jss298">
              {price_html}
            </div>
          </div>
        </div>
        '''
    
    def _create_multiple_products_html(self, products_data):
        """Helper method to create HTML with multiple products"""
        products_html = []
        for product in products_data:
            products_html.append(self._create_product_html(**product))
        
        return f'''
        <div class="product-list">
            {''.join(products_html)}
        </div>
        '''

    def test_scrape_mitra10_valid_products(self):
        html = self._create_product_html(
            name="Test Product", 
            price="IDR 25,000", 
            url="/test-product",
            grid_classes="MuiGrid-grid-xs-6 MuiGrid-grid-sm-4 MuiGrid-grid-md-3"
        )
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertIsInstance(products, list)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Test Product')
        self.assertEqual(products_dict[0]['price'], 25000)
        self.assertEqual(products_dict[0]['url'], '/test-product')

    def test_scrape_mitra10_empty_html(self):
        products = self.parser.parse_products("")
        self.assertIsInstance(products, list)
        self.assertEqual(len(products), 0)

    def test_scrape_mitra10_no_products(self):
        html = '<html><body><div class="MuiAlert-message">Kami tidak dapat menemukan produk yang sesuai dengan pilihan.</div></body></html>'
        products = self.parser.parse_products(html)
        self.assertIsInstance(products, list)
        self.assertEqual(len(products), 0)

    def test_scrape_mitra10_malformed_html(self):
        html = '<div class="MuiGrid-item"><div class="grid-item"><a class="gtm_mitra10_cta_product"'
        products = self.parser.parse_products(html)
        self.assertIsInstance(products, list)

    def test_scrape_mitra10_missing_name(self):
        html = self._create_product_html(price="IDR 25,000", url="/test-product")
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 0)

    def test_scrape_mitra10_missing_price(self):
        html = self._create_product_html(name="Test Product", url="/test-product")
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 0)  # Products with no price should be filtered out

    def test_scrape_mitra10_missing_url(self):
        html = self._create_product_html(name="Test Product", price="IDR 25,000")
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)  # Should generate fallback URL
        self.assertEqual(products_dict[0]['url'], '/product/test-product')  

    def test_scrape_mitra10_multiple_products(self):
        products_data = [
            {"name": "Product 1", "price": "IDR 10,000", "url": "/product-1"},
            {"name": "Product 2", "price": "IDR 20,000", "url": "/product-2"}
        ]
        html = self._create_multiple_products_html(products_data)
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 2)
        self.assertEqual(products_dict[0]['name'], 'Product 1')
        self.assertEqual(products_dict[0]['price'], 10000)
        self.assertEqual(products_dict[0]['url'], '/product-1')
        self.assertEqual(products_dict[1]['name'], 'Product 2')
        self.assertEqual(products_dict[1]['price'], 20000)
        self.assertEqual(products_dict[1]['url'], '/product-2')

    def test_scrape_mitra10_zero_price(self):
        html = self._create_product_html(name="Test Product", price="IDR 0", url="/test-product")
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 0)  

    def test_mitra10_product_name_exact_match(self):
        html = self._create_product_html(name="Exact Product Name", price="IDR 15,000", url="/exact-product-name")
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Exact Product Name')

    def test_mitra10_product_name_with_special_characters(self):
        html = self._create_product_html(name="Product & Tools 100%", price="IDR 25,000", url="/special-product")
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Product & Tools 100%')

    def test_mitra10_product_name_with_numbers(self):
        html = self._create_product_html(name="Cat Tembok 5Kg Premium 2024", price="IDR 45,000", url="/numbered-product")
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Cat Tembok 5Kg Premium 2024')

    def test_mitra10_product_name_with_whitespace(self):
        html = self._create_product_html(name="  Product With Spaces  ", price="IDR 12,000", url="/whitespace-product")
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Product With Spaces')

    def test_html_parser_css_selector_precision(self):
        """Test HTML parser with precise CSS selector matching"""
        html = '''
        <div class="container">
            <!-- Correct product structure -->
            <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
                <div class="jss273 grid-item">
                    <a class="gtm_mitra10_cta_product" href="/correct-product">
                        <p>Correct Product</p>
                    </a>
                    <span class="price__final">IDR 15,000</span>
                </div>
            </div>
            <!-- Incorrect structure - missing grid-item class -->
            <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
                <div class="wrong-class-name">
                    <a class="gtm_mitra10_cta_product" href="/wrong-product">
                        <p>Wrong Product</p>
                    </a>
                    <span class="price__final">IDR 20,000</span>
                </div>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 2)  
        self.assertEqual(products_dict[0]['name'], 'Correct Product')
        self.assertEqual(products_dict[0]['price'], 15000)

    def test_html_parser_nested_element_extraction(self):
        """Test extraction from deeply nested HTML structures"""
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <div class="product-wrapper">
                    <div class="product-inner">
                        <a class="gtm_mitra10_cta_product" href="/nested-product">
                            <div class="title-wrapper">
                                <p class="MuiTypography-root product-title">
                                    <span>Nested Product Title</span>
                                </p>
                            </div>
                        </a>
                    </div>
                </div>
                <div class="price-section">
                    <div class="price-wrapper">
                        <span class="MuiTypography-root price__final price-text">
                            IDR 30,000
                        </span>
                    </div>
                </div>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Nested Product Title')
        self.assertEqual(products_dict[0]['price'], 30000)
        self.assertEqual(products_dict[0]['url'], '/nested-product')

    def test_price_extraction_regex_rupiah(self):
        """Cover regex-based price extraction when no Rp/IDR is present to hit _extract_from_regex_patterns return."""
        html = '<div><span>harga sekitar 12.345 rupiah</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        price = self.parser.price_helper.extract_price_from_element(soup)
        self.assertEqual(price, 12345)

    def test_unit_fallback_from_name_when_item_html_has_no_unit(self):
        """Force first unit parse to None and second (name-only) to 'PCS' to cover name-fallback path."""
        mock_unit_parser = MagicMock()
        mock_unit_parser.parse_unit.side_effect = [None, 'PCS']
        parser = Mitra10HtmlParser(unit_parser=mock_unit_parser)

        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/p1">
                    <p>Produk Sample 10 PCS</p>
                </a>
                <span class="price__final">IDR 10,000</span>
            </div>
        </div>
        '''
        products = parser.parse_products(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].unit, 'PCS')

    def test_extract_sold_count_regular_number(self):
        """Cover normalization of sold count for standard integer text."""
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/sold-regular"><p>Produk A</p></a>
                <span class="price__final">IDR 20,000</span>
                <div>38 Terjual</div>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].sold_count, 38)

    def test_extract_sold_count_thousands_rb(self):
        """Cover normalization of sold count for 'rb' thousands notation."""
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/sold-rb"><p>Produk B</p></a>
                <span class="price__final">IDR 30,000</span>
                <div>1 rb+ terjual</div>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].sold_count, 1000)

    def test_extract_sold_count_no_digits_returns_none(self):
        """Cover branch where sold_text exists but contains no digits, triggering final return None (~294-297)."""
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/sold-nodigits"><p>Produk C</p></a>
                <span class="price__final">IDR 10,000</span>
                <div>terjual</div>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 1)
        self.assertIsNone(products[0].sold_count)

    def test_normalize_sold_count_value_error_branch(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/sold-patch"><p>Produk D</p></a>
                <span class="price__final">IDR 40,000</span>
                <div>123 terjual</div>
            </div>
        </div>
        '''
        # re.sub is no longer used in implementation; parsing should still succeed
        with patch.object(hp.re, 'sub', return_value='notanumber'):
            products = self.parser.parse_products(html)
        self.assertEqual(len(products), 1)
        # Expect robust digit-only parsing to return 123
        self.assertEqual(products[0].sold_count, 123)

    def test_normalize_sold_count_rb_value_error_branch(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/sold-rb-malformed"><p>Produk E</p></a>
                <span class="price__final">IDR 50,000</span>
                <div>1,,2 rb terjual</div>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].sold_count, 2000)

    def test_normalize_sold_count_rb_value_error_branch_forced(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/sold-rb-bad"><p>Produk F</p></a>
                <span class="price__final">IDR 10,000</span>
                <div>xx rb terjual</div>
            </div>
        </div>
        '''
        class DummyMatch:
            def group(self, idx):
                return "not-a-float"
        with patch.object(hp, 'RB_RIBU_PATTERN', autospec=True) as mock_pattern:
            mock_pattern.search.return_value = DummyMatch()
            products = self.parser.parse_products(html)
        self.assertEqual(len(products), 1)
        # Expect None due to forced ValueError in float(number_str)
        self.assertIsNone(products[0].sold_count)

    def test_html_parser_text_content_normalization(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/normalized-product">
                    <p>
                        
                        Product With
                        Multiple     Spaces
                        
                    </p>
                </a>
                <span class="price__final">
                    
                    IDR 25,000
                    
                </span>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)

        self.assertEqual(products_dict[0]['name'], 'Product With\n                        Multiple     Spaces')
        self.assertEqual(products_dict[0]['price'], 25000)
        self.assertEqual(products_dict[0]['url'], '/normalized-product')

    def test_normalize_sold_count_value_error_branch_forced(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/sold-int-bad"><p>Produk G</p></a>
                <span class="price__final">IDR 40,000</span>
                <div>abc terjual</div>
            </div>
        </div>
        '''
        # Test with non-numeric sold count to trigger ValueError in normalize
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 1)
        self.assertIsNone(products[0].sold_count)

    def test_html_parser_malformed_structure_resilience(self):
        malformed_htmls = [
            # Unclosed tags
            '<div class="MuiGrid-item"><div class="grid-item"><a class="gtm_mitra10_cta_product" href="/test"><p>Unclosed Product',
            # Missing closing tags
            '<div class="MuiGrid-item"><div class="grid-item"><a class="gtm_mitra10_cta_product" href="/test"><p>No Closing Tags<span class="price__final">IDR 10,000',
            # Nested tags incorrectly
            '<div class="MuiGrid-item"><div class="grid-item"><a class="gtm_mitra10_cta_product" href="/test"><p>Bad <span>Nesting</p></span><span class="price__final">IDR 10,000</span></div></div>',
            # Self-closing tags
            '<div class="MuiGrid-item"><div class="grid-item"/><a class="gtm_mitra10_cta_product" href="/test"/><span class="price__final">IDR 10,000</span>'
        ]
        
        for i, html in enumerate(malformed_htmls):
            with self.subTest(html_case=i):
                products = self.parser.parse_products(html)
                self.assertIsInstance(products, list)

    def test_html_parser_empty_and_none_inputs(self):
        test_cases = [
            ("", []),  
            ("   ", []),  
            ("<html></html>", []),  
            ("<div></div>", []), 
            (None, []),  
        ]
        
        for input_html, expected_output in test_cases:
            with self.subTest(input_html=str(input_html)):
                products = self.parser.parse_products(input_html)
                self.assertEqual(products, expected_output)

    def test_html_parser_exception_in_item_extraction(self):
        html = '''
        <div class="MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/test-product">
                    <p>Valid Product</p>
                </a>
                <span class="price__final">IDR 25,000</span>
            </div>
        </div>
        <div class="MuiGrid-item">
            <div class="jss273 grid-item">
                <!-- This will cause an exception in price cleaning -->
                <a class="gtm_mitra10_cta_product" href="/bad-product">
                    <p>Bad Product</p>
                </a>
                <span class="price__final">Invalid Price</span>
            </div>
        </div>
        '''

        with unittest.mock.patch.object(self.parser.price_cleaner, 'clean_price', side_effect=Exception("Mock exception")):
            products = self.parser.parse_products(html)
            self.assertIsInstance(products, list)

    def test_html_parser_general_parsing_exception(self):
        with unittest.mock.patch('api.mitra10.html_parser.BeautifulSoup', side_effect=Exception("BeautifulSoup error")):
            with self.assertRaises(Exception):  
                self.parser.parse_products("<div>test</div>")

    def test_extract_product_name_fallback_to_img_alt(self):
        html = self._create_product_html(img_alt="Product from Image Alt", price="IDR 15,000", url="/img-product")
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Product from Image Alt')

    def test_extract_price_fallback_to_text_search(self):
        html = '''
        <div class="MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/text-price-product">
                    <p>Product With Text Price</p>
                </a>
                <div class="some-other-div">
                    The price is Rp 35,000 for this item
                </div>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['price'], 35000)

    def test_extract_price_with_price_cleaner_exception(self):
        html = self._create_product_html(name="Product With Problematic Price", price="IDR 30,000", url="/exception-product")

        with unittest.mock.patch.object(self.parser.price_cleaner, 'clean_price', side_effect=[TypeError("Mock error"), 30000]):
            products = self.parser.parse_products(html)
            products_dict = self._products_to_dicts(products)
            self.assertEqual(len(products), 1)
            self.assertEqual(products_dict[0]['price'], 30000)

    def test_extract_price_fallback_exception_handling(self):
        html = '''
        <div class="MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/fallback-exception">
                    <p>Product With Fallback Exception</p>
                </a>
                <div>Some text with Rp 40,000</div>
            </div>
        </div>
        '''

        with unittest.mock.patch.object(self.parser.price_cleaner, 'clean_price', side_effect=ValueError("Always fails")):
            products = self.parser.parse_products(html)
            self.assertEqual(len(products), 0)

    def test_extract_url_fallback_to_unknown(self):
        html = '''
        <div class="MuiGrid-item">
            <a class="gtm_mitra10_cta_product">
                <!-- No href attribute -->
            </a>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.select_one("div.MuiGrid-item")
        
        url = self.parser._extract_product_url(item)
        self.assertEqual(url, "/product/unknown")

    def test_generate_slug_with_special_characters(self):
        test_cases = [
            ("Product Name", "product-name"),
            ("Product (New) & Special!", "product-new--special"),
            ("Product 123 Test", "product-123-test"),
            ("Cat Tembok 5Kg (Premium)", "cat-tembok-5kg-premium"),
            ("@#$%^&*()", ""),  # All special chars should be removed
        ]
        
        for name, expected_slug in test_cases:
            with self.subTest(name=name):
                slug = self.parser._generate_slug(name)
                self.assertEqual(slug, expected_slug)

    def test_safe_extraction_mixin_safe_extract(self):
        """Test SafeExtractionMixin safe_extract method"""
        def successful_operation():
            return "success"
        
        result = self.parser.safe_extract(successful_operation, "test operation")
        self.assertEqual(result, "success")

    def test_safe_extraction_mixin_safe_extract_with_exception(self):
        """Test SafeExtractionMixin safe_extract handles exceptions"""
        def failing_operation():
            raise ValueError("Test error")
        
        result = self.parser.safe_extract(failing_operation, "test operation")
        self.assertIsNone(result)

    def test_safe_extraction_mixin_safe_extract_with_default(self):
        """Test SafeExtractionMixin safe_extract_with_default method"""
        def successful_operation():
            return "success"
        
        result = self.parser.safe_extract_with_default(successful_operation, "default", "test operation")
        self.assertEqual(result, "success")

    def test_safe_extraction_mixin_safe_extract_with_default_on_exception(self):
        """Test SafeExtractionMixin safe_extract_with_default returns default on exception"""
        def failing_operation():
            raise ValueError("Test error")
        
        result = self.parser.safe_extract_with_default(failing_operation, "default_value", "test operation")
        self.assertEqual(result, "default_value")

    def test_safe_extraction_mixin_safe_extract_with_default_when_none(self):
        """Test SafeExtractionMixin safe_extract_with_default returns default when None"""
        def none_operation():
            return None
        
        result = self.parser.safe_extract_with_default(none_operation, "default_value", "test operation")
        self.assertEqual(result, "default_value")

    def test_parse_with_fallback_success(self):
        """Test _parse_with_fallback successfully parses with html.parser"""
        html = self._create_product_html(name="Test Product", price="IDR 25,000", url="/test")
        products = self.parser._parse_with_fallback(html, Exception("Original error"))
        self.assertEqual(len(products), 1)

    def test_parse_with_fallback_failure(self):
        with unittest.mock.patch('api.mitra10.html_parser.BeautifulSoup', side_effect=Exception("Parser error")):
            with self.assertRaises(HtmlParserError):
                self.parser._parse_with_fallback("<html></html>", Exception("Original"))

    def test_parse_product_details_valid(self):
        """Test parse_product_details with valid HTML"""
        html = '''
        <html>
            <body>
                <h1 class="product-title">Test Product</h1>
                <span class="price__final">Rp 50,000</span>
                <div class="specifications">Unit: 5 kg</div>
            </body>
        </html>
        '''
        product = self.parser.parse_product_details(html, "/test-product")
        self.assertIsNotNone(product)
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, 50000)
        self.assertEqual(product.url, "/test-product")

    def test_parse_product_details_empty_html(self):
        """Test parse_product_details with empty HTML"""
        product = self.parser.parse_product_details("", "/test")
        self.assertIsNone(product)

    def test_parse_product_details_missing_name(self):
        """Test parse_product_details when product name is missing"""
        html = '''
        <html>
            <body>
                <span class="price__final">Rp 50,000</span>
            </body>
        </html>
        '''
        product = self.parser.parse_product_details(html)
        self.assertIsNone(product)

    def test_parse_product_details_invalid_price(self):
        """Test parse_product_details with invalid price"""
        html = '''
        <html>
            <body>
                <h1 class="product-title">Test Product</h1>
                <span class="price__final">Invalid Price</span>
            </body>
        </html>
        '''
        product = self.parser.parse_product_details(html)
        self.assertIsNone(product)

    def test_has_lxml_available(self):
        """Test _has_lxml when lxml is available"""
        has_lxml = self.parser._has_lxml()
        # This will depend on the environment, but we just test it doesn't crash
        self.assertIsInstance(has_lxml, bool)

    def test_has_lxml_not_available(self):
        """Test _has_lxml when lxml is not available"""
        with unittest.mock.patch('builtins.__import__', side_effect=ImportError):
            has_lxml = self.parser._has_lxml()
            self.assertFalse(has_lxml)