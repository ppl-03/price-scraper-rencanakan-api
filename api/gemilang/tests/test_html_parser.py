from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from api.interfaces import Product, HtmlParserError
from api.gemilang.html_parser import GemilangHtmlParser
from api.gemilang.price_cleaner import GemilangPriceCleaner
from api.gemilang.unit_parser import GemilangUnitParser
class TestGemilangHtmlParser(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        fixture_path = base / "gemilang_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")
    def setUp(self):
        self.parser = GemilangHtmlParser()
    def test_parse_fixture_html(self):
        products = self.parser.parse_products(self.mock_html)
        self.assertEqual(len(products), 2)
        product1 = products[0]
        self.assertEqual(product1.name, "GML KUAS CAT 1inch")
        self.assertEqual(product1.price, 3600)
        self.assertEqual(product1.url, "https://gemilang-store.com/pusat/gml-kuas-cat-1inch")
        product2 = products[1]
        self.assertEqual(product2.name, "Cat Tembok Spectrum 5Kg")
        self.assertEqual(product2.price, 55000)
        self.assertEqual(product2.url, "https://gemilang-store.com/pusat/cat-tembok-spectrum-5kg")
    def test_parse_empty_html(self):
        products = self.parser.parse_products("")
        self.assertEqual(len(products), 0)
    def test_parse_html_with_no_products(self):
        html_no_products = "<html><body><div>No products found</div></body></html>"
        products = self.parser.parse_products(html_no_products)
        self.assertEqual(len(products), 0)
    def test_parse_malformed_html(self):
        malformed_html = "<div class='item-product'><a href='/test'><p>incomplete"
        products = self.parser.parse_products(malformed_html)
        self.assertIsInstance(products, list)
    def test_extract_product_with_missing_name(self):
        html_missing_name = """
        <div class="item-product">
            <div class="price-wrapper">
                <p class="price">Rp 10.000</p>
            </div>
        </div>
        """
        products = self.parser.parse_products(html_missing_name)
        self.assertEqual(len(products), 0)
    def test_extract_product_with_missing_price(self):
        html_missing_price = """
        <div class="item-product">
            <a href="/test">
                <p class="product-name">Test Product</p>
            </a>
        </div>
        """
        products = self.parser.parse_products(html_missing_price)
        self.assertEqual(len(products), 0)
    def test_extract_product_with_zero_price(self):
        html_zero_price = """
        <div class="item-product">
            <a href="/test">
                <p class="product-name">Test Product</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Free</p>
            </div>
        </div>
        """
        products = self.parser.parse_products(html_zero_price)
        self.assertEqual(len(products), 0)
    def test_extract_product_name_from_different_elements(self):
        html1 = """
        <div class="item-product">
            <p class="product-name">Direct Name</p>
            <div class="price-wrapper"><p class="price">Rp 10.000</p></div>
        </div>
        """
        html2 = """
        <div class="item-product">
            <a href="/test">
                <p class="product-name">Link Name</p>
            </a>
            <div class="price-wrapper"><p class="price">Rp 10.000</p></div>
        </div>
        """
        html3 = """
        <div class="item-product">
            <img src="/image.jpg" alt="Image Alt Name" />
            <div class="price-wrapper"><p class="price">Rp 10.000</p></div>
        </div>
        """
        for html, expected_name in [(html1, "Direct Name"), (html2, "Link Name"), (html3, "Image Alt Name")]:
            with self.subTest(expected_name=expected_name):
                products = self.parser.parse_products(html)
                self.assertEqual(len(products), 1)
                self.assertEqual(products[0].name, expected_name)
    def test_extract_product_url_generation(self):
        html_with_href = """
        <div class="item-product">
            <a href="/actual/product/url">
                <p class="product-name">Test Product</p>
            </a>
            <div class="price-wrapper"><p class="price">Rp 10.000</p></div>
        </div>
        """
        products = self.parser.parse_products(html_with_href)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].url, "https://gemilang-store.com/actual/product/url")
        html_without_href = """
        <div class="item-product">
            <p class="product-name">Test Product Name</p>
            <div class="price-wrapper"><p class="price">Rp 10.000</p></div>
        </div>
        """
        products = self.parser.parse_products(html_without_href)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].url, "https://gemilang-store.com/pusat/test-product-name")
    def test_price_extraction_fallback(self):
        html_fallback_price = """
        <div class="item-product">
            <p class="product-name">Test Product</p>
            <span>Price: Rp 25.000 available now</span>
        </div>
        """
        products = self.parser.parse_products(html_fallback_price)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].price, 25000)
    def test_custom_price_cleaner(self):
        mock_cleaner = Mock(spec=GemilangPriceCleaner)
        mock_cleaner.clean_price.return_value = 99999
        mock_cleaner.is_valid_price.return_value = True
        parser = GemilangHtmlParser(price_cleaner=mock_cleaner)
        html = """
        <div class="item-product">
            <p class="product-name">Test Product</p>
            <div class="price-wrapper"><p class="price">Rp 10.000</p></div>
        </div>
        """
        products = parser.parse_products(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].price, 99999)
        mock_cleaner.clean_price.assert_called()
        mock_cleaner.is_valid_price.assert_called_with(99999)
    def test_html_parser_error_handling(self):
        with patch('api.gemilang.html_parser.BeautifulSoup') as mock_soup:
            mock_soup.side_effect = Exception("Parsing error")
            with self.assertRaises(HtmlParserError) as context:
                self.parser.parse_products("<html></html>")
            self.assertIn("Failed to parse HTML", str(context.exception))
    def test_product_extraction_error_logging(self):
        html_mixed = """
        <div class="item-product">
            <p class="product-name">Good Product</p>
            <div class="price-wrapper"><p class="price">Rp 10.000</p></div>
        </div>
        <div class="item-product">
        </div>
        """
        products = self.parser.parse_products(html_mixed)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Good Product")
    def test_html_parser_critical_exception(self):
        with patch('api.gemilang.html_parser.BeautifulSoup', side_effect=Exception("Critical parsing error")):
            with self.assertRaises(HtmlParserError) as context:
                self.parser.parse_products("<html></html>")
            self.assertIn("Failed to parse HTML", str(context.exception))
            self.assertIn("Critical parsing error", str(context.exception))
    def test_product_extraction_with_exception_logging(self):
        html_with_problematic_item = """
        <div class="item-product">
            <p class="product-name">Normal Product</p>
            <div class="price-wrapper"><p class="price">Rp 10.000</p></div>
        </div>
        <div class="item-product">
            <p class="product-name">Problem Product</p>
            <div class="price-wrapper"><p class="price">Rp 5.000</p></div>
        </div>
        """
        with patch.object(self.parser, '_extract_product_from_item', side_effect=[
            Product(name="Normal Product", price=10000, url="/test"),
            Exception("Extraction failed")
        ]):
            with patch('api.gemilang.html_parser.logger') as mock_logger:
                products = self.parser.parse_products(html_with_problematic_item)
                self.assertEqual(len(products), 1)
                self.assertEqual(products[0].name, "Normal Product")
                mock_logger.warning.assert_called_once_with("Failed to extract product from item: Extraction failed")
    def test_price_extraction_with_type_error(self):
        html_type_error = """
        <div class="item-product">
            <p class="product-name">Test Product</p>
            <div class="price-wrapper">
                <p class="price">Invalid Price</p>
            </div>
        </div>
        """
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=TypeError("Invalid type")):
            products = self.parser.parse_products(html_type_error)
            self.assertEqual(len(products), 0)  # No valid price found
    def test_price_extraction_with_value_error(self):
        html_value_error = """
        <div class="item-product">
            <p class="product-name">Test Product</p>
            <div class="price-wrapper">
                <p class="price">Invalid Value</p>
            </div>
        </div>
        """
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=ValueError("Invalid value")):
            products = self.parser.parse_products(html_value_error)
            self.assertEqual(len(products), 0)  # No valid price found
    def test_fallback_price_extraction_with_errors(self):
        html_fallback = """
        <div class="item-product">
            <p class="product-name">Test Product</p>
            <span>Price: Rp 15.000</span>
            <span>Also: Rp 20.000</span>
        </div>
        """
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=TypeError("Always fail")):
            with patch.object(self.parser.price_cleaner, 'is_valid_price', return_value=False):
                products = self.parser.parse_products(html_fallback)
                self.assertEqual(len(products), 0)  # Invalid price means no product


