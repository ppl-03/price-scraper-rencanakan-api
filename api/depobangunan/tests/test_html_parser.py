import unittest
from unittest.mock import Mock, patch
import os
from pathlib import Path
from api.depobangunan.html_parser import DepoHtmlParser
from api.depobangunan.price_cleaner import DepoPriceCleaner
from api.interfaces import HtmlParserError, Product


class TestDepoHtmlParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = DepoHtmlParser()
    
    def test_parse_products_with_depo_mock_html(self):
        test_dir = Path(__file__).parent
        fixture_path = test_dir / 'depo_mock_results.html'
        
        with open(fixture_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        products = self.parser.parse_products(html_content)
        
        # Should find 3 products from the mock HTML
        self.assertEqual(len(products), 3)
        
        # Verify first product (regular price)
        product_a = products[0]
        self.assertEqual(product_a.name, "Produk A")
        self.assertEqual(product_a.price, 3600)
        self.assertEqual(product_a.url, "/produk-a.html")
        
        # Verify second product (regular price)
        product_b = products[1]
        self.assertEqual(product_b.name, "Produk B")
        self.assertEqual(product_b.price, 125000)
        self.assertEqual(product_b.url, "/produk-b.html")
        
        # Verify third product (discounted price)
        product_c = products[2]
        self.assertEqual(product_c.name, "AQUA PROOF 061 ABU-ABU 1KG: Cat pelapis anti bocor yang tahan lama dan elastis")
        self.assertEqual(product_c.price, 59903)  # Should get the special/discounted price
        self.assertEqual(product_c.url, "https://www.depobangunan.co.id/aqua-proof-045-merah-delima-20kg.html")
    
    def test_parse_products_empty_html(self):
        products = self.parser.parse_products("")
        self.assertEqual(len(products), 0)
    
    def test_parse_products_no_products_html(self):
        html_content = """
        <html>
        <body>
            <div>No products found</div>
        </body>
        </html>
        """
        products = self.parser.parse_products(html_content)
        self.assertEqual(len(products), 0)
    
    def test_parse_products_malformed_html(self):
        html_content = "<div><incomplete html"
        products = self.parser.parse_products(html_content)
        self.assertEqual(len(products), 0)
    
    def test_parse_products_with_invalid_prices(self):
        html_content = """
        <ul class="products list items product-items">
          <li class="item product product-item">
            <div class="product-item-info">
              <div class="product details product-item-details">
                <strong class="product name product-item-name">
                  <a href="/produk-no-price.html">Product Without Price</a>
                </strong>
                <div class="price-box price-final_price">
                  <span class="price-wrapper" data-price-type="finalPrice">
                    <span class="price">No price</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>
        """
        products = self.parser.parse_products(html_content)
        self.assertEqual(len(products), 0)
    
    def test_parse_products_with_missing_name(self):
        html_content = """
        <ul class="products list items product-items">
          <li class="item product product-item">
            <div class="product-item-info">
              <div class="product details product-item-details">
                <div class="price-box price-final_price">
                  <span class="price-wrapper" data-price-type="finalPrice" data-price-amount="1000">
                    <span class="price">Rp 1.000</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>
        """
        products = self.parser.parse_products(html_content)
        self.assertEqual(len(products), 0)
    
    def test_parse_products_with_custom_price_cleaner(self):
        mock_price_cleaner = Mock(spec=DepoPriceCleaner)
        mock_price_cleaner.clean_price.return_value = 12345
        mock_price_cleaner.is_valid_price.return_value = True
        
        parser = DepoHtmlParser(price_cleaner=mock_price_cleaner)
        
        html_content = """
        <ul class="products list items product-items">
          <li class="item product product-item">
            <div class="product-item-info">
              <div class="product details product-item-details">
                <strong class="product name product-item-name">
                  <a href="/test.html">Test Product</a>
                </strong>
                <div class="price-box price-final_price">
                  <span class="price-wrapper" data-price-type="finalPrice">
                    <span class="price">Test Price</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>
        """
        
        products = parser.parse_products(html_content)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].price, 12345)
        mock_price_cleaner.clean_price.assert_called()
        mock_price_cleaner.is_valid_price.assert_called_with(12345)
    
    def test_parse_products_handles_individual_product_errors(self):
        html_content = """
        <ul class="products list items product-items">
          <li class="item product product-item">
            <div class="product-item-info">
              <div class="product details product-item-details">
                <strong class="product name product-item-name">
                  <a href="/good-product.html">Good Product</a>
                </strong>
                <div class="price-box price-final_price">
                  <span class="price-wrapper" data-price-type="finalPrice" data-price-amount="1000">
                    <span class="price">Rp 1.000</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>
        """
        products = self.parser.parse_products(html_content)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Good Product")
    
    def test_parse_products_with_data_price_amount(self):
        html_content = """
        <ul class="products list items product-items">
          <li class="item product product-item">
            <div class="product-item-info">
              <div class="product details product-item-details">
                <strong class="product name product-item-name">
                  <a href="/test.html">Test Product</a>
                </strong>
                <div class="price-box price-final_price">
                  <span class="price-wrapper" data-price-type="finalPrice" data-price-amount="5000">
                    <span class="price">Rp 5.000</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>
        """
        products = self.parser.parse_products(html_content)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].price, 5000)
    
    def test_parse_products_with_extraction_exception(self):
        # Create a parser that will raise an exception in price cleaning
        mock_price_cleaner = Mock(spec=DepoPriceCleaner)
        mock_price_cleaner.clean_price.side_effect = Exception("Test exception")
        mock_price_cleaner.is_valid_price.return_value = False
        
        parser = DepoHtmlParser(price_cleaner=mock_price_cleaner)
        
        html_content = """
        <ul class="products list items product-items">
          <li class="item product product-item">
            <div class="product-item-info">
              <div class="product details product-item-details">
                <strong class="product name product-item-name">
                  <a href="/test.html">Test Product</a>
                </strong>
                <div class="price-box price-final_price">
                  <span class="price-wrapper" data-price-type="finalPrice">
                    <span class="price">Rp 1.000</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>
        """
        
        # This should not raise exception and return empty list
        products = parser.parse_products(html_content)
        self.assertEqual(len(products), 0)
    
    def test_extract_product_name_from_direct_text(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div class="product-item-info">
            <div class="product details product-item-details">
              <strong class="product name product-item-name">Direct Product Name</strong>
            </div>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_product_name(item)
        self.assertEqual(result, "Direct Product Name")
    
    def test_extract_product_name_no_name_element(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div class="product-item-info">
            <div class="product details product-item-details">
              <div>No name here</div>
            </div>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_product_name(item)
        self.assertIsNone(result)
    
    def test_extract_product_url_no_name_element(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div class="product-item-info">
            <div class="product details product-item-details">
              <div>No name here</div>
            </div>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_product_url(item)
        self.assertEqual(result, "")
    
    def test_extract_product_url_no_link(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div class="product-item-info">
            <div class="product details product-item-details">
              <strong class="product name product-item-name">Product Name</strong>
            </div>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_product_url(item)
        self.assertEqual(result, "")
    
    def test_extract_price_from_data_attribute_with_invalid_data(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <span data-price-type="finalPrice" data-price-amount="invalid">
            <span class="price">Rp 1.000</span>
          </span>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_data_attribute(item)
        self.assertEqual(result, 0)
    
    def test_extract_price_from_special_price_no_wrapper(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <span class="special-price">
            <span class="price">Rp 1.000</span>
          </span>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_special_price(item)
        self.assertEqual(result, 0)
    
    def test_extract_price_from_special_price_with_data_amount(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <span class="special-price">
            <span data-price-type="finalPrice" data-price-amount="5000">
              <span class="price">Rp 5.000</span>
            </span>
          </span>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_special_price(item)
        self.assertEqual(result, 5000)
    
    def test_extract_price_from_special_price_with_invalid_data_amount(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <span class="special-price">
            <span data-price-type="finalPrice" data-price-amount="invalid">
              <span class="price">Rp 5.000</span>
            </span>
          </span>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_special_price(item)
        self.assertEqual(result, 5000)
    
    def test_extract_price_from_special_price_no_price_span(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <span class="special-price">
            <span data-price-type="finalPrice">
              <div>No price span</div>
            </span>
          </span>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_special_price(item)
        self.assertEqual(result, 0)
    
    def test_extract_price_from_regular_price_no_price_box(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div>No price box</div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_regular_price(item)
        self.assertEqual(result, 0)
    
    def test_extract_price_from_regular_price_no_wrapper(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div class="price-box price-final_price">
            <span class="price">Rp 1.000</span>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_regular_price(item)
        self.assertEqual(result, 0)
    
    def test_extract_price_from_regular_price_with_data_amount(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div class="price-box price-final_price">
            <span data-price-type="finalPrice" data-price-amount="3000">
              <span class="price">Rp 3.000</span>
            </span>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_regular_price(item)
        self.assertEqual(result, 3000)
    
    def test_extract_price_from_regular_price_with_invalid_data_amount(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div class="price-box price-final_price">
            <span data-price-type="finalPrice" data-price-amount="invalid">
              <span class="price">Rp 3.000</span>
            </span>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_regular_price(item)
        self.assertEqual(result, 3000)
    
    def test_extract_price_from_regular_price_no_price_span(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div class="price-box price-final_price">
            <span data-price-type="finalPrice">
              <div>No price span</div>
            </span>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_regular_price(item)
        self.assertEqual(result, 0)
    
    def test_extract_price_from_text_search_no_rp_text(self):
        from bs4 import BeautifulSoup
        
        html_content = """
        <li class="item product product-item">
          <div>No price text here</div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_price_from_text_search(item)
        self.assertEqual(result, 0)
    
    def test_extract_price_from_text_search_invalid_price(self):
        from bs4 import BeautifulSoup
        
        mock_price_cleaner = Mock(spec=DepoPriceCleaner)
        mock_price_cleaner.clean_price.return_value = 5000
        mock_price_cleaner.is_valid_price.return_value = False
        
        parser = DepoHtmlParser(price_cleaner=mock_price_cleaner)
        
        html_content = """
        <li class="item product product-item">
          <div>Rp invalid price</div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = parser._extract_price_from_text_search(item)
        self.assertEqual(result, 0)
    
    def test_clean_price_text_with_exception(self):
        mock_price_cleaner = Mock(spec=DepoPriceCleaner)
        mock_price_cleaner.clean_price.side_effect = ValueError("Test error")
        
        parser = DepoHtmlParser(price_cleaner=mock_price_cleaner)
        
        result = parser._clean_price_text("invalid price")
        self.assertEqual(result, 0)
    
    @patch('api.depobangunan.html_parser.logger')
    def test_parse_products_logs_product_count(self, mock_logger):
        html_content = """
        <ul class="products list items product-items">
          <li class="item product product-item">
            <div class="product-item-info">
              <div class="product details product-item-details">
                <strong class="product name product-item-name">
                  <a href="/test.html">Test Product</a>
                </strong>
                <div class="price-box price-final_price">
                  <span class="price-wrapper" data-price-type="finalPrice" data-price-amount="1000">
                    <span class="price">Rp 1.000</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>
        """
        
        self.parser.parse_products(html_content)
        
        # Verify logging calls
        mock_logger.info.assert_any_call("Found 1 product items in HTML")
        mock_logger.info.assert_any_call("Successfully parsed 1 products")
    
    @patch('api.depobangunan.html_parser.logger')
    def test_parse_products_logs_individual_errors(self, mock_logger):
        # Create a parser that will fail on product extraction
        mock_price_cleaner = Mock(spec=DepoPriceCleaner)
        mock_price_cleaner.clean_price.side_effect = Exception("Test exception")
        
        parser = DepoHtmlParser(price_cleaner=mock_price_cleaner)
        
        html_content = """
        <ul class="products list items product-items">
          <li class="item product product-item">
            <div class="product-item-info">
              <div class="product details product-item-details">
                <strong class="product name product-item-name">
                  <a href="/test.html">Test Product</a>
                </strong>
                <div class="price-box price-final_price">
                  <span class="price-wrapper" data-price-type="finalPrice">
                    <span class="price">Rp 1.000</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>
        """
        
        parser.parse_products(html_content)
        
        # Verify error logging
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        self.assertIn("Failed to extract product from item", warning_call)
    
    def test_parse_products_with_html_parser_error(self):
        from api.interfaces import HtmlParserError
        
        # Create a parser that will fail during BeautifulSoup parsing
        with patch('api.depobangunan.html_parser.BeautifulSoup') as mock_soup:
            mock_soup.side_effect = Exception("BeautifulSoup parsing error")
            
            with self.assertRaises(HtmlParserError) as context:
                self.parser.parse_products("<html>content</html>")
            
            self.assertIn("Failed to parse HTML", str(context.exception))
            self.assertIn("BeautifulSoup parsing error", str(context.exception))
    
    def test_extract_price_with_no_valid_methods(self):
        from bs4 import BeautifulSoup
        
        # Create HTML with no recognizable price structure
        html_content = """
        <li class="item product product-item">
          <div>No price information</div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_product_price(item)
        self.assertEqual(result, 0)
    
    def test_extract_price_from_text_search_multiple_invalid(self):
        from bs4 import BeautifulSoup
        
        mock_price_cleaner = Mock(spec=DepoPriceCleaner)
        mock_price_cleaner.clean_price.return_value = 0
        mock_price_cleaner.is_valid_price.return_value = False
        
        parser = DepoHtmlParser(price_cleaner=mock_price_cleaner)
        
        html_content = """
        <li class="item product product-item">
          <div>Rp invalid1</div>
          <div>Rp invalid2</div>
          <span>Rp invalid3</span>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = parser._extract_price_from_text_search(item)
        self.assertEqual(result, 0)
    
    def test_extract_product_price_fallback_to_text_search(self):
        from bs4 import BeautifulSoup
        
        # HTML with no structured price but contains Rp text
        html_content = """
        <li class="item product product-item">
          <div class="product-info">
            <p>Price: Rp 15.000</p>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_product_price(item)
        self.assertEqual(result, 15000)  # Should extract from text search
    
    def test_extract_product_price_all_methods_return_zero(self):
        from bs4 import BeautifulSoup
        
        # Create a mock price cleaner that makes text search return 0
        mock_price_cleaner = Mock(spec=DepoPriceCleaner)
        mock_price_cleaner.clean_price.return_value = 0
        mock_price_cleaner.is_valid_price.return_value = False
        
        parser = DepoHtmlParser(price_cleaner=mock_price_cleaner)
        
        # HTML with unstructured price text that will be cleaned to 0
        html_content = """
        <li class="item product product-item">
          <div class="product-info">
            <p>Rp invalid</p>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        # This should trigger line 137 (price > 0 is False) and line 209 (return 0 from text search)
        result = parser._extract_product_price(item)
        self.assertEqual(result, 0)
    
    def test_extract_product_price_regular_price_returns_zero(self):
        from bs4 import BeautifulSoup
        
        # HTML that has no structured price but has text with "Rp"
        html_content = """
        <li class="item product product-item">
          <div class="product-info">
            <span>Harga: Rp 25.000</span>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        

        result = self.parser._extract_product_price(item)
        self.assertEqual(result, 25000)
    
    def test_extract_product_price_regular_price_succeeds(self):
        """Test the exact scenario where line 137 executes - regular price > 0 returns price"""
        from bs4 import BeautifulSoup
        
        # HTML with structured regular price that should succeed
        html_content = """
        <li class="item product product-item">
          <div class="price-box price-final_price">
            <span class="price-wrapper" data-price-type="finalPrice">
              <span class="price">Rp 75.000</span>
            </span>
          </div>
        </li>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('li')
        
        result = self.parser._extract_product_price(item)
        self.assertEqual(result, 75000)


if __name__ == '__main__':
    unittest.main()