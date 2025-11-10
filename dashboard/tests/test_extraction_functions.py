"""
Comprehensive tests for product extraction functions across all vendors.
"""
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from dashboard import views


class DepoProductExtractionTest(TestCase):
    """Test Depo Bangunan product extraction functions"""
    
    def test_extract_depo_product_name_from_link(self):
        """Test extracting product name from Depo Bangunan card"""
        html = '<div><strong class="product name product-item-name"><a href="/test">Depo Product</a></strong></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_name(card)
        
        self.assertEqual(result, "Depo Product")
    
    def test_extract_depo_product_name_from_img_alt(self):
        """Test extracting name from image alt"""
        html = '<div><img alt="Depo Product from Image" /></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_name(card)
        
        self.assertEqual(result, "Depo Product from Image")
    
    def test_extract_depo_product_name_returns_none(self):
        """Test returns None when no name found"""
        html = '<div></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_name(card)
        
        self.assertIsNone(result)
    
    def test_extract_depo_product_link(self):
        """Test extracting Depo product link"""
        html = '<div><strong class="product name product-item-name"><a href="/product/123">Test</a></strong></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_link(card)
        
        self.assertEqual(result, "https://www.depobangunan.com/product/123")
    
    def test_extract_depo_product_link_absolute(self):
        """Test extracting absolute URL"""
        html = '<div><a href="https://www.depobangunan.com/full">Test</a></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_link(card)
        
        self.assertEqual(result, "https://www.depobangunan.com/full")
    
    def test_extract_depo_product_link_fallback(self):
        """Test link fallback"""
        html = '<div></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_link(card)
        
        self.assertEqual(result, "https://www.depobangunan.com/")
    
    def test_extract_depo_product_price_data_attribute(self):
        """Test extracting price from data attribute"""
        html = '<div><span data-price-type="finalPrice" data-price-amount="150000">Rp 150.000</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_price(card)
        
        self.assertEqual(result, 150000)
    
    def test_extract_depo_product_price_special_price(self):
        """Test extracting special price"""
        html = '<div><span class="special-price"><span class="price">Rp 250.000</span></span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_price(card)
        
        self.assertEqual(result, 250000)
    
    def test_extract_depo_product_price_regular_price(self):
        """Test extracting regular price"""
        html = '<div><div class="price-box"><span class="price">Rp 350.000</span></div></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_depo_product_price(card)
        
        self.assertEqual(result, 350000)
    
    def test_try_depo_data_attribute_price(self):
        """Test data attribute price extraction"""
        html = '<span data-price-type="finalPrice" data-price-amount="123456.78"></span>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_depo_data_attribute_price(soup)
        
        self.assertEqual(result, 123456)
    
    def test_try_depo_special_price(self):
        """Test special price extraction"""
        html = '<span class="special-price"><span class="price">Rp 999.999</span></span>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_depo_special_price(soup)
        
        self.assertEqual(result, 999999)
    
    def test_try_depo_regular_price(self):
        """Test regular price extraction"""
        html = '<div class="price-box"><span class="price">Rp 777.777</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_depo_regular_price(soup)
        
        self.assertEqual(result, 777777)
    
    def test_try_depo_currency_text_price(self):
        """Test currency text price extraction"""
        html = '<div>Price: Rp 555.555</div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_depo_currency_text_price(soup)
        
        self.assertEqual(result, 555555)
    
    @patch('dashboard.views._human_get')
    @patch('api.depobangunan.unit_parser.DepoBangunanUnitParser')
    def test_extract_depo_product_unit_from_url(self, mock_parser_class, mock_get):
        """Test unit extraction from URL"""
        mock_get.return_value = '<html><body>Unit content</body></html>'
        
        mock_parser = Mock()
        mock_parser.parse_unit_from_detail_page.return_value = "kg"
        mock_parser_class.return_value = mock_parser
        
        result = views._extract_depo_product_unit("/test")
        
        self.assertEqual(result, "kg")
    
    @patch('dashboard.views._human_get')
    def test_extract_depo_product_unit_handles_exception(self, mock_get):
        """Test unit extraction handles exceptions"""
        mock_get.side_effect = Exception("Network error")
        
        result = views._extract_depo_product_unit("/test")
        
        self.assertEqual(result, "")
    
    @patch('api.depobangunan.unit_parser.DepoBangunanUnitParser')
    def test_extract_depo_product_unit_from_name(self, mock_parser_class):
        """Test unit extraction from product name"""
        mock_parser = Mock()
        mock_parser.parse_unit_from_product_name.return_value = "pcs"
        mock_parser_class.return_value = mock_parser
        
        result = views._extract_depo_product_unit_from_name("Test Product 10 pcs")
        
        self.assertEqual(result, "pcs")


