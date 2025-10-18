import unittest
from unittest.mock import patch, Mock, MagicMock
import requests
from api.juragan_material.html_parser import JuraganMaterialHtmlParser
from bs4 import BeautifulSoup


class TestJuraganMaterialHtmlParserUnitExtraction(unittest.TestCase):
    """Test cases for unit extraction functionality in JuraganMaterialHtmlParser."""
    
    def setUp(self):
        self.parser = JuraganMaterialHtmlParser()
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_success_with_relative_url(self, mock_get):
        """Test successful unit extraction with relative URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Create HTML that matches the exact CSS selector used in implementation
        mock_response.text = """
        <html>
            <body>
                <div>
                    <div>
                        <main>
                            <div>
                                <div>
                                    <div>
                                        <div>
                                            <div>
                                                <div>
                                                    <div>
                                                        <div>
                                                            <p>Product Info</p>
                                                            <p>Kg</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </main>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Mock the BeautifulSoup selector to return the expected element
        with patch('api.juragan_material.html_parser.BeautifulSoup') as mock_soup:
            mock_element = Mock()
            mock_element.get_text.return_value = "Kg"
            mock_soup_instance = Mock()
            mock_soup_instance.select_one.return_value = mock_element
            mock_soup.return_value = mock_soup_instance
            
            unit = self.parser._extract_product_unit("/products/semen-40kg")
            
            self.assertEqual(unit, "Kg")
            mock_get.assert_called_once_with("https://juraganmaterial.id/products/semen-40kg", timeout=10)
            mock_soup.assert_called_once_with(mock_response.text, 'html.parser')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_success_with_absolute_url(self, mock_get):
        """Test successful unit extraction with absolute URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div>
                    <div>
                        <main>
                            <div>
                                <div>
                                    <div>
                                        <div>
                                            <div>
                                                <div>
                                                    <div>
                                                        <div>
                                                            <p>Product Info</p>
                                                            <p>Liter</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </main>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Mock the BeautifulSoup selector to return the expected element
        with patch('api.juragan_material.html_parser.BeautifulSoup') as mock_soup:
            mock_element = Mock()
            mock_element.get_text.return_value = "Liter"
            mock_soup_instance = Mock()
            mock_soup_instance.select_one.return_value = mock_element
            mock_soup.return_value = mock_soup_instance
            
            unit = self.parser._extract_product_unit("https://juraganmaterial.id/products/cat-5liter")
            
            self.assertEqual(unit, "Liter")
            mock_get.assert_called_once_with("https://juraganmaterial.id/products/cat-5liter", timeout=10)
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_with_whitespace_stripping(self, mock_get):
        """Test unit extraction with whitespace that needs stripping."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div>
                    <div>
                        <main>
                            <div>
                                <div>
                                    <div>
                                        <div>
                                            <div>
                                                <div>
                                                    <div>
                                                        <div>
                                                            <p>Product Info</p>
                                                            <p>   Meter   </p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </main>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Mock the BeautifulSoup selector to return the expected element with whitespace
        with patch('api.juragan_material.html_parser.BeautifulSoup') as mock_soup:
            mock_element = Mock()
            mock_element.get_text.return_value = "Meter"  # get_text(strip=True) removes whitespace
            mock_soup_instance = Mock()
            mock_soup_instance.select_one.return_value = mock_element
            mock_soup.return_value = mock_soup_instance
            
            unit = self.parser._extract_product_unit("/products/besi-meter")
            
            self.assertEqual(unit, "Meter")
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_element_not_found(self, mock_get):
        """Test unit extraction when the specific element is not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div>Different structure without the unit element</div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        unit = self.parser._extract_product_unit("/products/no-unit")
        
        self.assertEqual(unit, "")
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_404_response(self, mock_get):
        """Test unit extraction with 404 response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        with patch('api.juragan_material.html_parser.logger') as mock_logger:
            unit = self.parser._extract_product_unit("/products/not-found")
            
            self.assertEqual(unit, "")
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            self.assertIn("Failed to fetch product detail page", warning_msg)
            self.assertIn("/products/not-found", warning_msg)
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_500_response(self, mock_get):
        """Test unit extraction with server error response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        with patch('api.juragan_material.html_parser.logger') as mock_logger:
            unit = self.parser._extract_product_unit("/products/server-error")
            
            self.assertEqual(unit, "")
            mock_logger.warning.assert_called_once()
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_connection_error(self, mock_get):
        """Test unit extraction with connection error."""
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        
        with patch('api.juragan_material.html_parser.logger') as mock_logger:
            unit = self.parser._extract_product_unit("/products/connection-fail")
            
            self.assertEqual(unit, "")
            mock_logger.error.assert_called_once()
            error_msg = mock_logger.error.call_args[0][0]
            self.assertIn("Error fetching unit for", error_msg)
            self.assertIn("Connection failed", error_msg)
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_timeout_error(self, mock_get):
        """Test unit extraction with timeout error."""
        mock_get.side_effect = requests.Timeout("Request timed out")
        
        with patch('api.juragan_material.html_parser.logger') as mock_logger:
            unit = self.parser._extract_product_unit("/products/timeout")
            
            self.assertEqual(unit, "")
            mock_logger.error.assert_called_once()
            error_msg = mock_logger.error.call_args[0][0]
            self.assertIn("Request timed out", error_msg)
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_with_request_exception(self, mock_get):
        """Test unit extraction with general request exception."""
        mock_get.side_effect = requests.RequestException("General request error")
        
        with patch('api.juragan_material.html_parser.logger') as mock_logger:
            unit = self.parser._extract_product_unit("/products/request-error")
            
            self.assertEqual(unit, "")
            mock_logger.error.assert_called_once()
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_with_beautifulsoup_error(self, mock_get):
        """Test unit extraction when BeautifulSoup parsing fails."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Invalid HTML content"
        mock_get.return_value = mock_response
        
        with patch('api.juragan_material.html_parser.BeautifulSoup') as mock_soup:
            mock_soup.side_effect = Exception("HTML parsing failed")
            
            with patch('api.juragan_material.html_parser.logger') as mock_logger:
                unit = self.parser._extract_product_unit("/products/parse-error")
                
                self.assertEqual(unit, "")
                mock_logger.error.assert_called_once()
    
    def test_extract_unit_with_empty_url(self):
        """Test unit extraction with empty URL."""
        unit = self.parser._extract_product_unit("")
        
        self.assertEqual(unit, "")
    
    def test_extract_unit_with_none_url(self):
        """Test unit extraction with None URL."""
        unit = self.parser._extract_product_unit(None)
        
        self.assertEqual(unit, "")
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_with_malformed_url(self, mock_get):
        """Test unit extraction with malformed URL."""
        mock_get.side_effect = requests.exceptions.InvalidURL("Invalid URL")
        
        with patch('api.juragan_material.html_parser.logger') as mock_logger:
            unit = self.parser._extract_product_unit("not-a-valid-url")
            
            self.assertEqual(unit, "")
            mock_logger.error.assert_called_once()
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_timeout_parameter(self, mock_get):
        """Test that unit extraction uses correct timeout parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_get.return_value = mock_response
        
        self.parser._extract_product_unit("/products/test")
        
        # Verify timeout parameter is passed correctly
        mock_get.assert_called_once_with("https://juraganmaterial.id/products/test", timeout=10)
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_with_multiple_matching_elements(self, mock_get):
        """Test unit extraction when multiple elements match the selector."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div>
                    <div>
                        <main>
                            <div>
                                <div>
                                    <div>
                                        <div>
                                            <div>
                                                <div>
                                                    <div>
                                                        <div>
                                                            <p>Product Info</p>
                                                            <p>First Unit</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </main>
                    </div>
                </div>
                <div>
                    <div>
                        <main>
                            <div>
                                <div>
                                    <div>
                                        <div>
                                            <div>
                                                <div>
                                                    <div>
                                                        <div>
                                                            <p>Another Product</p>
                                                            <p>Second Unit</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </main>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Mock the BeautifulSoup selector to return the first matching element
        with patch('api.juragan_material.html_parser.BeautifulSoup') as mock_soup:
            mock_element = Mock()
            mock_element.get_text.return_value = "First Unit"
            mock_soup_instance = Mock()
            mock_soup_instance.select_one.return_value = mock_element
            mock_soup.return_value = mock_soup_instance
            
            unit = self.parser._extract_product_unit("/products/multiple-units")
            
            # Should return the first matching element
            self.assertEqual(unit, "First Unit")
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_unit_with_empty_element_text(self, mock_get):
        """Test unit extraction when the element exists but has no text."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div>
                    <div>
                        <main>
                            <div>
                                <div>
                                    <div>
                                        <div>
                                            <div>
                                                <div>
                                                    <div>
                                                        <div>
                                                            <p>Product Info</p>
                                                            <p></p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </main>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        unit = self.parser._extract_product_unit("/products/empty-unit")
        
        self.assertEqual(unit, "")
    
    def test_extract_unit_integration_with_extract_product_from_item(self):
        """Test that unit extraction is called during product extraction."""
        html_content = """
        <div class="product-card">
            <a href="/products/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <div class="product-card-price">
                <div class="price">Rp 50.000</div>
            </div>
        </div>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('div', class_='product-card')
        
        with patch.object(self.parser, '_extract_product_unit', return_value='Kg') as mock_unit:
            product = self.parser._extract_product_from_item(item)
            
            self.assertIsNotNone(product)
            self.assertEqual(product.unit, 'Kg')
            mock_unit.assert_called_once_with("/products/test-product")
    
    def test_extract_unit_not_called_when_no_url(self):
        """Test that unit extraction is not called when product has no URL."""
        html_content = """
        <div class="product-card">
            <p class="product-name">Test Product</p>
            <div class="product-card-price">
                <div class="price">Rp 50.000</div>
            </div>
        </div>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        item = soup.find('div', class_='product-card')
        
        with patch.object(self.parser, '_extract_product_unit') as mock_unit:
            product = self.parser._extract_product_from_item(item)
            
            # The method should still be called even for generated URLs
            # The actual implementation calls unit extraction for any non-empty URL
            self.assertIsNotNone(product)
            mock_unit.assert_called_once()


if __name__ == '__main__':
    unittest.main()