class TestParseProductDetails(TestCase):
    
    def setUp(self):
        self.parser = GemilangHtmlParser()
    
    def test_parse_product_details_with_empty_html(self):
        result = self.parser.parse_product_details("")
        self.assertIsNone(result)
    
    def test_parse_product_details_with_none_html(self):
        result = self.parser.parse_product_details(None)
        self.assertIsNone(result)
    
    def test_parse_product_details_with_valid_html(self):
        html = """
        <html>
            <h1>Test Product Name</h1>
            <div class="price">Rp 50.000</div>
            <table>
                <tr><th>Spesifikasi</th><td>Unit: Pcs</td></tr>
            </table>
        </html>
        """
        result = self.parser.parse_product_details(html, "https://test.com/product")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Test Product Name")
        self.assertEqual(result.price, 50000)
        self.assertEqual(result.url, "https://test.com/product")
    
    def test_parse_product_details_without_url(self):
        html = """
        <html>
            <h1>Test Product</h1>
            <div class="price">Rp 25.000</div>
        </html>
        """
        result = self.parser.parse_product_details(html)
        self.assertIsNotNone(result)
        self.assertEqual(result.url, "")
    
    def test_parse_product_details_no_name_found(self):
        html = """
        <html>
            <div class="price">Rp 30.000</div>
        </html>
        """
        result = self.parser.parse_product_details(html)
        self.assertIsNone(result)
    
    def test_parse_product_details_invalid_price(self):
        html = """
        <html>
            <h1>Test Product</h1>
            <div class="price">Free</div>
        </html>
        """
        result = self.parser.parse_product_details(html)
        self.assertIsNone(result)
    
    def test_parse_product_details_with_exception(self):
        with patch('api.gemilang.html_parser.BeautifulSoup', side_effect=Exception("Parse error")):
            result = self.parser.parse_product_details("<html></html>")
            self.assertIsNone(result)
    
    def test_parse_product_details_with_unit(self):
        html = """
        <html>
            <h1>Cement 50kg</h1>
            <div class="price">Rp 100.000</div>
        </html>
        """
        with patch.object(self.parser.unit_parser, 'parse_unit', return_value="KG"):
            result = self.parser.parse_product_details(html)
            self.assertIsNotNone(result)
            self.assertEqual(result.unit, "KG")


