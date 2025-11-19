from django.test import TestCase
from unittest.mock import patch, MagicMock, Mock
from dashboard import views
from bs4 import BeautifulSoup


class PriceExtractionStrategiesTest(TestCase):
    """Test various price extraction strategies"""

    def test_try_primary_juragan_price(self):
        html = '<div class="primary-price" data-price="100000">Rp 100.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        price = views._try_primary_juragan_price(card)
        self.assertIsInstance(price, int)

    def test_try_secondary_juragan_price(self):
        html = '<div class="secondary-price">Rp 150.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        price = views._try_secondary_juragan_price(card)
        self.assertIsInstance(price, int)

    def test_try_currency_text_juragan_price(self):
        html = '<div>Rp 200.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        price = views._try_currency_text_juragan_price(card)
        self.assertIsInstance(price, int)

    def test_try_depo_data_attribute_price(self):
        html = '<div data-price="250000"></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        price = views._try_depo_data_attribute_price(card)
        self.assertIsInstance(price, int)

    def test_try_depo_special_price(self):
        html = '<div class="special-price">Rp 300.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        price = views._try_depo_special_price(card)
        self.assertIsInstance(price, int)

    def test_try_depo_regular_price(self):
        html = '<div class="regular-price">Rp 350.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        price = views._try_depo_regular_price(card)
        self.assertIsInstance(price, int)

    def test_try_depo_currency_text_price(self):
        html = '<div>Rp 400.000</div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        price = views._try_depo_currency_text_price(card)
        self.assertIsInstance(price, int)


class Mitra10NameExtractionTests(TestCase):
    """Test Mitra10 name extraction strategies"""

    def test_try_specific_mitra10_selectors(self):
        html = '<div class="product-name">Test Product</div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        name = views._try_specific_mitra10_selectors(container)
        # May return None if selector doesn't match
        self.assertIsInstance(name, (str, type(None)))

    def test_try_mitra10_image_alt(self):
        html = '<div><img alt="Product Image" /></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        name = views._try_mitra10_image_alt(container)
        self.assertIsInstance(name, (str, type(None)))

    def test_try_mitra10_link_text(self):
        html = '<div><a href="/product">Product Link</a></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        name = views._try_mitra10_link_text(container)
        self.assertIsInstance(name, (str, type(None)))

    def test_try_mitra10_generic_text(self):
        html = '<div>Generic Product Text</div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        name = views._try_mitra10_generic_text(container)
        self.assertIsInstance(name, (str, type(None)))


class HandleSuccessfulScrapeTests(TestCase):
    """Test the _handle_successful_scrape function"""

    @patch('dashboard.views._save_products_to_database')
    def test_handle_successful_scrape_with_products(self, mock_save):
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware
        
        factory = RequestFactory()
        request = factory.post('/scrape/')
        
        # Add middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))
        
        # Create mock result object with products attribute
        class MockProduct:
            def __init__(self, name, price, unit, location):
                self.name = name
                self.price = price
                self.unit = unit
                self.location = location
                self.url = ''
        
        res = MagicMock()
        res.products = [
            MockProduct('Product 1', 100000, 'pcs', 'Jakarta'),
            MockProduct('Product 2', 200000, 'm2', 'Jakarta')
        ]
        
        rows = views._handle_successful_scrape(request, res, 'gemilang', 'https://test.com', 1000)
        
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)
        mock_save.assert_called_once()

    @patch('dashboard.views._save_products_to_database')
    def test_handle_successful_scrape_empty_products(self, mock_save):
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware
        
        factory = RequestFactory()
        request = factory.post('/scrape/')
        
        # Add middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))
        
        res = MagicMock()
        res.products = []
        
        rows = views._handle_successful_scrape(request, res, 'gemilang', 'https://test.com', 0)
        
        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), 0)


class VendorDetectionTests(TestCase):
    """Test vendor detection in _save_products_to_database"""

    def test_save_unknown_vendor_returns_early(self):
        """Test that unknown vendors return True without doing anything"""
        # Create mock product objects
        class MockProduct:
            def __init__(self, name, price, unit):
                self.name = name
                self.price = price
                self.unit = unit
                self.url = ''
        
        products = [MockProduct('Product', 100000, 'pcs')]
        
        # Unknown vendor should return True immediately
        result = views._save_products_to_database(products, 'unknown_vendor')
        self.assertTrue(result)


class RunVendorToCountTests(TestCase):
    """Test the _run_vendor_to_count function"""

    @patch('dashboard.views._handle_successful_scrape')
    def test_run_vendor_to_count_success(self, mock_handle):
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware
        
        factory = RequestFactory()
        request = factory.post('/scrape/')
        
        # Add middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))
        
        # Mock scraper
        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {
            'products': [
                {'name': 'P1', 'price': 100000, 'unit': 'pcs', 'location': 'Jakarta'}
            ]
        }
        mock_url_builder = MagicMock()
        
        mock_handle.return_value = [{'name': 'P1', 'price': 100000}]
        
        count = views._run_vendor_to_count(
            request,
            'cement',
            lambda: (mock_scraper, mock_url_builder),
            'test_source'
        )
        
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)

    @patch('dashboard.views._handle_successful_scrape')
    def test_run_vendor_to_count_with_fallback(self, mock_handle):
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware
        
        factory = RequestFactory()
        request = factory.post('/scrape/')
        
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))
        
        # Mock scraper to return empty
        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {'products': []}
        mock_url_builder = MagicMock()
        
        # Mock fallback to return products
        def mock_fallback(keyword):
            return (
                [{'name': 'P1', 'price': 100000, 'unit': 'pcs', 'location': 'Jakarta'}],
                'https://test.com',
                1000
            )
        
        mock_handle.return_value = [{'name': 'P1', 'price': 100000}]
        
        count = views._run_vendor_to_count(
            request,
            'cement',
            lambda: (mock_scraper, mock_url_builder),
            'test_source',
            mock_fallback
        )
        
        self.assertIsInstance(count, int)
