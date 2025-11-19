from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from dashboard import views


class TriggerScrapeIntegrationTests(TestCase):
    """Integration tests for the trigger_scrape view"""

    def setUp(self):
        self.client = Client()

    @patch('dashboard.views._run_vendor_to_count')
    def test_trigger_scrape_all_vendors(self, mock_run_vendor):
        # Mock vendor counts
        mock_run_vendor.return_value = 5
        
        response = self.client.post('/scrape/gemilang/', {'q': 'cement'})
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        # Should have called vendor runner for each vendor
        self.assertGreater(mock_run_vendor.call_count, 0)


class ExceptionPathTests(TestCase):
    """Tests for exception handling paths"""

    @patch('api.gemilang.database_service.GemilangDatabaseService')
    def test_save_products_database_exception(self, mock_service_class):
        # Mock database service to raise exception
        mock_service = MagicMock()
        mock_service.save_with_price_update.side_effect = Exception('Database error')
        mock_service_class.return_value = mock_service
        
        products = [
            {'name': 'Product', 'price': 100000, 'unit': 'pcs', 'location': 'Jakarta'}
        ]
        
        # Should not raise exception, should handle it gracefully
        try:
            views._save_products_to_database(products, 'gemilang')
        except Exception:
            self.fail("_save_products_to_database should handle exceptions gracefully")

    @patch('dashboard.views.BaseHttpClient')
    def test_fallback_network_error(self, mock_client_class):
        # Mock network error
        mock_client = MagicMock()
        mock_client.get_html.side_effect = ConnectionError('Network error')
        mock_client_class.return_value = mock_client
        
        rows, _, html_len = views._juragan_fallback('test')
        
        # Should return empty result, not raise exception
        self.assertEqual(rows, [])
        self.assertEqual(html_len, 0)

    def test_currency_extraction_with_none(self):
        from bs4 import BeautifulSoup
        
        html = '<div></div>'
        soup = BeautifulSoup(html, 'html.parser')
        node = soup.find('div')
        
        # Should handle None/empty gracefully
        result = views._try_currency_text_price(node)
        self.assertEqual(result, 0)

    def test_process_jsonld_with_malformed_json(self):
        script = MagicMock()
        script.string = '{invalid json'
        
        result = views._process_jsonld_script(script, 'https://test.com')
        
        # Should return None, not raise exception
        self.assertIsNone(result)

    def test_save_products_empty_list(self):
        # Empty product list should be handled
        products = []
        
        try:
            views._save_products_to_database(products, 'gemilang')
        except Exception:
            self.fail("Should handle empty product list")


class UrlConstructionTests(TestCase):
    """Tests for URL construction functions"""

    def test_try_simple_mitra10_url(self):
        # This function returns a tuple (rows, url, html_len)
        result = views._try_simple_mitra10_url('cement')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    @patch('dashboard.views._fetch_with_playwright')
    def test_try_playwright_mitra10_success(self, mock_fetch):
        mock_fetch.return_value = '<html>Product page</html>'
        
        result = views._try_playwright_mitra10('cement', 'https://fallback.com')
        
        # Returns tuple (rows, url, html_len)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    @patch('dashboard.views._fetch_with_playwright')
    def test_try_playwright_mitra10_failure(self, mock_fetch):
        mock_fetch.return_value = None
        
        result = views._try_playwright_mitra10('cement', 'https://fallback.com')
        
        # Should return fallback result
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    def test_try_complex_mitra10_url(self):
        result = views._try_complex_mitra10_url('cement', True, 1, 'https://fallback.com')
        
        # Returns tuple (rows, url, html_len)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)


class AdditionalParsingTests(TestCase):
    """Additional parsing tests for edge cases"""

    def test_try_specific_mitra10_containers(self):
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
        <body>
            <div class="product-grid">
                <div class="product-card">Product 1</div>
                <div class="product-card">Product 2</div>
            </div>
        </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        containers = views._try_specific_mitra10_containers(soup)
        self.assertIsInstance(containers, list)

    def test_try_generic_mitra10_containers(self):
        from bs4 import BeautifulSoup
        
        html = '<html><body><div class="item">Product</div></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        containers = views._try_generic_mitra10_containers(soup)
        self.assertIsInstance(containers, list)

    def test_try_specific_price_classes(self):
        from bs4 import BeautifulSoup
        
        html = '<div class="product-price">Rp 100.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        node = soup.find('div')
        
        price = views._try_specific_price_classes(node)
        self.assertIsInstance(price, int)

    def test_try_generic_price_classes(self):
        from bs4 import BeautifulSoup
        
        html = '<div class="price">Rp 150.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        node = soup.find('div')
        
        price = views._try_generic_price_classes(node)
        self.assertIsInstance(price, int)

    def test_try_data_attributes_price(self):
        from bs4 import BeautifulSoup
        
        html = '<div data-price="200000"></div>'
        soup = BeautifulSoup(html, 'html.parser')
        node = soup.find('div')
        
        price = views._try_data_attributes_price(node)
        self.assertIsInstance(price, int)