class TestExtractProductNameFromPage(TestCase):
    
    def setUp(self):
        self.parser = GemilangHtmlParser()
    
    def test_extract_name_from_h1(self):
        html = "<html><h1>Product Name from H1</h1></html>"
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_name_from_page(soup)
        self.assertEqual(result, "Product Name from H1")
    
    def test_extract_name_from_product_title_class(self):
        html = '<html><div class="product-title">Product Title Class</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_name_from_page(soup)
        self.assertEqual(result, "Product Title Class")
    
    def test_extract_name_from_product_name_class(self):
        html = '<html><p class="product-name">Product Name Class</p></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_name_from_page(soup)
        self.assertEqual(result, "Product Name Class")
    
    def test_extract_name_from_title_tag(self):
        html = '<html><head><title>Title Tag Product</title></head></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_name_from_page(soup)
        self.assertEqual(result, "Title Tag Product")
    
    def test_extract_name_skips_short_names(self):
        html = '<html><h1>AB</h1><div class="product-title">Real Product Name</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_name_from_page(soup)
        self.assertEqual(result, "Real Product Name")
    
    def test_extract_name_returns_none_when_no_name(self):
        html = '<html><div>No product info here</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_name_from_page(soup)
        self.assertIsNone(result)
    
    def test_extract_name_with_whitespace_stripping(self):
        html = '<html><h1>  Product With Spaces  </h1></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_name_from_page(soup)
        self.assertEqual(result, "Product With Spaces")


