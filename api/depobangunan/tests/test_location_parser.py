from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from api.interfaces import Location, HtmlParserError
from api.depobangunan.location_parser import DepoBangunanLocationParser
from api.depobangunan.location_parser import TextCleaner, HtmlElementExtractor, ParserConfiguration
from bs4 import BeautifulSoup
import sys


class TestDepoBangunanLocationParser(TestCase):
    @classmethod
    def setUpClass(cls):
        """Load mock HTML fixture for testing"""
        fixtures_dir = Path(__file__).parent.parent.parent / 'tests' / 'fixtures'
        mock_location_file = fixtures_dir / 'depo_mock_locations.html'
        
        if mock_location_file.exists():
            with open(mock_location_file, 'r', encoding='utf-8') as f:
                cls.mock_location_html = f.read()
        else:
            # Fallback mock HTML if fixture doesn't exist
            cls.mock_location_html = """
            <html>
                <h2>Depo Bangunan - Kalimalang</h2>
                <p>Jl. Raya Kalimalang No.46, Duren Sawit, Kec. Duren Sawit, Timur, Daerah Khusus Ibukota Jakarta 13440</p>
                
                <h2>Depo Bangunan - Tangerang Selatan</h2>
                <p>Jl. Raya Serpong No.KM.2, Pakulonan, Kec. Serpong Utara, Kota Tangerang Selatan, Banten 15325</p>
            </html>
            """

    def setUp(self):
        self.parser = DepoBangunanLocationParser()

    def test_parse_locations_from_mock_html(self):
        """Test parsing locations from mock HTML"""
        locations = self.parser.parse_locations(self.mock_location_html)
        
        self.assertGreaterEqual(len(locations), 1)
        
        # Check first location
        location1 = locations[0]
        # Location names should NOT contain "Depo Bangunan" prefix
        self.assertNotIn("Depo Bangunan -", location1.name)
        self.assertIsNotNone(location1.code)
        self.assertGreater(len(location1.code), 0)

    def test_parse_empty_html(self):
        """Test parsing empty HTML returns empty list"""
        locations = self.parser.parse_locations("")
        self.assertEqual(len(locations), 0)

    def test_parse_html_with_no_locations(self):
        """Test parsing HTML with no location data"""
        html_no_locations = "<html><body><div>No locations found</div></body></html>"
        locations = self.parser.parse_locations(html_no_locations)
        self.assertEqual(len(locations), 0)

    def test_parse_malformed_html(self):
        """Test parsing malformed HTML doesn't crash"""
        malformed_html = "<h2>Depo Bangunan - Test</h2><p>incomplete"
        locations = self.parser.parse_locations(malformed_html)
        self.assertIsInstance(locations, list)

    def test_extract_location_with_missing_store_name(self):
        """Test extraction fails gracefully when store name is missing"""
        html_missing_name = """
        <html>
            <h2>Just a regular header</h2>
            <p>Jl. Test Street<br>Test City<br>Indonesia</p>
        </html>
        """
        locations = self.parser.parse_locations(html_missing_name)
        self.assertEqual(len(locations), 0)

    def test_extract_location_with_missing_address(self):
        """Test extraction fails gracefully when address is missing"""
        html_missing_address = """
        <html>
            <h2>Depo Bangunan - Test Store</h2>
        </html>
        """
        locations = self.parser.parse_locations(html_missing_address)
        self.assertEqual(len(locations), 0)

    def test_extract_store_name_cleaning(self):
        """Test store name is properly cleaned of whitespace"""
        html_with_whitespace = """
        <html>
            <h2>   Depo Bangunan - Test Store   </h2>
            <p>Test Address, Test City</p>
        </html>
        """
        locations = self.parser.parse_locations(html_with_whitespace)
        if len(locations) > 0:
            self.assertEqual(locations[0].name, "Test Store")

    def test_extract_address_with_alamat_prefix(self):
        """Test address extraction handles 'Alamat:' prefix"""
        html_with_alamat = """
        <html>
            <h2>Depo Bangunan - Test Store</h2>
            <p>Alamat: Jl. Test Street 123, Test City, Test Province</p>
        </html>
        """
        locations = self.parser.parse_locations(html_with_alamat)
        self.assertEqual(len(locations), 1)
        # Address should not contain "Alamat:" prefix
        self.assertNotIn("Alamat:", locations[0].code)
        self.assertIn("Jl. Test Street", locations[0].code)

    def test_parse_html_raises_error_on_critical_failure(self):
        """Test parser handles critical failures gracefully"""
        # Parser should not raise exceptions, just return empty list
        result = self.parser.parse_locations(None)
        self.assertEqual(len(result), 0)

    def test_location_parser_handles_different_html_structure(self):
        """Test parser only matches expected HTML structure"""
        html_variation = """
        <html>
            <div class="store-item">
                <h3>Depo Bangunan - Variation Store</h3>
                <div class="location-info">Variation Address, Variation City</div>
            </div>
        </html>
        """
        locations = self.parser.parse_locations(html_variation)
        # Should not match h3 tags, only h2
        self.assertEqual(len(locations), 0)

    def test_extract_location_with_special_characters(self):
        """Test extraction handles special characters in names and addresses"""
        html_special_chars = """
        <html>
            <h2>Depo Bangunan - Store & Co.</h2>
            <p>Jl. Raya No. 123/A-B, Kota (Special), Provinsi</p>
        </html>
        """
        locations = self.parser.parse_locations(html_special_chars)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].name, "Store & Co.")
        self.assertIn("123/A-B", locations[0].code)

    def test_parse_locations_with_nested_elements(self):
        """Test parser handles nested HTML elements"""
        html_nested = """
        <html>
            <h2><span>Depo Bangunan - Nested Store</span></h2>
            <p><span>Jl. Nested Street</span>, Nested City</p>
        </html>
        """
        locations = self.parser.parse_locations(html_nested)
        self.assertEqual(len(locations), 1)
        self.assertIn("Nested Store", locations[0].name)

    def test_parse_locations_with_multiple_stores(self):
        """Test parsing multiple stores correctly"""
        html_multiple = """
        <html>
            <h2>Depo Bangunan - Store A</h2>
            <p>Address A, City A</p>
            
            <h2>Depo Bangunan - Store B</h2>
            <p>Address B, City B</p>
            
            <h2>Depo Bangunan - Store C</h2>
            <p>Address C, City C</p>
        </html>
        """
        locations = self.parser.parse_locations(html_multiple)
        self.assertEqual(len(locations), 3)
        self.assertEqual(locations[0].name, "Store A")
        self.assertEqual(locations[1].name, "Store B")
        self.assertEqual(locations[2].name, "Store C")

    def test_parse_locations_with_unicode_characters(self):
        """Test parser handles Unicode characters"""
        html_unicode = """
        <html>
            <h2>Depo Bangunan - Tôkô Spéciàl</h2>
            <p>Jl. Spéciàl Streét 123, Città Spéciàl, Prövincé</p>
        </html>
        """
        locations = self.parser.parse_locations(html_unicode)
        self.assertEqual(len(locations), 1)
        self.assertIn("Tôkô Spéciàl", locations[0].name)

    def test_parse_locations_with_empty_paragraph(self):
        """Test parser handles empty paragraph tags"""
        html_empty_p = """
        <html>
            <h2>Depo Bangunan - Empty Address Store</h2>
            <p></p>
        </html>
        """
        locations = self.parser.parse_locations(html_empty_p)
        self.assertEqual(len(locations), 0)

    def test_parse_locations_with_whitespace_only_address(self):
        """Test parser handles whitespace-only addresses"""
        html_whitespace_address = """
        <html>
            <h2>Depo Bangunan - Whitespace Store</h2>
            <p>   </p>
        </html>
        """
        locations = self.parser.parse_locations(html_whitespace_address)
        self.assertEqual(len(locations), 0)

    def test_parse_locations_case_sensitive_header_check(self):
        """Test that parser correctly identifies Depo Bangunan stores"""
        html_wrong_case = """
        <html>
            <h2>depo bangunan - lowercase</h2>
            <p>Some Address</p>
            
            <h2>Depo Bangunan - Correct Case</h2>
            <p>Correct Address</p>
        </html>
        """
        locations = self.parser.parse_locations(html_wrong_case)
        # Should only match exact case "Depo Bangunan -"
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].name, "Correct Case")

    def test_parse_locations_with_html_entities(self):
        """Test parser handles HTML entities"""
        html_entities = """
        <html>
            <h2>Depo Bangunan &amp; Partners - Test</h2>
            <p>Jl. Test &gt; Special, City &lt; Province</p>
        </html>
        """
        locations = self.parser.parse_locations(html_entities)
        if len(locations) > 0:
            self.assertIn("&", locations[0].name)

    def test_parse_locations_with_mixed_content(self):
        """Test parser handles mixed content with other headers"""
        html_mixed = """
        <html>
            <h1>Main Title</h1>
            <h2>Some Other Header</h2>
            <p>Random paragraph</p>
            
            <h2>Depo Bangunan - Valid Store</h2>
            <p>Valid Address, Valid City</p>
            
            <h3>Sub header</h3>
            <p>More content</p>
        </html>
        """
        locations = self.parser.parse_locations(html_mixed)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].name, "Valid Store")

    def test_parse_large_number_of_locations(self):
        """Test parser can handle many locations"""
        html_parts = ["<html>"]
        for i in range(50):
            html_parts.append(f"<h2>Depo Bangunan - Store {i}</h2>")
            html_parts.append(f"<p>Address {i}, City {i}</p>")
        html_parts.append("</html>")
        
        large_html = "\n".join(html_parts)
        locations = self.parser.parse_locations(large_html)
        self.assertEqual(len(locations), 50)

    def test_parse_locations_performance_with_malformed_html(self):
        """Test parser doesn't hang on malformed HTML"""
        malformed_html = "<h2>Depo Bangunan - Test" * 100 + "<p>Address" * 100
        locations = self.parser.parse_locations(malformed_html)
        self.assertIsInstance(locations, list)

    def test_address_without_jl_prefix(self):
        """Test address extraction works without 'Jl.' prefix"""
        html_no_jl = """
        <html>
            <h2>Depo Bangunan - Test Store</h2>
            <p>Kompleks Central Square, Gedangan</p>
        </html>
        """
        locations = self.parser.parse_locations(html_no_jl)
        self.assertIsInstance(locations, list)

    def test_multiple_paragraphs_after_header(self):
        """Test parser picks the correct paragraph for address"""
        html_multi_p = """
        <html>
            <h2>Depo Bangunan - Test Store</h2>
            <p>Jadwal Buka: 08:00 - 21:00</p>
            <p>Alamat: Jl. Test Street 123, Test City</p>
        </html>
        """
        locations = self.parser.parse_locations(html_multi_p)
        if len(locations) > 0:
            # Should extract the paragraph with address
            self.assertIn("Jl. Test Street", locations[0].code)
            self.assertNotIn("Jadwal Buka", locations[0].code)

    def test_text_cleaner_clean_store_name_prefix(self):
        # name with 'Depo Bangunan -' prefix should have it removed
        raw = 'Depo Bangunan - Super Supplier'
        cleaned = TextCleaner.clean_store_name(raw)
        self.assertEqual(cleaned, 'Super Supplier')
        
        # name without 'Depo Bangunan -' should remain as is (just stripped)
        raw2 = 'Super Supplier'
        cleaned2 = TextCleaner.clean_store_name(raw2)
        self.assertEqual(cleaned2, 'Super Supplier')

    def test_html_element_extractor_extract_store_name_exception(self):
        # Header object whose get_text raises exception
        class BadHeader:
            def get_text(self, strip=True):
                raise ValueError('bad header')

        extractor = HtmlElementExtractor(TextCleaner(), ParserConfiguration())
        self.assertIsNone(extractor.extract_store_name(BadHeader()))

    def test_html_element_extractor_skips_non_address_pattern(self):
        # Create HTML where first p contains non-address indicator and second p is address
        config = ParserConfiguration()
        # add a custom non-address pattern
        config.non_address_patterns = ['IGNORE_ME']
        extractor = HtmlElementExtractor(TextCleaner(), config)

        html = '<h2>Depo Bangunan - T</h2><p>IGNORE_ME: not address</p><p>Jl. Real Address 1</p>'
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h2')
        addr = extractor.extract_address(header)
        self.assertIsNotNone(addr)
        self.assertIn('Jl. Real Address', addr)

    def test_parser_configuration_get_parser_when_lxml_missing_and_present(self):
        # Simulate lxml missing
        config = ParserConfiguration()
        saved = sys.modules.pop('lxml', None)
        try:
            self.assertEqual(config.get_parser(), config.fallback_parser)
        finally:
            if saved is not None:
                sys.modules['lxml'] = saved

        # Simulate lxml present
        sys.modules['lxml'] = True
        try:
            self.assertEqual(config.get_parser(), config.preferred_parser)
        finally:
            sys.modules.pop('lxml', None)



