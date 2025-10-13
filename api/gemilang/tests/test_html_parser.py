from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from api.interfaces import Product, HtmlParserError
from api.gemilang.html_parser import GemilangHtmlParser
from api.gemilang.price_cleaner import GemilangPriceCleaner
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
