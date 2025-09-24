from django.test import TestCase
from api.mitra10.html_parser import Mitra10HtmlParser


class TestsMitra10HTMLParser(TestCase):

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

    def test_scrape_mitra10_valid_products(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6 MuiGrid-grid-sm-4 MuiGrid-grid-md-3">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" href="/test-product">
              <p class="MuiTypography-root MuiTypography-body1 MuiTypography-alignLeft">
                Test Product
              </p>
            </a>
            <div class="jss298">
              <span class="MuiTypography-root price__final MuiTypography-caption MuiTypography-alignLeft">
                IDR 25,000
              </span>
            </div>
          </div>
        </div>
        '''
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
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" href="/test-product">
            </a>
            <div class="jss298">
              <span class="price__final">IDR 25,000</span>
            </div>
          </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 0)

    def test_scrape_mitra10_missing_price(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" href="/test-product">
              <p>Test Product</p>
            </a>
            <div class="jss298">
            </div>
          </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 0)  # Products with no price should be filtered out

    def test_scrape_mitra10_missing_url(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product">
              <p>Test Product</p>
            </a>
            <div class="jss298">
              <span class="price__final">IDR 25,000</span>
            </div>
          </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)  # Should generate fallback URL
        self.assertEqual(products_dict[0]['url'], '/product/test-product')  

    def test_scrape_mitra10_multiple_products(self):
        html = '''
        <div class="product-list">
            <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
              <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/product-1">
                  <p>Product 1</p>
                </a>
                <div class="jss298">
                  <span class="price__final">IDR 10,000</span>
                </div>
              </div>
            </div>
            <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
              <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/product-2">
                  <p>Product 2</p>
                </a>
                <div class="jss298">
                  <span class="price__final">IDR 20,000</span>
                </div>
              </div>
            </div>
        </div>
        '''
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
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" href="/test-product">
              <p>Test Product</p>
            </a>
            <div class="jss298">
              <span class="price__final">IDR 0</span>
            </div>
          </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 0)  # Products with 0 price should be filtered out

    def test_mitra10_product_name_exact_match(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" href="/exact-product-name">
              <p class="MuiTypography-root MuiTypography-body1 MuiTypography-alignLeft">
                Exact Product Name
              </p>
            </a>
            <div class="jss298">
              <span class="price__final">IDR 15,000</span>
            </div>
          </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Exact Product Name')

    def test_mitra10_product_name_with_special_characters(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" href="/special-product">
              <p>Product & Tools 100%</p>
            </a>
            <div class="jss298">
              <span class="price__final">IDR 25,000</span>
            </div>
          </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Product & Tools 100%')

    def test_mitra10_product_name_with_numbers(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" href="/numbered-product">
              <p>Cat Tembok 5Kg Premium 2024</p>
            </a>
            <div class="jss298">
              <span class="price__final">IDR 45,000</span>
            </div>
          </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Cat Tembok 5Kg Premium 2024')

    def test_mitra10_product_name_with_whitespace(self):
        html = '''
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-6">
          <div class="jss273 grid-item">
            <a class="gtm_mitra10_cta_product" href="/whitespace-product">
              <p>  Product With Spaces  </p>
            </a>
            <div class="jss298">
              <span class="price__final">IDR 12,000</span>
            </div>
          </div>
        </div>
        '''
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
        self.assertEqual(len(products), 2)  # Both containers have MuiGrid-item class
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

    def test_html_parser_text_content_normalization(self):
        """Test HTML parser's text content normalization and whitespace handling"""
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
        """Test that exceptions during item extraction are caught and logged"""
        # Create HTML that will cause an exception in _extract_product_from_item
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
        # Mock the price cleaner to raise an exception
        import unittest.mock
        with unittest.mock.patch.object(self.parser.price_cleaner, 'clean_price', side_effect=Exception("Mock exception")):
            products = self.parser.parse_products(html)
            # Should still return some products despite exceptions
            self.assertIsInstance(products, list)

    def test_html_parser_general_parsing_exception(self):
        """Test that general parsing exceptions are properly raised"""
        # Mock BeautifulSoup to raise an exception
        import unittest.mock
        with unittest.mock.patch('api.mitra10.html_parser.BeautifulSoup', side_effect=Exception("BeautifulSoup error")):
            with self.assertRaises(Exception):  # Should raise HtmlParserError
                self.parser.parse_products("<div>test</div>")

    def test_extract_product_name_fallback_to_img_alt(self):
        """Test fallback to img alt attribute when p tag is missing"""
        html = '''
        <div class="MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/img-product">
                    <img alt="Product from Image Alt" src="test.jpg">
                </a>
                <span class="price__final">IDR 15,000</span>
            </div>
        </div>
        '''
        products = self.parser.parse_products(html)
        products_dict = self._products_to_dicts(products)
        self.assertEqual(len(products), 1)
        self.assertEqual(products_dict[0]['name'], 'Product from Image Alt')

    def test_extract_price_fallback_to_text_search(self):
        """Test price extraction fallback to searching for Rp/IDR in text"""
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
        """Test price extraction when price cleaner raises exception"""
        html = '''
        <div class="MuiGrid-item">
            <div class="jss273 grid-item">
                <a class="gtm_mitra10_cta_product" href="/exception-product">
                    <p>Product With Problematic Price</p>
                </a>
                <span class="price__final">IDR 30,000</span>
            </div>
        </div>
        '''
        # Mock price cleaner to raise TypeError for main price element
        import unittest.mock
        with unittest.mock.patch.object(self.parser.price_cleaner, 'clean_price', side_effect=[TypeError("Mock error"), 30000]):
            products = self.parser.parse_products(html)
            products_dict = self._products_to_dicts(products)
            self.assertEqual(len(products), 1)
            self.assertEqual(products_dict[0]['price'], 30000)

    def test_extract_price_fallback_exception_handling(self):
        """Test exception handling in fallback price extraction"""
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
        # Mock price cleaner to raise exception for all calls
        import unittest.mock
        with unittest.mock.patch.object(self.parser.price_cleaner, 'clean_price', side_effect=ValueError("Always fails")):
            products = self.parser.parse_products(html)
            # Should return empty list since no valid price found and exceptions caught
            self.assertEqual(len(products), 0)
  