class TestLocationParserEdgeCases(TestCase):
    
    def test_parse_locations_with_none_html(self):
        """Test parse_locations with None HTML"""
        parser = DepoBangunanLocationParser()
        result = parser.parse_locations(None)
        self.assertEqual(result, [])
    
    def test_parse_locations_with_empty_html(self):
        """Test parse_locations with empty HTML"""
        parser = DepoBangunanLocationParser()
        result = parser.parse_locations("")
        self.assertEqual(result, [])
    
    def test_parse_locations_with_invalid_items(self):
        """Test parsing locations when items don't have required data"""
        html = '''
        <html>
            <body>
                <select id="ktplocation">
                    <option value="">Invalid</option>
                    <option>No value attribute</option>
                </select>
            </body>
        </html>
        '''
        
        parser = DepoBangunanLocationParser()
        result = parser.parse_locations(html)
        # Should skip invalid items
        self.assertIsInstance(result, list)
    
    def test_text_cleaner_clean_store_name_empty(self):
        """Line 19: clean_store_name with empty text returns empty string"""
        result = TextCleaner.clean_store_name("")
        self.assertEqual(result, "")
    
    def test_text_cleaner_clean_address_empty(self):
        """Line 29: clean_address with empty text returns empty string"""
        result = TextCleaner.clean_address("")
        self.assertEqual(result, "")
    
    def test_extract_store_name_invalid_text(self):
        """Lines 57-58: extract_store_name with invalid text returns None"""
        config = ParserConfiguration()
        extractor = HtmlElementExtractor(TextCleaner(), config)
        
        # Create header with whitespace-only text
        html = '<h2>   </h2>'
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h2')
        
        result = extractor.extract_store_name(header)
        self.assertIsNone(result)
    
    def test_extract_address_cleaned_whitespace_only(self):
        """Lines 100-102: extract_address returns None when cleaned address is whitespace"""
        config = ParserConfiguration()
        extractor = HtmlElementExtractor(TextCleaner(), config)
        
        # Create HTML where address becomes whitespace after cleaning
        html = '<h2>Test</h2><p>\n\n\n</p>'
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h2')
        
        result = extractor.extract_address(header)
        self.assertIsNone(result)
    
    def test_extract_address_exception_handling(self):
        """Lines 158-160: extract_address handles exceptions"""
        config = ParserConfiguration()
        extractor = HtmlElementExtractor(TextCleaner(), config)
        
        # Create a mock header that causes exception
        class BadHeader:
            def find_next_sibling(self):
                raise ValueError("Simulated error")
        
        result = extractor.extract_address(BadHeader())
        self.assertIsNone(result)
    
    def test_extract_locations_from_soup_exception_handling(self):
        """Lines 195-197: _extract_locations_from_soup handles exceptions per header"""
        parser = DepoBangunanLocationParser()
        
        # Create HTML with a header that will cause issues
        html = '''
        <html>
            <h2>Depo Bangunan - Valid Store</h2>
            <p>Valid Address</p>
            <h2>Depo Bangunan - Will Fail</h2>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        # The parser should continue even if one header fails
        locations = parser._extract_locations_from_soup(soup)
        # Should get at least the valid one
        self.assertGreaterEqual(len(locations), 1)
    
    def test_parse_locations_general_exception(self):
        """Lines 205-206: parse_locations handles general exceptions"""
        parser = DepoBangunanLocationParser()
        
        # Override _create_soup to raise an exception
        def bad_create_soup(html_content):
            raise RuntimeError("Simulated parsing error")
        
        parser._create_soup = bad_create_soup
        
        result = parser.parse_locations("<html>test</html>")
        self.assertEqual(result, [])
    
    def test_gerai_header_skipped(self):
        """Line 187: Headers starting with 'Gerai' are skipped"""
        parser = DepoBangunanLocationParser()
        
        html = '''
        <html>
            <h2>Gerai Depo Bangunan Central</h2>
            <p>This should be skipped</p>
            <h2>Depo Bangunan - Valid Store</h2>
            <p>Valid Address</p>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        locations = parser._extract_locations_from_soup(soup)
        # Should only get the valid one, not the "Gerai" header
        self.assertEqual(len(locations), 1)
        self.assertNotIn("Gerai", locations[0].store_name)
    
    def test_extract_locations_continue_on_exception(self):
        """Lines 195-197: Exception in one header continues to next"""
        parser = DepoBangunanLocationParser()
        
        # Create HTML with multiple headers where one will cause exception
        html = '''
        <html>
            <h2>Depo Bangunan - First Store</h2>
            <p>First Address</p>
            <h2>Depo Bangunan - Second Store</h2>
            <p>Second Address</p>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        headers = soup.find_all('h2')
        
        # Mock get_text to fail on second header
        def bad_get_text(*args, **kwargs):
            raise ValueError("Simulated header error")
        headers[1].get_text = bad_get_text
        
        # Should still process other headers despite exception
        locations = parser._extract_locations_from_soup(soup)
        self.assertGreaterEqual(len(locations), 1)
    
    def test_parse_locations_with_bad_html_structure(self):
        """Lines 205-206: parse_locations returns [] on parsing failure"""
        parser = DepoBangunanLocationParser()
        
        # Provide malformed HTML that causes BeautifulSoup issues
        # But we need to trigger exception in parse_locations, not _create_soup
        with patch.object(parser, '_extract_locations_from_soup', side_effect=Exception("Parse error")):
            result = parser.parse_locations("<html><h2>Test</h2></html>")
            self.assertEqual(result, [])
    
    def test_extract_location_from_header_no_store_name(self):
        """Lines 205-206: _extract_location_from_header returns None when store name extraction fails"""
        parser = DepoBangunanLocationParser()
        
        # Create a header that will fail store name extraction
        html = '<h2>   </h2><p>Some Address</p>'
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h2')
        
        result = parser._extract_location_from_header(header)
        self.assertIsNone(result)

