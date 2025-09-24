from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from api.interfaces import Product, HtmlParserError
from api.juragan_material.html_parser import JuraganMaterialHtmlParser
from api.juragan_material.price_cleaner import JuraganMaterialPriceCleaner


class TestJuraganMaterialHtmlParser(TestCase):
    """Test cases for JuraganMaterialHtmlParser."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent.parent.parent
        fixture_path = base / "tests/fixtures/juraganmaterial_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")
    
    def setUp(self):
        self.parser = JuraganMaterialHtmlParser()
    
    def test_parse_fixture_html(self):
        """Test parsing the fixture HTML file."""
        products = self.parser.parse_products(self.mock_html)
        self.assertEqual(len(products), 3)
        
        product1 = products[0]
        self.assertEqual(product1.name, "Semen Holcim 40Kg")
        self.assertEqual(product1.price, 60500)
        self.assertEqual(product1.url, "/products/semen-holcim-40kg")
        
        product2 = products[1]
        self.assertEqual(product2.name, "Pasir Bangunan")
        self.assertEqual(product2.price, 120000)
        self.assertEqual(product2.url, "/products/pasir-bangunan-murah")
        
        product3 = products[2]
        self.assertEqual(product3.name, "Batu Bata Merah")
        self.assertEqual(product3.price, 1000)
        self.assertEqual(product3.url, "/products/batu-bata-merah")
    
    def test_parse_empty_html(self):
        """Test parsing empty HTML content."""
        products = self.parser.parse_products("")
        self.assertEqual(len(products), 0)
    
    def test_parse_html_with_no_products(self):
        """Test parsing HTML with no product elements."""
        html_no_products = "<html><body><div>No products found</div></body></html>"
        products = self.parser.parse_products(html_no_products)
        self.assertEqual(len(products), 0)
    
    def test_extract_product_with_missing_name(self):
        """Test extracting product with missing name."""
        html_missing_name = """
        <div class="product-card">
            <div class="product-card-price">
                <div class="price">Rp 10.000</div>
            </div>
        </div>
        """
        products = self.parser.parse_products(html_missing_name)
        self.assertEqual(len(products), 0)
    
    def test_extract_product_with_missing_price(self):
        """Test extracting product with missing price."""
        html_missing_price = """
        <div class="product-card">
            <a href="/test">
                <p class="product-name">Test Product</p>
            </a>
        </div>
        """
        products = self.parser.parse_products(html_missing_price)
        self.assertEqual(len(products), 0)
    
    def test_html_parser_error_handling(self):
        """Test HTML parser error handling."""
        with patch('api.juragan_material.html_parser.BeautifulSoup') as mock_soup:
            mock_soup.side_effect = Exception("Parsing error")
            with self.assertRaises(HtmlParserError) as context:
                self.parser.parse_products("<html></html>")
            self.assertIn("Failed to parse HTML", str(context.exception))