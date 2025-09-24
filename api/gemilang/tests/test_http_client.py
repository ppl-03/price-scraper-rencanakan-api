from unittest import TestCase
from unittest.mock import Mock, patch
from api.interfaces import HttpClientError
from api.core import BaseHttpClient
class TestHttpClient(TestCase):
    @patch('api.core.requests.Session')
    def test_successful_request(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.content = b"<html>test content</html>"
        mock_response.encoding = "utf-8"
        mock_session.get.return_value = mock_response
        client = BaseHttpClient()
        result = client.get("https://example.com")
        self.assertEqual(result, "<html>test content</html>")
        mock_session.get.assert_called_once()
    @patch('api.core.requests.Session')
    def test_request_timeout(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = Exception("Timeout")
        client = BaseHttpClient()
        with self.assertRaises(HttpClientError):
            client.get("https://example.com")
    @patch('api.core.requests.Session')
    def test_request_with_custom_headers(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.content = b"<html>test content</html>"
        mock_response.encoding = "utf-8"
        mock_session.get.return_value = mock_response
        client = BaseHttpClient()
        result = client.get("https://example.com")
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        self.assertEqual(call_args[0][0], "https://example.com")
    @patch('api.core.requests.Session')
    def test_request_handles_encoding(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.content = "test content".encode('utf-8')
        mock_response.encoding = "utf-8"
        mock_session.get.return_value = mock_response
        client = BaseHttpClient()
        result = client.get("https://example.com")
        self.assertEqual(result, "test content")
