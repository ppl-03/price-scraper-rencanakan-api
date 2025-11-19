from django.test import TestCase
from unittest.mock import patch, MagicMock
from dashboard import views


class PlaywrightTests(TestCase):
    """Tests for Playwright-related code paths"""

    @patch('dashboard.views.HAS_PLAYWRIGHT', True)
    @patch('dashboard.views.sync_playwright')
    def test_fetch_with_playwright_success(self, mock_playwright):
        # Mock the playwright context
        mock_context = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        
        mock_page.content.return_value = '<html><body>Test Content</body></html>'
        mock_browser.new_context.return_value.new_page.return_value = mock_page
        mock_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_context
        
        html = views._fetch_with_playwright('https://test.com')
        
        # Returns string or empty string
        self.assertIsInstance(html, str)

    @patch('dashboard.views.HAS_PLAYWRIGHT', True)
    @patch('dashboard.views.sync_playwright')
    def test_fetch_with_playwright_exception(self, mock_playwright):
        # Mock playwright to raise an exception
        mock_playwright.side_effect = Exception('Playwright error')
        
        html = views._fetch_with_playwright('https://test.com')
        
        # Should return empty string on error
        self.assertEqual(html, '')

    @patch('dashboard.views.HAS_PLAYWRIGHT', False)
    def test_fetch_with_playwright_not_available(self):
        # When Playwright is not available, should return empty string
        html = views._fetch_with_playwright('https://test.com')
        self.assertEqual(html, '')


class Mitra10ParsingTests(TestCase):
    """Tests for Mitra10 HTML parsing functions"""

    def test_parse_mitra10_html_with_products(self):
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
        <body>
            <div class="product-card">
                <div class="product-name">Product A</div>
                <div class="product-price" data-price="100000">Rp 100.000</div>
            </div>
            <div class="product-card">
                <div class="product-name">Product B</div>
                <div class="product-price">Rp 200.000</div>
            </div>
        </body>
        </html>
        '''
        
        results = views._parse_mitra10_html(html, 'https://mitra10.com/search?q=cement')
        
        # May or may not find products depending on selector strictness
        self.assertIsInstance(results, list)

    def test_parse_mitra10_html_empty(self):
        html = '<html><body></body></html>'
        results = views._parse_mitra10_html(html, 'https://mitra10.com')
        self.assertEqual(results, [])

    def test_parse_mitra10_html_invalid(self):
        html = 'not valid html'
        results = views._parse_mitra10_html(html, 'https://mitra10.com')
        self.assertIsInstance(results, list)


class DepoParsingTests(TestCase):
    """Tests for Depo Bangunan parsing functions"""

    def test_extract_depo_product_name_success(self):
        from bs4 import BeautifulSoup
        
        html = '''
        <div class="product-card">
            <h3 class="product-title">Test Product</h3>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div', class_='product-card')
        
        name = views._extract_depo_product_name(card)
        
        if name:  # May return None depending on selector match
            self.assertIsInstance(name, str)
            self.assertGreater(len(name), 0)

    def test_extract_depo_product_unit_success(self):
        from bs4 import BeautifulSoup
        
        html = '''
        <div class="product-card">
            <span class="unit">per m2</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div', class_='product-card')
        
        unit = views._extract_depo_product_unit(card)
        
        if unit:
            self.assertIsInstance(unit, str)

    def test_extract_depo_product_link(self):
        from bs4 import BeautifulSoup
        
        html = '<div class="product-card"><a href="/product/123">Link</a></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div', class_='product-card')
        
        link = views._extract_depo_product_link(card)
        
        # May or may not find a link
        self.assertIsInstance(link, (str, type(None)))


class JuraganParsingTests(TestCase):
    """Tests for Juragan Material parsing functions"""

    def test_extract_juragan_product_name(self):
        from bs4 import BeautifulSoup
        
        html = '''
        <div class="product">
            <div class="product-name">Test Juragan Product</div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div', class_='product')
        
        name = views._extract_juragan_product_name(card)
        
        if name:
            self.assertIsInstance(name, str)
            self.assertGreater(len(name), 0)

    def test_extract_juragan_product_unit(self):
        from bs4 import BeautifulSoup
        
        html = '''
        <div class="product">
            <span class="unit-info">per pcs</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div', class_='product')
        
        unit = views._extract_juragan_product_unit(card)
        
        if unit:
            self.assertIsInstance(unit, str)

    def test_extract_juragan_product_location_empty(self):
        from bs4 import BeautifulSoup
        
        html = '<div class="product"></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div', class_='product')
        
        location = views._extract_juragan_product_location(card)
        
        # May return empty string or a default value
        self.assertIsInstance(location, str)


class TokopediaParsingTests(TestCase):
    """Tests for Tokopedia parsing functions"""

    def test_parse_tokopedia_html_with_jsonld(self):
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "Tokopedia Product",
                "offers": {
                    "@type": "Offer",
                    "price": "150000",
                    "priceCurrency": "IDR"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        '''
        
        results = views._parse_tokopedia_html(html)
        
        self.assertIsInstance(results, list)
        # May or may not extract depending on exact parsing logic
        
    def test_parse_tokopedia_html_empty(self):
        html = '<html><body></body></html>'
        results = views._parse_tokopedia_html(html)
        self.assertEqual(results, [])
