from unittest import TestCase
from unittest.mock import Mock, patch
from api.interfaces import HttpClientError
from api.core import BaseHttpClient


class TestJuraganMaterialHttpClient(TestCase):
    """Test cases for HTTP client functionality in Juragan Material scraper."""

    @patch('api.core.requests.Session')
    def test_successful_request(self, mock_session_class):
        """Test successful HTTP GET request."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.content = b"<html>juragan material content</html>"
        mock_response.encoding = "utf-8"
        mock_response.raise_for_status.return_value = None  # No HTTP errors
        mock_session.get.return_value = mock_response

        client = BaseHttpClient()
        result = client.get("https://juraganmaterial.id/produk?keyword=semen")

        self.assertEqual(result, "<html>juragan material content</html>")
        mock_session.get.assert_called_once()

    @patch('api.core.requests.Session')
    def test_request_timeout(self, mock_session_class):
        """Test HTTP request timeout handling."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = Exception("Request timeout")

        client = BaseHttpClient()
        
        with self.assertRaises(HttpClientError) as context:
            client.get("https://juraganmaterial.id/produk?keyword=semen")
        
        self.assertIn("Request timeout", str(context.exception))

    @patch('api.core.requests.Session')
    def test_request_with_juragan_material_url(self, mock_session_class):
        """Test HTTP request with specific Juragan Material URL structure."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.content = b"<html>juragan material search results</html>"
        mock_response.encoding = "utf-8"
        mock_response.raise_for_status.return_value = None  # No HTTP errors
        mock_session.get.return_value = mock_response

        client = BaseHttpClient()
        result = client.get("https://juraganmaterial.id/produk?keyword=besi&page=2&sort=lowest_price")

        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        self.assertEqual(call_args[0][0], "https://juraganmaterial.id/produk?keyword=besi&page=2&sort=lowest_price")
        self.assertEqual(result, "<html>juragan material search results</html>")

    @patch('api.core.requests.Session')
    def test_request_handles_encoding(self, mock_session_class):
        """Test HTTP request properly handles different text encoding."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.content = "juragan material content with special chars: ÂÃÄ".encode('utf-8')
        mock_response.encoding = "utf-8"
        mock_response.raise_for_status.return_value = None  # No HTTP errors
        mock_session.get.return_value = mock_response

        client = BaseHttpClient()
        result = client.get("https://juraganmaterial.id/produk")

        self.assertEqual(result, "juragan material content with special chars: ÂÃÄ")

    @patch('api.core.requests.Session')
    def test_request_with_connection_error(self, mock_session_class):
        """Test HTTP request with connection error."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = ConnectionError("Unable to connect to juraganmaterial.id")

        client = BaseHttpClient()
        
        with self.assertRaises(HttpClientError) as context:
            client.get("https://juraganmaterial.id/produk")
        
        self.assertIn("Unable to connect to juraganmaterial.id", str(context.exception))

    @patch('api.core.requests.Session')
    def test_request_with_http_error_response(self, mock_session_class):
        """Test HTTP request with server error response."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Simulate HTTP error like 404 or 500
        http_error = Exception("404 Client Error: Not Found")
        mock_session.get.side_effect = http_error

        client = BaseHttpClient()
        
        with self.assertRaises(HttpClientError) as context:
            client.get("https://juraganmaterial.id/nonexistent-page")
        
        self.assertIn("404 Client Error", str(context.exception))

    @patch('api.core.requests.Session')
    def test_request_with_empty_response(self, mock_session_class):
        """Test HTTP request with empty response content raises error."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.content = b""
        mock_response.encoding = "utf-8"
        mock_response.raise_for_status.return_value = None  # No HTTP errors
        mock_session.get.return_value = mock_response

        client = BaseHttpClient()
        
        with self.assertRaises(HttpClientError) as context:
            client.get("https://juraganmaterial.id/produk")
        
        self.assertIn("Empty response from", str(context.exception))
        # Should retry, so get() is called multiple times
        self.assertGreater(mock_session.get.call_count, 1)

    @patch('api.core.requests.Session')
    def test_request_with_large_response(self, mock_session_class):
        """Test HTTP request with large response content."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        # Simulate large HTML content
        large_content = "<html>" + "x" * 10000 + "</html>"
        mock_response.content = large_content.encode('utf-8')
        mock_response.encoding = "utf-8"
        mock_response.raise_for_status.return_value = None  # No HTTP errors
        mock_session.get.return_value = mock_response

        client = BaseHttpClient()
        result = client.get("https://juraganmaterial.id/produk")

        self.assertEqual(len(result), 10013)  # <html> + 10000 x's + </html>
        self.assertTrue(result.startswith("<html>"))
        self.assertTrue(result.endswith("</html>"))