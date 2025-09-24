from django.test import TestCase
from unittest.mock import patch, MagicMock
from api.core import BaseHttpClient
from api.interfaces import HttpClientError
import requests


class TestMitra10HttpClient(TestCase):    
    def setUp(self):
        self.base_url = "https://www.mitra10.com"
        self.search_url = f"{self.base_url}/catalogsearch/result/?q=semen"
        self.sample_mitra10_html = """
        <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12 MuiGrid-grid-md-6">
            <div class="product-item">
                <h3>Semen Portland</h3>
                <div class="price">Rp 55.000</div>
            </div>
        </div>
        """
    
    def test_mitra10_successful_request(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.content = self.sample_mitra10_html.encode('utf-8')
            mock_response.encoding = 'utf-8'
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            result = client.get(self.search_url)
            
            self.assertEqual(result, self.sample_mitra10_html)
            mock_session.get.assert_called()
    
    def test_mitra10_request_with_timeout(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.Timeout("Request timed out")
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            
            with self.assertRaises(HttpClientError) as context:
                client.get(self.search_url)
            
            self.assertIn("timeout", str(context.exception).lower())
    
    def test_mitra10_connection_error(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("Failed to connect")
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            
            with self.assertRaises(HttpClientError) as context:
                client.get(self.search_url)
            
            self.assertIn("connection", str(context.exception).lower())
    
    def test_mitra10_http_error_404(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            
            http_error = requests.exceptions.HTTPError("404 Client Error")
            http_error.response = MagicMock()
            http_error.response.status_code = 404
            
            mock_response.raise_for_status.side_effect = http_error
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            
            with self.assertRaises(HttpClientError) as context:
                client.get(self.search_url)
            
            self.assertIn("404", str(context.exception))
    
    def test_mitra10_http_error_500(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            
            http_error = requests.exceptions.HTTPError("500 Server Error")
            http_error.response = MagicMock()
            http_error.response.status_code = 500
            
            mock_response.raise_for_status.side_effect = http_error
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            
            with self.assertRaises(HttpClientError) as context:
                client.get(self.search_url)
            
            self.assertIn("500", str(context.exception))
    
    def test_mitra10_empty_response(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.content = b""  
            mock_response.encoding = 'utf-8'
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            
            with self.assertRaises(HttpClientError) as context:
                client.get(self.search_url)
            
            self.assertIn("empty", str(context.exception).lower())
    
    def test_mitra10_retry_mechanism(self):
        with patch('requests.Session') as mock_session_class, patch('time.sleep'):
            
            mock_session = MagicMock()
            mock_response_success = MagicMock()
            mock_response_success.raise_for_status.return_value = None
            mock_response_success.content = self.sample_mitra10_html.encode('utf-8')
            mock_response_success.encoding = 'utf-8'
            
            mock_session.get.side_effect = [
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.ConnectionError("Connection failed"),
                mock_response_success
            ]
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient(max_retries=3)
            result = client.get(self.search_url)
            
            self.assertEqual(result, self.sample_mitra10_html)
            self.assertEqual(mock_session.get.call_count, 3)
    
    def test_mitra10_max_retries_exceeded(self):
        with patch('requests.Session') as mock_session_class, patch('time.sleep'):  
            
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient(max_retries=2)
            
            with self.assertRaises(HttpClientError) as context:
                client.get(self.search_url)
            
            self.assertEqual(mock_session.get.call_count, 2)  # max_retries attempts
            self.assertIn("connection", str(context.exception).lower())
    
    def test_mitra10_headers_configuration(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.content = self.sample_mitra10_html.encode('utf-8')
            mock_response.encoding = 'utf-8'
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            result = client.get(self.search_url)
            
            self.assertIsNotNone(client.session.headers.get('User-Agent'))
    
    def test_mitra10_request_exception_handling(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.RequestException("Generic request error")
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            
            with self.assertRaises(HttpClientError) as context:
                client.get(self.search_url)
            
            self.assertIn("request", str(context.exception).lower())
    
    def test_mitra10_unexpected_exception(self):
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.side_effect = ValueError("Unexpected error")
            mock_session_class.return_value = mock_session
            
            client = BaseHttpClient()
            
            with self.assertRaises(HttpClientError) as context:
                client.get(self.search_url)
            
            self.assertIn("unexpected", str(context.exception).lower())
    
    def test_mitra10_url_construction_patterns(self):
        test_patterns = [
            ("semen", "https://www.mitra10.com/catalogsearch/result/?q=semen"),
            ("cat besi", "https://www.mitra10.com/catalogsearch/result/?q=cat+besi"),
            ("keramik lantai", "https://www.mitra10.com/catalogsearch/result/?q=keramik+lantai"),
        ]
        
        for query, expected_url in test_patterns:
            constructed_url = f"https://www.mitra10.com/catalogsearch/result/?q={query.replace(' ', '+')}"
            self.assertEqual(constructed_url, expected_url)

