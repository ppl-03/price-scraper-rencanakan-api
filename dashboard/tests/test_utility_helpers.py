from django.test import TestCase
from dashboard import views
from bs4 import BeautifulSoup


class TextProcessingTests(TestCase):
    """Test text processing utility functions"""

    def test_digits_to_int(self):
        """Test digit extraction and conversion"""
        self.assertEqual(views._digits_to_int("100000"), 100000)
        self.assertEqual(views._digits_to_int("1.000.000"), 1000000)
        self.assertEqual(views._digits_to_int("Rp 50,000"), 50000)
        self.assertEqual(views._digits_to_int("abc123def456"), 123456)

    def test_clean_text(self):
        """Test text cleaning function"""
        result = views._clean_text("  Hello   World  ")
        self.assertEqual(result, "Hello World")
        result = views._clean_text("\n\tMultiple\n\tLines\n")
        self.assertEqual(result, "Multiple Lines")





class FetchLengthTests(TestCase):
    """Test _fetch_len function"""

    def test_fetch_len_with_valid_url(self):
        """Test fetching length of HTML content"""
        # This would need mocking for real tests
        # Testing the function exists and has correct signature
        self.assertTrue(callable(views._fetch_len))


class BotChallengeDetectionTests(TestCase):
    """Test bot challenge detection"""

    def test_looks_like_bot_challenge_false(self):
        """Test normal pages don't trigger bot detection"""
        normal_html = "<html><body><h1>Product Listing</h1></body></html>"
        result = views._looks_like_bot_challenge(normal_html)
        self.assertFalse(result)


class BotChallengeHintTests(TestCase):
    """Test bot challenge hint generation"""

    def test_get_bot_challenge_hint_generic(self):
        """Test generic hint"""
        hint = views._get_bot_challenge_hint("https://example.com/search")
        self.assertIsInstance(hint, str)


class PriceExtractionHelperTests(TestCase):
    """Test price extraction helper functions"""

    def test_extract_price_from_jsonld_offers_single(self):
        """Test extracting price from single offer"""
        offer = {"price": "100000", "priceCurrency": "IDR"}
        result = views._extract_price_from_jsonld_offers(offer)
        self.assertEqual(result, 100000)




class ProcessJsonldProductTests(TestCase):
    """Test JSON-LD product processing"""

    def test_process_jsonld_product_with_name_and_offers(self):
        """Test processing product with name and offers"""
        prod_data = {
            "name": "Test Product",
            "offers": {"price": "100000"},
            "url": "https://example.com/product"
        }
        name, price, url = views._process_jsonld_product(prod_data)
        self.assertEqual(name, "Test Product")
        self.assertEqual(price, 100000)
        self.assertIn("example.com", url)

    def test_process_jsonld_product_missing_data(self):
        """Test processing product with missing data"""
        prod_data = {}
        name, price, url = views._process_jsonld_product(prod_data)
        self.assertIsNone(name)
        self.assertEqual(price, 0)
        self.assertIsNone(url)


class ParseJsonldItemlistTests(TestCase):
    """Test JSON-LD itemlist parsing"""

    def test_parse_jsonld_itemlist_empty(self):
        """Test parsing empty itemlist"""
        results = []
        def emit_func(name, price, url):
            results.append({"name": name, "price": price, "url": url})
        
        data = {}
        views._parse_jsonld_itemlist(data, emit_func)
        self.assertEqual(len(results), 0)


class ParseJsonldProductsTests(TestCase):
    """Test JSON-LD products parsing"""

    def test_parse_jsonld_products_with_dict(self):
        """Test parsing single product dict"""
        results = []
        def emit_func(name, price, url):
            results.append({"name": name, "price": price, "url": url})
        
        data = {"name": "Single Product", "offers": {"price": "100000"}, "url": "url1"}
        views._parse_jsonld_products(data, emit_func)
        self.assertEqual(len(results), 1)

    def test_parse_jsonld_products_with_list(self):
        """Test parsing list of products"""
        results = []
        def emit_func(name, price, url):
            results.append({"name": name, "price": price, "url": url})
        
        data = [
            {"name": "Product 1", "offers": {"price": "100000"}, "url": "url1"},
            {"name": "Product 2", "offers": {"price": "200000"}, "url": "url2"}
        ]
        views._parse_jsonld_products(data, emit_func)
        self.assertEqual(len(results), 2)


