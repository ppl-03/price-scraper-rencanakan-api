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
    
    def test_extract_product_item_exception_handling(self):
        """Test exception handling when extracting individual product items."""
        html_with_broken_item = """
        <div class="product-card">
            <p class="product-name">Valid Product</p>
            <div class="product-card-price">
                <div class="price">Rp 10.000</div>
            </div>
        </div>
        <div class="product-card">
            <!-- This will cause an exception in extraction -->
            <p class="product-name">Broken Product</p>
        </div>
        """
        
        # Mock the _extract_product_from_item to raise an exception for second item
        original_method = self.parser._extract_product_from_item
        
        def mock_extract(item):
            name_elem = item.find('p', class_='product-name')
            if name_elem and 'Broken' in name_elem.get_text():
                raise ValueError("Simulated extraction error")
            return original_method(item)
        
        with patch.object(self.parser, '_extract_product_from_item', side_effect=mock_extract):
            products = self.parser.parse_products(html_with_broken_item)
            # Should still get the valid product, broken one should be skipped
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0].name, "Valid Product")
    
    def test_fallback_product_name_extraction(self):
        """Test fallback to direct p.product-name when no link exists."""
        html_no_link = """
        <div class="product-card">
            <p class="product-name">Product Without Link</p>
            <div class="product-card-price">
                <div class="price">Rp 15.000</div>
            </div>
        </div>
        """
        products = self.parser.parse_products(html_no_link)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Product Without Link")
    
    def test_fallback_url_generation_no_name(self):
        """Test fallback URL when no product name is available."""
        html_no_name_in_url = """
        <div class="product-card">
            <p class="product-name">Test Product</p>
            <div class="product-card-price">
                <div class="price">Rp 20.000</div>
            </div>
        </div>
        """
        # Mock to simulate no link and no name element for URL generation
        with patch.object(self.parser, '_extract_product_url') as mock_url:
            mock_url.return_value = "/products/product"  # Default fallback
            products = self.parser.parse_products(html_no_name_in_url)
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0].url, "/products/product")
    
    def test_price_extraction_with_type_value_errors(self):
        """Test price extraction with TypeError and ValueError handling."""
        # Create HTML with price that will cause cleaner errors, but also has fallback text
        html_bad_price = """
        <div class="product-card">
            <a href="/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <div class="product-card-price">
                <div class="price">Invalid Price Format</div>
            </div>
            <span>Rp 25.000</span>
        </div>
        """
        
        # Mock price cleaner to raise TypeError first, then work normally on fallback
        original_clean_price = self.parser.price_cleaner.clean_price
        call_count = 0
        
        def mock_clean_price(price_str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TypeError("Mocked TypeError")
            return original_clean_price(price_str)
        
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=mock_clean_price):
            products = self.parser.parse_products(html_bad_price)
            # Should have 1 product since fallback price extraction succeeds
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0].price, 25000)
    
    def test_fallback_price_extraction_with_rp_text(self):
        """Test fallback price extraction using text containing 'Rp'."""
        html_fallback_price = """
        <div class="product-card">
            <a href="/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <!-- No standard price structure, but has Rp text -->
            <span>Price: Rp 25.000</span>
        </div>
        """
        products = self.parser.parse_products(html_fallback_price)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].price, 25000)
    
    def test_fallback_price_extraction_with_invalid_price(self):
        """Test fallback price extraction when price is invalid."""
        html_invalid_fallback = """
        <div class="product-card">
            <a href="/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <!-- Rp text but invalid price -->
            <span>Rp Contact for price</span>
        </div>
        """
        products = self.parser.parse_products(html_invalid_fallback)
        # Should be no products since price is invalid (0)
        self.assertEqual(len(products), 0)
    
    def test_fallback_price_extraction_with_exception_handling(self):
        """Test exception handling in fallback price extraction."""
        html_with_rp_text = """
        <div class="product-card">
            <a href="/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <div class="product-card-price">
                <div class="price">Main Price</div>
            </div>
            <span>Rp 30.000</span>
        </div>
        """
        
        # Mock price cleaner to raise TypeError first, then ValueError in fallback
        call_count = 0
        
        def mock_clean_price(price_str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First attempt raises TypeError to trigger fallback
                raise TypeError("Mocked TypeError")
            # Fallback attempts raise ValueError
            raise ValueError("Mocked ValueError")
        
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=mock_clean_price):
            products = self.parser.parse_products(html_with_rp_text)
            # Should be no products since fallback price extraction fails
            self.assertEqual(len(products), 0)
    
    def test_fallback_url_generation_when_no_name_element(self):
        """Test URL generation fallback when no name element exists for URL generation."""
        # Create HTML with no link and no name element
        html_minimal = """
        <div class="product-card">
            <div class="product-card-price">
                <div class="price">Rp 15.000</div>
            </div>
        </div>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_minimal, 'html.parser')
        item = soup.find('div', class_='product-card')
        
        url = self.parser._extract_product_url(item)
        self.assertEqual(url, "/products/product")
    
    def test_fallback_price_extraction_multiple_rp_texts_with_continue(self):
        """Test fallback price extraction with multiple Rp texts where some cause exceptions."""
        html_multiple_rp = """
        <div class="product-card">
            <a href="/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <span>Rp invalid</span>
            <span>Rp also-invalid</span>
            <span>Rp 40.000</span>
        </div>
        """
        
        # Mock price cleaner to fail on first two attempts, succeed on third
        original_clean_price = self.parser.price_cleaner.clean_price
        call_count = 0
        
        def mock_clean_price(price_str):
            nonlocal call_count
            call_count += 1
            if 'invalid' in price_str and call_count <= 2:
                raise ValueError(f"Invalid price: {price_str}")
            return original_clean_price(price_str)
        
        with patch.object(self.parser.price_cleaner, 'clean_price', side_effect=mock_clean_price):
            products = self.parser.parse_products(html_multiple_rp)
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0].price, 40000)