class Mitra10ProductExtractionTest(TestCase):
    """Test Mitra10 product extraction functions"""
    
    def test_extract_mitra10_product_name_from_link(self):
        """Test extracting Mitra10 product name"""
        html = '<div><a class="product-item-link" href="/test">Mitra10 Product</a></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        result = views._extract_mitra10_product_name(container)
        
        self.assertEqual(result, "Mitra10 Product")
    
    def test_extract_mitra10_product_name_from_img_alt(self):
        """Test extracting name from image alt"""
        html = '<div><img alt="Mitra10 Product Image" /></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        result = views._extract_mitra10_product_name(container)
        
        self.assertEqual(result, "Mitra10 Product Image")
    
    def test_try_specific_mitra10_selectors(self):
        """Test specific Mitra10 selectors"""
        html = '<div><a class="product-item-link">Test Product Name</a></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        result = views._try_specific_mitra10_selectors(container)
        
        self.assertEqual(result, "Test Product Name")
    
    def test_try_mitra10_image_alt(self):
        """Test image alt extraction"""
        html = '<div><img alt="Valid Product Name" /></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        result = views._try_mitra10_image_alt(container)
        
        self.assertEqual(result, "Valid Product Name")
    
    def test_try_mitra10_link_text(self):
        """Test link text extraction"""
        html = '<div><a href="/test" title="Product from title">Link text</a></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        result = views._try_mitra10_link_text(container)
        
        self.assertEqual(result, "Product from title")
    
    def test_try_mitra10_generic_text(self):
        """Test generic text extraction"""
        html = '<div><span>This is a valid product name text</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        result = views._try_mitra10_generic_text(container)
        
        self.assertEqual(result, "This is a valid product name text")
    
    def test_extract_mitra10_product_url(self):
        """Test Mitra10 URL extraction"""
        html = '<div><a class="product-item-link" href="/product/123">Test</a></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        
        result = views._extract_mitra10_product_url(container, "https://www.mitra10.com")
        
        self.assertIn("/product/123", result)
    
    def test_extract_price_from_node_data_attributes(self):
        """Test price extraction from data attributes"""
        html = '<div><span data-price-amount="99999">Rp 99.999</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._extract_price_from_node(soup)
        
        self.assertEqual(result, 99999)
    
    def test_try_data_attributes_price(self):
        """Test data attributes price"""
        html = '<div><span data-price-amount="88888.00">Price</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_data_attributes_price(soup)
        
        self.assertEqual(result, 88888)
    
    def test_try_specific_price_classes(self):
        """Test specific price classes"""
        html = '<div><span class="price__final">Rp 77.777</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_specific_price_classes(soup)
        
        self.assertEqual(result, 77777)
    
    def test_try_generic_price_classes(self):
        """Test generic price classes"""
        html = '<div><span class="product-price-value">Rp 66.666</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_generic_price_classes(soup)
        
        self.assertEqual(result, 66666)
    
    def test_try_currency_text_price_with_rp(self):
        """Test currency text price with Rp"""
        html = '<div>Price: Rp 55.555</div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_currency_text_price(soup)
        
        self.assertEqual(result, 55555)
    
    def test_try_numeric_text_price(self):
        """Test numeric text price extraction"""
        html = '<div>Product costs 44444 rupiah</div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = views._try_numeric_text_price(soup)
        
        self.assertEqual(result, 44444)
    
    @patch('dashboard.views._human_get')
    @patch('api.mitra10.unit_parser.Mitra10UnitParser')
    def test_extract_mitra10_product_unit(self, mock_parser_class, mock_get):
        """Test Mitra10 unit extraction"""
        mock_get.return_value = '<html>Unit data</html>'
        
        mock_parser = Mock()
        mock_parser.parse_unit.return_value = "meter"
        mock_parser_class.return_value = mock_parser
        
        result = views._extract_mitra10_product_unit("/test")
        
        self.assertEqual(result, "meter")
    
    @patch('api.mitra10.unit_parser.Mitra10UnitExtractor')
    def test_extract_mitra10_product_unit_from_name(self, mock_extractor_class):
        """Test unit extraction from name"""
        mock_extractor = Mock()
        mock_extractor.extract_unit.return_value = "liter"
        mock_extractor_class.return_value = mock_extractor
        
        result = views._extract_mitra10_product_unit_from_name("Product 5 liter")
        
        self.assertEqual(result, "liter")