class Mitra10ContainerValidationTests(TestCase):
    """Test Mitra10 container validation"""

    def test_is_valid_mitra10_container_without_link(self):
        """Test invalid container without product link"""
        html = '<div><span>Not a product</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('div')
        result = views._is_valid_mitra10_container(container)
        self.assertFalse(result)


class CleanTokopediaPriceTests(TestCase):
    """Test Tokopedia price cleaning"""

    def test_clean_tokopedia_price_standard(self):
        """Test cleaning standard Tokopedia price"""
        result = views._clean_tokopedia_price("Rp100.000")
        self.assertEqual(result, 100000)

    def test_clean_tokopedia_price_with_spaces(self):
        """Test cleaning price with spaces"""
        result = views._clean_tokopedia_price("Rp 250.000")
        self.assertEqual(result, 250000)

    def test_clean_tokopedia_price_with_comma(self):
        """Test cleaning price with comma separator"""
        result = views._clean_tokopedia_price("Rp1,000,000")
        self.assertEqual(result, 1000000)

    def test_clean_tokopedia_price_per_unit(self):
        """Test cleaning price with per unit notation"""
        result = views._clean_tokopedia_price("Rp50.000/pcs")
        self.assertEqual(result, 50000)


class LocationScrapingFormattingTests(TestCase):
    """Test location scraping result formatting"""

    def test_format_location_results(self):
        """Test formatting location results"""
        locations = [
            {"name": "Location 1"},
            {"name": "Location 2"}
        ]
        result = views._format_location_results(locations, "test_source")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["source"], "test_source")



class FallbackLocationsTests(TestCase):
    """Test fallback location functions"""

    def test_get_gemilang_fallback_locations(self):
        """Test Gemilang fallback locations"""
        result = views._get_gemilang_fallback_locations()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_depo_fallback_locations(self):
        """Test Depo fallback locations"""
        result = views._get_depo_fallback_locations()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_mitra10_fallback_locations(self):
        """Test Mitra10 fallback locations"""
        result = views._get_mitra10_fallback_locations()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_fallback_locations_by_source_unknown(self):
        """Test getting fallback locations for unknown source"""
        result = views._get_fallback_locations_by_source("unknown")
        self.assertEqual(len(result), 0)


class UnitExtractionFromNameTests(TestCase):
    """Test unit extraction from product names"""

    def test_extract_depo_product_unit_from_name_meter(self):
        """Test extracting meter unit from Depo product name"""
        name = "Cable 10 meter high quality"
        result = views._extract_depo_product_unit_from_name(name)
        self.assertIn("m", result.lower())

    def test_extract_depo_product_unit_from_name_kilogram(self):
        """Test extracting kg unit from Depo product name"""
        name = "Cement 50 kg Portland"
        result = views._extract_depo_product_unit_from_name(name)
        self.assertIn("kg", result.lower())

    def test_extract_depo_product_unit_from_name_default(self):
        """Test default unit when none found"""
        name = "Generic Product"
        result = views._extract_depo_product_unit_from_name(name)
        self.assertIsInstance(result, str)

    def test_extract_mitra10_product_unit_from_name_meter(self):
        """Test extracting meter unit from Mitra10 product name"""
        name = "Pipe 5 meter PVC"
        result = views._extract_mitra10_product_unit_from_name(name)
        self.assertIn("m", result.lower())

    def test_extract_mitra10_product_unit_from_name_liter(self):
        """Test extracting liter unit from Mitra10 product name"""
        name = "Paint 20 liter white"
        result = views._extract_mitra10_product_unit_from_name(name)
        self.assertIn("l", result.lower())

    def test_extract_mitra10_product_unit_from_name_default(self):
        """Test default unit when none found"""
        name = "Generic Product"
        result = views._extract_mitra10_product_unit_from_name(name)
        self.assertIsInstance(result, str)



    def test_extract_tokopedia_product_unit_from_name_default(self):
        """Test default unit when none found"""
        name = "Generic Product"
        result = views._extract_tokopedia_product_unit_from_name(name)
        self.assertIsInstance(result, str)
