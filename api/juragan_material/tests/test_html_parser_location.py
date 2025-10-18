import unittest
from unittest.mock import patch, Mock
import requests
from api.juragan_material.html_parser import JuraganMaterialHtmlParser
from api.interfaces import HtmlParserError


class TestJuraganMaterialLocationScraping(unittest.TestCase):
    """Test cases for location extraction from Juragan Material product detail pages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = JuraganMaterialHtmlParser()
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_valid_url(self, mock_get):
        """Test location extraction with valid URL and location element present."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>Jakarta Selatan, DKI Jakarta</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, 'Jakarta Selatan, DKI Jakarta')
        mock_get.assert_called_once_with('https://juraganmaterial.id/products/test-product', timeout=10)
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_full_url(self, mock_get):
        """Test location extraction with full URL (not relative path)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>Bandung, Jawa Barat</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('https://juraganmaterial.id/products/test-product')
        
        self.assertEqual(location, 'Bandung, Jawa Barat')
        mock_get.assert_called_once_with('https://juraganmaterial.id/products/test-product', timeout=10)
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_element_not_found(self, mock_get):
        """Test location extraction when location element is not found in HTML."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div>No location information</div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_empty_element(self, mock_get):
        """Test location extraction when location element exists but is empty."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span></span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_whitespace_only(self, mock_get):
        """Test location extraction when location element contains only whitespace."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>   \n\t  </span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_extra_whitespace(self, mock_get):
        """Test location extraction strips extra whitespace from location text."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>  Surabaya, Jawa Timur  </span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, 'Surabaya, Jawa Timur')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_http_404(self, mock_get):
        """Test location extraction when product detail page returns 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/non-existent')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_http_500(self, mock_get):
        """Test location extraction when product detail page returns 500."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/error-product')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_request_timeout(self, mock_get):
        """Test location extraction when request times out."""
        mock_get.side_effect = requests.Timeout('Request timed out')
        
        location = self.parser._extract_product_location_xpath('/products/slow-product')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_connection_error(self, mock_get):
        """Test location extraction when connection error occurs."""
        mock_get.side_effect = requests.ConnectionError('Connection failed')
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_invalid_html(self, mock_get):
        """Test location extraction with malformed HTML."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><div>Malformed HTML without closing tags'
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        # Should not crash, just return empty string
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_special_characters(self, mock_get):
        """Test location extraction with special characters in location."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>Yogyakarta, D.I. Yogyakarta (Jogja)</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, 'Yogyakarta, D.I. Yogyakarta (Jogja)')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_unicode_characters(self, mock_get):
        """Test location extraction with unicode characters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>Bali, Indonesia 🏝️</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, 'Bali, Indonesia 🏝️')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_nested_elements(self, mock_get):
        """Test location extraction when location has nested HTML elements."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span><strong>Jakarta</strong>, <em>DKI Jakarta</em></span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        # get_text(strip=True) should handle nested elements (space between tags is removed)
        self.assertEqual(location, 'Jakarta,DKI Jakarta')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_empty_url(self, mock_get):
        """Test location extraction with empty URL."""
        location = self.parser._extract_product_location_xpath('')
        
        # Should handle gracefully
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_multiple_matching_elements(self, mock_get):
        """Test location extraction when multiple elements match the selector."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>First</span>
                    <span>Jakarta Pusat, DKI Jakarta</span>
                    <span>Extra span</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        # select_one should return the first matching element (second span in this case)
        self.assertEqual(location, 'Jakarta Pusat, DKI Jakarta')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_long_text(self, mock_get):
        """Test location extraction with very long location text."""
        long_location = 'Jl. Raya Very Long Street Name Number 123, RT 001/RW 002, Kelurahan Test, Kecamatan Test District, Jakarta Selatan, DKI Jakarta, 12345, Indonesia'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = f'''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>{long_location}</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, long_location)
    
    @patch('api.juragan_material.html_parser.requests.get')
    @patch('api.juragan_material.html_parser.logger')
    def test_extract_location_logs_warning_on_404(self, mock_logger, mock_get):
        """Test that warning is logged when product detail page returns 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        self.parser._extract_product_location_xpath('/products/non-existent')
        
        mock_logger.warning.assert_called_once()
    
    @patch('api.juragan_material.html_parser.requests.get')
    @patch('api.juragan_material.html_parser.logger')
    def test_extract_location_logs_error_on_exception(self, mock_logger, mock_get):
        """Test that error is logged when exception occurs."""
        mock_get.side_effect = Exception('Unexpected error')
        
        self.parser._extract_product_location_xpath('/products/test-product')
        
        mock_logger.error.assert_called_once()
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_numeric_characters(self, mock_get):
        """Test location extraction with numeric characters in location."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>Jakarta Barat 11480, DKI Jakarta</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, 'Jakarta Barat 11480, DKI Jakarta')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_request_exception_generic(self, mock_get):
        """Test location extraction when generic request exception occurs."""
        mock_get.side_effect = requests.RequestException('Generic request error')
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_ampersand(self, mock_get):
        """Test location extraction with ampersand in location."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>Tangerang & Sekitarnya, Banten</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, 'Tangerang & Sekitarnya, Banten')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_none_response(self, mock_get):
        """Test location extraction when response is None."""
        mock_get.return_value = None
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        # Should handle None response gracefully
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_empty_response_text(self, mock_get):
        """Test location extraction when response text is empty."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_with_line_breaks(self, mock_get):
        """Test location extraction with line breaks in location text."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div id="footer-address-link">
                    <span>Address:</span>
                    <span>Semarang
                    Jawa Tengah</span>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/test-product')
        
        # strip=True only strips leading/trailing whitespace, not internal newlines
        # The actual behavior preserves the internal newline and spaces
        self.assertIn('Semarang', location)
        self.assertIn('Jawa Tengah', location)
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_http_redirect_3xx(self, mock_get):
        """Test location extraction when product detail page returns redirect status."""
        mock_response = Mock()
        mock_response.status_code = 301
        mock_get.return_value = mock_response
        
        location = self.parser._extract_product_location_xpath('/products/redirected')
        
        self.assertEqual(location, '')
    
    @patch('api.juragan_material.html_parser.requests.get')
    def test_extract_location_verify_timeout_parameter(self, mock_get):
        """Test that timeout parameter is correctly passed to requests.get."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><div id="footer-address-link"><span>Test</span></div></body></html>'
        mock_get.return_value = mock_response
        
        self.parser._extract_product_location_xpath('/products/test-product')
        
        # Verify that timeout=10 is passed
        mock_get.assert_called_with('https://juraganmaterial.id/products/test-product', timeout=10)


if __name__ == '__main__':
    unittest.main()