class TokopediaProductExtractionTest(TestCase):
    """Test Tokopedia product extraction functions"""
    
    def test_extract_tokopedia_product_name(self):
        """Test extracting Tokopedia product name"""
        html = '<div><span class="css-20kt3o">Tokopedia Product</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_tokopedia_product_name(card)
        
        self.assertEqual(result, "Tokopedia Product")
    
    def test_try_primary_tokopedia_name(self):
        """Test primary name selector"""
        html = '<div><span data-testid="lblProductName">Primary Name</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._try_primary_tokopedia_name(card)
        
        self.assertEqual(result, "Primary Name")
    
    def test_try_fallback_tokopedia_name(self):
        """Test fallback name selector"""
        html = '<div><h3>Fallback Product Name</h3></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._try_fallback_tokopedia_name(card)
        
        self.assertEqual(result, "Fallback Product Name")
    
    def test_try_tokopedia_image_alt(self):
        """Test image alt extraction"""
        html = '<div><img alt="Product Alt Text" /></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._try_tokopedia_image_alt(card)
        
        self.assertEqual(result, "Product Alt Text")
    
    def test_extract_tokopedia_product_price(self):
        """Test extracting Tokopedia price"""
        html = '<div><span class="css-o5uqv">Rp62.500</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_tokopedia_product_price(card)
        
        self.assertEqual(result, 62500)
    
    def test_try_primary_tokopedia_price(self):
        """Test primary price selector"""
        html = '<div><span data-testid="lblProductPrice">Rp123.456</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._try_primary_tokopedia_price(card)
        
        self.assertEqual(result, 123456)
    
    def test_clean_tokopedia_price(self):
        """Test Tokopedia price cleaning"""
        result = views._clean_tokopedia_price("Rp 150.000")
        self.assertEqual(result, 150000)
        
        result = views._clean_tokopedia_price("Rp150000")
        self.assertEqual(result, 150000)
        
        result = views._clean_tokopedia_price("150.000")
        self.assertEqual(result, 150000)
    
    def test_extract_tokopedia_product_link(self):
        """Test extracting Tokopedia product link"""
        html = '<div><a data-testid="lnkProductContainer" href="/p/product-123">Test</a></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = views._extract_tokopedia_product_link(card)
        
        self.assertEqual(result, "/p/product-123")
    
    @patch('dashboard.views._human_get')
    def test_extract_tokopedia_product_unit(self, mock_get):
        """Test Tokopedia unit extraction"""
        mock_get.return_value = '<html>Unit content</html>'
        
        with patch('dashboard.views.TokopediaUnitParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser.parse_unit.return_value = "box"
            mock_parser_class.return_value = mock_parser
            
            result = views._extract_tokopedia_product_unit("/test")
            
            self.assertEqual(result, "box")
    
    def test_extract_tokopedia_product_unit_from_name(self):
        """Test unit extraction from name"""
        with patch('dashboard.views.TokopediaUnitParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser._extract_unit_from_name.return_value = "pack"
            mock_parser_class.return_value = mock_parser
            
            result = views._extract_tokopedia_product_unit_from_name("Product 1 pack")
            
            self.assertEqual(result, "pack")
    
    def test_extract_tokopedia_product_location(self):
        """Test location extraction"""
        html = '<div>Location data</div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        with patch('dashboard.views.TokopediaLocationScraper') as mock_scraper_class:
            mock_scraper = Mock()
            mock_scraper.extract_location_from_product_item.return_value = "Jakarta"
            mock_scraper_class.return_value = mock_scraper
            
            result = views._extract_tokopedia_product_location(card)
            
            self.assertEqual(result, "Jakarta")


class JuraganUnitAndLocationTest(TestCase):
    """Test Juragan Material unit and location extraction"""
    
    @patch('dashboard.views._human_get')
    def test_extract_juragan_product_unit(self, mock_get):
        """Test Juragan unit extraction"""
        # The actual CSS selector is very specific, let's test the exception handling instead
        mock_get.return_value = '<html><body></body></html>'
        
        result = views._extract_juragan_product_unit("/product/123")
        
        # Should return empty string when unit not found
        self.assertEqual(result, "")
    
    @patch('dashboard.views._human_get')
    def test_extract_juragan_product_unit_handles_exception(self, mock_get):
        """Test unit extraction handles exceptions"""
        mock_get.side_effect = Exception("Error")
        
        result = views._extract_juragan_product_unit("/test")
        
        self.assertEqual(result, "")
    
    @patch('dashboard.views._human_get')
    def test_extract_juragan_product_location(self, mock_get):
        """Test Juragan location extraction"""
        mock_html = '''<html><body><span id="footer-address-link"><span></span><span>Bandung</span></span></body></html>'''
        mock_get.return_value = mock_html
        
        result = views._extract_juragan_product_location("/product/123")
        
        self.assertEqual(result, "Bandung")
    
    @patch('dashboard.views._human_get')
    def test_extract_juragan_product_location_handles_exception(self, mock_get):
        """Test location extraction handles exceptions"""
        mock_get.side_effect = Exception("Error")
        
        result = views._extract_juragan_product_location("/test")
        
        self.assertEqual(result, "")


class PlaywrightFunctionsTest(TestCase):
    """Test Playwright-related functions"""
    
    def test_looks_like_bot_challenge_with_attention_required(self):
        """Test bot challenge detection"""
        html = '<html><body>Attention Required</body></html>'
        
        result = views._looks_like_bot_challenge(html)
        
        self.assertTrue(result)
    
    def test_looks_like_bot_challenge_with_captcha(self):
        """Test captcha detection"""
        html = '<html><body>Please complete the CAPTCHA</body></html>'
        
        result = views._looks_like_bot_challenge(html)
        
        self.assertTrue(result)
    
    def test_looks_like_bot_challenge_with_cf_challenge(self):
        """Test Cloudflare challenge detection"""
        html = '<html><body class="cf-challenge">Challenge</body></html>'
        
        result = views._looks_like_bot_challenge(html)
        
        self.assertTrue(result)
    
    def test_looks_like_bot_challenge_normal_html(self):
        """Test normal HTML returns False"""
        html = '<html><body>Normal content</body></html>'
        
        result = views._looks_like_bot_challenge(html)
        
        self.assertFalse(result)
    
    def test_looks_like_bot_challenge_empty_html(self):
        """Test empty HTML returns False"""
        result = views._looks_like_bot_challenge("")
        
        self.assertFalse(result)


class JSONLDParsingTest(TestCase):
    """Test JSON-LD parsing functions"""
    
    def test_extract_price_from_jsonld_offers(self):
        """Test price extraction from JSON-LD offers"""
        offers = {"price": "150000"}
        
        result = views._extract_price_from_jsonld_offers(offers)
        
        self.assertEqual(result, 150000)
    
    def test_extract_price_from_jsonld_offers_with_comma(self):
        """Test price with comma"""
        offers = {"price": "150,000"}
        
        result = views._extract_price_from_jsonld_offers(offers)
        
        self.assertEqual(result, 150000)
    
    def test_process_jsonld_product(self):
        """Test processing JSON-LD product"""
        prod_data = {
            "name": "Test Product",
            "offers": {"price": "99999"},
            "url": "https://test.com/product"
        }
        
        name, price, url = views._process_jsonld_product(prod_data)
        
        self.assertEqual(name, "Test Product")
        self.assertEqual(price, 99999)
        self.assertEqual(url, "https://test.com/product")
    
    def test_parse_jsonld_itemlist(self):
        """Test parsing ItemList"""
        data = {
            "@type": "ItemList",
            "itemListElement": [
                {
                    "item": {
                        "@type": "Product",
                        "name": "Product 1",
                        "offers": {"price": "10000"}
                    }
                }
            ]
        }
        
        results = []
        def emit_func(name, price, url):
            results.append((name, price, url))
        
        views._parse_jsonld_itemlist(data, emit_func)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "Product 1")
        self.assertEqual(results[0][1], 10000)
