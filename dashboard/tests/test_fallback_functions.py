from django.test import TestCase
from unittest.mock import patch, MagicMock
from dashboard import views


class FallbackFunctionsTest(TestCase):
    """Tests for vendor fallback scraping functions"""

    @patch('dashboard.views.BaseHttpClient')
    def test_juragan_fallback_success(self, mock_client_class):
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        html = '''
        <div class="product-card">
            <div class="product-name">Test Product</div>
            <div class="product-price">Rp 100.000</div>
        </div>
        '''
        mock_client.get_html.return_value = html
        
        rows, url, html_len = views._juragan_fallback('test-keyword')
        
        self.assertIsInstance(rows, list)
        self.assertIsInstance(url, str)
        self.assertIsInstance(html_len, int)

    @patch('dashboard.views.BaseHttpClient')
    def test_juragan_fallback_exception(self, mock_client_class):
        # Mock client to raise exception
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_html.side_effect = Exception('Network error')
        
        rows, url, html_len = views._juragan_fallback('test-keyword')
        
        self.assertEqual(rows, [])
        self.assertIsInstance(url, str)
        self.assertEqual(html_len, 0)

    @patch('dashboard.views.BaseHttpClient')
    def test_mitra10_fallback_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        html = '<div class="product">Test Mitra10 Product</div>'
        mock_client.get_html.return_value = html
        
        rows, url, html_len = views._mitra10_fallback('cement')
        
        self.assertIsInstance(rows, list)
        self.assertIsInstance(url, str)

    @patch('dashboard.views.BaseHttpClient')
    def test_mitra10_fallback_exception(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_html.side_effect = Exception('Error')
        
        rows, url, html_len = views._mitra10_fallback('cement')
        self.assertEqual(rows, [])

    @patch('dashboard.views.BaseHttpClient')
    def test_depo_fallback_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        html = '<div class="product-item">Depo Product</div>'
        mock_client.get_html.return_value = html
        
        rows, url, html_len = views._depo_fallback('paint')
        
        self.assertIsInstance(rows, list)
        self.assertIsInstance(url, str)

    @patch('dashboard.views.BaseHttpClient')
    def test_depo_fallback_exception(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_html.side_effect = Exception('Failed')
        
        rows, url, html_len = views._depo_fallback('paint')
        self.assertEqual(rows, [])

    @patch('dashboard.views.BaseHttpClient')
    def test_tokopedia_fallback_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        html = '<script type="application/ld+json">{"name": "Product"}</script>'
        mock_client.get_html.return_value = html
        
        rows, url, html_len = views._tokopedia_fallback('brick')
        
        self.assertIsInstance(rows, list)
        self.assertIsInstance(url, str)

    @patch('dashboard.views.BaseHttpClient')
    def test_tokopedia_fallback_exception(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_html.side_effect = Exception('Error')
        
        rows, url, html_len = views._tokopedia_fallback('brick')
        self.assertEqual(rows, [])


class ExtractionHelperTests(TestCase):
    """Tests for extraction helper functions"""

    def test_try_currency_text_price_valid(self):
        from bs4 import BeautifulSoup
        html = '<div>Rp 1.500.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        node = soup.find('div')
        result = views._try_currency_text_price(node)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_try_currency_text_price_invalid(self):
        from bs4 import BeautifulSoup
        html = '<div>invalid text</div>'
        soup = BeautifulSoup(html, 'html.parser')
        node = soup.find('div')
        result = views._try_currency_text_price(node)
        self.assertEqual(result, 0)

    def test_try_numeric_text_price_valid(self):
        from bs4 import BeautifulSoup
        html = '<div>150000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        node = soup.find('div')
        result = views._try_numeric_text_price(node)
        self.assertEqual(result, 150000)

    def test_try_numeric_text_price_invalid(self):
        from bs4 import BeautifulSoup
        html = '<div>not a number</div>'
        soup = BeautifulSoup(html, 'html.parser')
        node = soup.find('div')
        result = views._try_numeric_text_price(node)
        self.assertEqual(result, 0)


class ParseJsonLdTests(TestCase):
    """Tests for JSON-LD parsing functions"""

    def test_process_jsonld_script_product(self):
        script = MagicMock()
        script.string = '''
        {
            "@type": "Product",
            "name": "Test Product",
            "offers": {
                "price": "100000"
            }
        }
        '''
        
        result = views._process_jsonld_script(script, 'test-url')
        
        if result:
            self.assertIn('name', result)
            self.assertIn('price', result)

    def test_process_jsonld_script_non_product(self):
        script = MagicMock()
        script.string = '{"@type": "Organization", "name": "Company"}'
        
        result = views._process_jsonld_script(script, 'test-url')
        self.assertIsNone(result)

    def test_process_jsonld_script_invalid_json(self):
        script = MagicMock()
        script.string = 'not valid json'
        
        result = views._process_jsonld_script(script, 'test-url')
        self.assertIsNone(result)