class TestExtractProductPriceFromPage(TestCase):
    
    def setUp(self):
        self.parser = GemilangHtmlParser()
    
    def test_extract_price_from_price_class(self):
        html = '<html><div class="price">Rp 45.000</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 45000)
    
    def test_extract_price_from_product_price_class(self):
        html = '<html><span class="product-price">Rp 35.000</span></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 35000)
    
    def test_extract_price_from_harga_class(self):
        html = '<html><div class="harga">Rp 25.000</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 25000)
    
    def test_extract_price_from_id_price(self):
        html = '<html><div id="price">Rp 55.000</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 55000)
    
    def test_extract_price_from_class_attribute_selector(self):
        html = '<html><div class="current-price-display">Rp 65.000</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 65000)
    
    def test_extract_price_from_id_attribute_selector(self):
        html = '<html><span id="product-price-123">Rp 75.000</span></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 75000)
    
    def test_extract_price_from_price_current_class(self):
        html = '<html><div class="price-current">Rp 85.000</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 85000)
    
    def test_extract_price_skips_invalid_prices(self):
        html = '''
        <html>
            <div class="price">Invalid</div>
            <div class="product-price">Rp 50.000</div>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 50000)
    
    def test_extract_price_with_type_error_handling(self):
        html = '<html><div class="price">Rp 40.000</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=TypeError("Type error")):
            result = self.parser._extract_product_price_from_page(soup)
            self.assertEqual(result, 0)
    
    def test_extract_price_with_value_error_handling(self):
        html = '<html><div class="price">Rp 30.000</div></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=ValueError("Value error")):
            result = self.parser._extract_product_price_from_page(soup)
            self.assertEqual(result, 0)
    
    def test_extract_price_fallback_rp_pattern(self):
        html = '<html><body>Product costs Rp 12.000 only</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 12000)
    
    def test_extract_price_fallback_idr_pattern(self):
        html = '<html><body>Price: IDR 15.000</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 15000)
    
    def test_extract_price_fallback_rupiah_pattern(self):
        html = '<html><body>Costs 18000 rupiah</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 18000)
    
    def test_extract_price_fallback_with_commas(self):
        html = '<html><body>Rp 1,250,000</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 1250000)
    
    def test_extract_price_fallback_with_dots(self):
        html = '<html><body>Rp 1.250.000</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 1250000)
    
    def test_extract_price_fallback_skips_out_of_range_low(self):
        html = '<html><body>Rp 50 only</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 0)
    
    def test_extract_price_fallback_skips_out_of_range_high(self):
        html = '<html><body>Rp 99.000.000</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 0)
    
    def test_extract_price_fallback_skips_invalid_after_cleaning(self):
        html = '<html><body>Rp 5.000</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(self.parser.price_cleaner, 'is_valid_price', return_value=False):
            result = self.parser._extract_product_price_from_page(soup)
            self.assertEqual(result, 0)
    
    def test_extract_price_fallback_handles_value_error_in_conversion(self):
        html = '<html><body>Rp invalid.price</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 0)
    
    def test_extract_price_fallback_handles_type_error_in_conversion(self):
        html = '<html><body>Rp 12.000</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=TypeError("Type error")):
            result = self.parser._extract_product_price_from_page(soup)
            self.assertEqual(result, 0)
    
    def test_extract_price_returns_zero_when_no_price_found(self):
        html = '<html><body>No price here</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertEqual(result, 0)
    
    def test_extract_price_multiple_matches_returns_first_valid(self):
        html = '''
        <html>
            <body>
                Prices: Rp 10.000 or Rp 20.000
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = self.parser._extract_product_price_from_page(soup)
        self.assertIn(result, [10000, 20000])


class TestExtractProductUrl(TestCase):
    
    def setUp(self):
        self.parser = GemilangHtmlParser()
    
    def test_extract_url_with_absolute_http_url(self):
        html = '''
        <div class="item-product">
            <a href="http://external.com/product">Link</a>
            <p class="product-name">Test Product</p>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item-product')
        result = self.parser._extract_product_url(item)
        self.assertEqual(result, "https://external.com/product")
    
    def test_extract_url_with_absolute_https_url(self):
        html = '''
        <div class="item-product">
            <a href="https://external.com/product">Link</a>
            <p class="product-name">Test Product</p>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item-product')
        result = self.parser._extract_product_url(item)
        self.assertEqual(result, "https://external.com/product")
    
    def test_extract_url_with_relative_no_leading_slash(self):
        html = '''
        <div class="item-product">
            <a href="product/123">Link</a>
            <p class="product-name">Test Product</p>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item-product')
        result = self.parser._extract_product_url(item)
        self.assertEqual(result, "https://gemilang-store.com/product/123")


class TestHasLxml(TestCase):
    
    def setUp(self):
        self.parser = GemilangHtmlParser()
    
    def test_has_lxml_returns_true_when_lxml_available(self):
        result = self.parser._has_lxml()
        self.assertIsInstance(result, bool)
        
        with patch('builtins.__import__', return_value=Mock()):
            result = self.parser._has_lxml()
            self.assertTrue(result)
