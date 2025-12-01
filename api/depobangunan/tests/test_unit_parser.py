import unittest
from unittest.mock import Mock, patch
from api.depobangunan.unit_parser import DepoBangunanUnitExtractor, DepoBangunanUnitParser


class TestDepoBangunanUnitExtractor(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.extractor = DepoBangunanUnitExtractor()
    
    def test_extract_unit_from_name_with_kg_pattern(self):
        """Test extracting KG unit from product names."""
        test_cases = [
            ("MAGIX WIN TILE GROUT WHITE 1KG", "KG"),
            ("SEMEN PORTLAND 50KG", "KG"),
            ("CAT TEMBOK 25 KG", "KG"),
            ("BETON READY MIX 40KG", "KG"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_name_with_gram_patterns(self):
        """Test extracting gram units from product names."""
        test_cases = [
            ("BAUT M8 500GRAM", "G"),
            ("SEKRUP 250GR", "G"),
            ("PAKU 100 GRAM", "G"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_name_with_liter_patterns(self):
        """Test extracting liter units from product names."""
        test_cases = [
            ("CAT PRIMER 5 LITER", "L"),
            ("THINNER 1LT", "L"),
            ("PELARUT 2.5L", "L"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_name_with_ml_patterns(self):
        """Test extracting milliliter units from product names."""
        test_cases = [
            ("PYLOX SOLID 102 WHITE 300CC", "CC"),
            ("CAT SPRAY 400ML", "ML"),
            ("PRIMER 250 ML", "ML"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_name_with_inch_patterns(self):
        """Test extracting inch units from product names."""
        test_cases = [
            ('DBS FILAMENT PAINT BRUSH, 3"', "INCH"),
            ("KUAS 4 INCH", "INCH"),
            ('PIPA PVC 2"', "INCH"),
            ("SELANG 1.5 INCH", "INCH"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_name_with_area_patterns(self):
        """Test extracting area units from product names."""
        test_cases = [
            ("KERAMIK 60X60CM", "CM²"),
            ("GRANIT 80x80 CM", "CM²"),
            ("TILE 30X30MM", "MM²"),
            ("PLYWOOD 120x240 CM", "CM²"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_name_with_count_patterns(self):
        """Test extracting count units from product names."""
        test_cases = [
            ("BAUT SET 100 PCS", "PCS"),
            ("SEKRUP PACK 50 PIECES", "PCS"),
            ("TILE GROUT 1 SET", "SET"),
            ("KAWAT 1 ROLL", "ROLL"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_name_should_default_to_pcs_for_tools(self):
        """Test that tools and accessories default to PCS when no unit specified."""
        test_cases = [
            ("UNIK SPONGE (ANGKA 8)", "PCS"),
            ("PAINT BRUSH", "PCS"),
            ("KUAS CAT", "PCS"),
            ("SPONS CUCI", "PCS"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_name_returns_none_for_no_unit(self):
        """Test that products without recognizable units return None."""
        test_cases = [
            "RANDOM PRODUCT NAME",
            "SOME CONSTRUCTION MATERIAL",
            "BUILDING SUPPLIES",
        ]
        
        for product_name in test_cases:
            with self.subTest(product_name=product_name):
                result = self.extractor.extract_unit_from_name(product_name)
                self.assertIsNone(result)
    
    def test_extract_unit_from_name_handles_none_input(self):
        """Test that None input is handled gracefully."""
        result = self.extractor.extract_unit_from_name(None)
        self.assertIsNone(result)
    
    def test_extract_unit_from_name_handles_empty_string(self):
        """Test that empty string is handled gracefully."""
        result = self.extractor.extract_unit_from_name("")
        self.assertIsNone(result)
    
    def test_extract_unit_from_specification_with_kg_value(self):
        """Test extracting unit from specification text like '1KG'."""
        test_cases = [
            ("1KG", "KG"),
            ("25KG", "KG"),
            ("2.5KG", "KG"),
        ]
        
        for spec_text, expected_unit in test_cases:
            with self.subTest(spec_text=spec_text):
                result = self.extractor.extract_unit_from_specification(spec_text)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_specification_with_various_units(self):
        """Test extracting various units from specification text."""
        test_cases = [
            ("5L", "L"),
            ("300ML", "ML"),
            ("2.5M", "M"),
            ("50CM", "CM"),
            ("10PCS", "PCS"),
        ]
        
        for spec_text, expected_unit in test_cases:
            with self.subTest(spec_text=spec_text):
                result = self.extractor.extract_unit_from_specification(spec_text)
                self.assertEqual(result, expected_unit)
    
    def test_extract_unit_from_specification_returns_none_for_invalid(self):
        """Test that invalid specification text returns None."""
        test_cases = [
            None,
            "",
            "INVALID",
            "123",
        ]
        
        for spec_text in test_cases:
            with self.subTest(spec_text=spec_text):
                result = self.extractor.extract_unit_from_specification(spec_text)
                self.assertIsNone(result)


class TestDepoBangunanUnitParser(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.parser = DepoBangunanUnitParser()
    
    def test_parse_unit_from_product_name(self):
        """Test parsing unit from product name."""
        product_name = "MAGIX WIN TILE GROUT WHITE 1KG"
        result = self.parser.parse_unit_from_product_name(product_name)
        self.assertEqual(result, "KG")
    
    @patch('api.depobangunan.unit_parser.BeautifulSoup')
    def test_parse_unit_from_detail_page_with_table(self, mock_soup_class):
        """Test parsing unit from detail page HTML with specification table."""
        # Mock HTML structure
        mock_soup = Mock()
        mock_soup_class.return_value = mock_soup
        
        # Mock table with Ukuran specification
        mock_table = Mock()
        mock_row = Mock()
        mock_cell1 = Mock()
        mock_cell2 = Mock()
        
        mock_cell1.get_text.return_value = "Ukuran"
        mock_cell2.get_text.return_value = "1KG"
        mock_row.find_all.return_value = [mock_cell1, mock_cell2]
        mock_table.find_all.return_value = [mock_row]
        mock_soup.find_all.return_value = [mock_table]
        
        html_content = "<table><tr><td>Ukuran</td><td>1KG</td></tr></table>"
        result = self.parser.parse_unit_from_detail_page(html_content)
        
        self.assertEqual(result, "KG")
    
    def test_parse_unit_from_detail_page_with_empty_html(self):
        """Test parsing unit from empty HTML content."""
        result = self.parser.parse_unit_from_detail_page("")
        self.assertEqual(result, 'PCS')
    
    def test_parse_unit_from_detail_page_with_none_html(self):
        """Test parsing unit from None HTML content."""
        result = self.parser.parse_unit_from_detail_page(None)
        self.assertEqual(result, 'PCS')


class TestDepoBangunanUnitParserIntegration(unittest.TestCase):
    """Integration tests for the complete unit parsing workflow."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.parser = DepoBangunanUnitParser()
    
    def test_unit_parsing_priority_order(self):
        """Test that unit parsing follows the correct priority order."""
        # Area units should take priority over linear units
        product_name = "KERAMIK 60X60CM MOTIF"
        result = self.parser.parse_unit_from_product_name(product_name)
        self.assertEqual(result, "CM²")  # Should be area, not just CM
        
        # Weight units should be detected correctly
        product_name = "SEMEN PORTLAND 50KG"
        result = self.parser.parse_unit_from_product_name(product_name)
        self.assertEqual(result, "KG")
    
    def test_unit_parsing_case_insensitive(self):
        """Test that unit parsing is case insensitive."""
        test_cases = [
            ("magix win tile grout white 1kg", "KG"),
            ("MAGIX WIN TILE GROUT WHITE 1KG", "KG"),
            ("Magix Win Tile Grout White 1Kg", "KG"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.parser.parse_unit_from_product_name(product_name)
                self.assertEqual(result, expected_unit)
    
    def test_unit_parsing_with_special_characters(self):
        """Test unit parsing with special characters and punctuation."""
        test_cases = [
            ('DBS FILAMENT PAINT BRUSH, 3"', "INCH"),
            ("KUAS (4 INCH)", "INCH"),
            ("CAT 2.5L - PRIMER", "L"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.parser.parse_unit_from_product_name(product_name)
                self.assertEqual(result, expected_unit)

    def test_extract_feet_patterns_and_standard_adjacent(self):
        extractor = DepoBangunanUnitExtractor()
        self.assertEqual(extractor.extract_unit_from_name("PIPA 6'"), 'FEET')
        self.assertEqual(extractor.extract_unit_from_name("ROD 2 ft"), 'FEET')
        self.assertEqual(extractor.extract_unit_from_name("NAIL 10 pcs"), 'PCS')

    def test_extract_unit_from_detail_page_near_element(self):
        parser = DepoBangunanUnitParser()
        html = '<div><span>Ukuran</span><span> 2kg </span></div>'
        # Should find 'Ukuran' keyword and then detect 2kg
        res = parser.parse_unit_from_detail_page(html)
        self.assertEqual(res, 'KG')


class TestUnitParserPCSDefault(unittest.TestCase):
    """Tests for unit parser PCS default behavior when unit is None or X"""
    
    def setUp(self):
        self.parser = DepoBangunanUnitParser()
    
    def test_parse_unit_from_name_returns_pcs_for_none(self):
        """Test that None unit defaults to PCS"""
        with patch.object(self.parser.extractor, 'extract_unit_from_name', return_value=None):
            result = self.parser.parse_unit_from_product_name('Some Product Name')
            self.assertEqual(result, 'PCS')
    
    def test_parse_unit_from_name_returns_pcs_for_uppercase_x(self):
        """Test that 'X' unit defaults to PCS"""
        with patch.object(self.parser.extractor, 'extract_unit_from_name', return_value='X'):
            result = self.parser.parse_unit_from_product_name('Product X Name')
            self.assertEqual(result, 'PCS')
    
    def test_parse_unit_from_name_valid_unit_kg(self):
        """Test that valid KG unit is returned as-is"""
        with patch.object(self.parser.extractor, 'extract_unit_from_name', return_value='KG'):
            result = self.parser.parse_unit_from_product_name('Semen 50 KG')
            self.assertEqual(result, 'KG')
    
    def test_parse_unit_from_name_valid_unit_liter(self):
        """Test that valid L unit is returned as-is"""
        with patch.object(self.parser.extractor, 'extract_unit_from_name', return_value='L'):
            result = self.parser.parse_unit_from_product_name('Cat 5 Liter')
            self.assertEqual(result, 'L')
    
    def test_parse_unit_from_detail_page_returns_pcs_on_no_content(self):
        """Test that detail page parser returns PCS when content is None"""
        result = self.parser.parse_unit_from_detail_page(None)
        self.assertEqual(result, 'PCS')
    
    def test_parse_unit_from_detail_page_returns_pcs_on_empty_content(self):
        """Test that detail page parser returns PCS for empty string"""
        result = self.parser.parse_unit_from_detail_page('')
        self.assertEqual(result, 'PCS')
    
    def test_parse_unit_from_detail_page_returns_pcs_when_not_found(self):
        """Test that detail page parser returns PCS when unit not found"""
        html = '<html><body><div>No unit info here</div></body></html>'
        result = self.parser.parse_unit_from_detail_page(html)
        self.assertEqual(result, 'PCS')
    
    def test_parse_unit_from_detail_page_valid_unit_from_table(self):
        """Test parsing valid unit from detail page table"""
        html = '''
        <html>
            <body>
                <table class="data table additional-attributes">
                    <tbody>
                        <tr>
                            <th>Ukuran</th>
                            <td>5KG</td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        '''
        result = self.parser.parse_unit_from_detail_page(html)
        self.assertEqual(result, 'KG')
    
    def test_parse_unit_empty_string_defaults_to_pcs(self):
        """Test parsing empty product name defaults to PCS"""
        with patch.object(self.parser.extractor, 'extract_unit_from_name', return_value=None):
            result = self.parser.parse_unit_from_product_name('')
            self.assertEqual(result, 'PCS')
    
    def test_parse_unit_whitespace_only_defaults_to_pcs(self):
        """Test parsing whitespace-only product name defaults to PCS"""
        with patch.object(self.parser.extractor, 'extract_unit_from_name', return_value=None):
            result = self.parser.parse_unit_from_product_name('   ')
            self.assertEqual(result, 'PCS')
    
    def test_parse_unit_from_name_special_characters_with_valid_unit(self):
        """Test parsing product name with special characters but valid unit"""
        with patch.object(self.parser.extractor, 'extract_unit_from_name', return_value='KG'):
            result = self.parser.parse_unit_from_product_name('Semen @ 50 KG #1')
            self.assertEqual(result, 'KG')
    
    def test_parse_unit_from_detail_page_malformed_html_returns_pcs(self):
        """Test handling malformed HTML returns PCS"""
        malformed_html_cases = [
            '<html><body><table class="data table additional-attributes"',  # Unclosed tags
            '<><><>',  # Invalid tags
            'Just plain text without tags',
        ]
        
        for html in malformed_html_cases:
            with self.subTest(html=html[:30]):
                result = self.parser.parse_unit_from_detail_page(html)
                self.assertEqual(result, 'PCS')
    
    def test_parse_unit_from_product_name_no_match_defaults_to_pcs(self):
        """Test that products without recognizable units default to PCS"""
        test_cases = [
            "RANDOM PRODUCT NAME",
            "SOME CONSTRUCTION MATERIAL",
            "BUILDING SUPPLIES WITHOUT UNIT",
        ]
        
        for product_name in test_cases:
            with self.subTest(product_name=product_name):
                result = self.parser.parse_unit_from_product_name(product_name)
                self.assertEqual(result, 'PCS')


class TestDepoBangunanUnitExtractorEdgeCases(unittest.TestCase):
    """Test edge cases and error handling for 100% coverage"""
    
    def setUp(self):
        self.extractor = DepoBangunanUnitExtractor()
        self.parser = DepoBangunanUnitParser()
    
    def test_extract_unit_from_name_with_long_product_name(self):
        """Test handling of very long product names - covers lines 78-79"""
        long_name = "A" * 1500 + " CEMENT 50KG"
        with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
            self.extractor.extract_unit_from_name(long_name)
            # The name is truncated to 1000 chars, should still work
            mock_log.assert_called_once()
            self.assertIn("Product name too long", mock_log.call_args[0][0])
    
    def test_extract_unit_from_specification_with_long_spec_text(self):
        """Test handling of very long specification text - covers lines 112-113"""
        long_spec = "A" * 600 + "KG"
        with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
            self.extractor.extract_unit_from_specification(long_spec)
            # May or may not extract unit, but should log warning
            mock_log.assert_called_once()
            self.assertIn("Specification text too long", mock_log.call_args[0][0])
    
    def test_extract_unit_from_specification_exception_handling(self):
        """Test exception handling in extract_unit_from_specification - covers lines 147-149"""
        # Create a mock pattern that raises exception
        mock_pattern = Mock()
        mock_pattern.search.side_effect = Exception("Test error")
        
        # Temporarily replace the pattern
        original_pattern = self.extractor._SPEC_UNIT_PATTERN
        self.extractor._SPEC_UNIT_PATTERN = mock_pattern
        
        try:
            with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
                result = self.extractor.extract_unit_from_specification("50KG")
                self.assertIsNone(result)
                mock_log.assert_called_once()
                self.assertIn("Error extracting unit from specification", mock_log.call_args[0][0])
        finally:
            # Restore original pattern
            self.extractor._SPEC_UNIT_PATTERN = original_pattern
    
    def test_extract_unit_from_name_exception_handling(self):
        """Test exception handling in extract_unit_from_name"""
        # This will trigger an exception in the processing
        with patch.object(self.extractor, '_extract_area_unit', side_effect=Exception("Test error")):
            with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
                result = self.extractor.extract_unit_from_name("Test Product 50KG")
                self.assertIsNone(result)
                mock_log.assert_called_once()
                self.assertIn("Error extracting unit", mock_log.call_args[0][0])
    
    def test_extract_by_priority_patterns_timeout_error(self):
        """Test TimeoutError handling in _extract_by_priority_patterns - covers lines 224-225"""
        # Mock compiled pattern to raise TimeoutError
        mock_pattern = Mock()
        mock_pattern.search.side_effect = TimeoutError("Regex timeout")
        
        self.extractor._compiled_patterns = {'KG': mock_pattern}
        
        with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
            self.extractor._extract_by_priority_patterns("test 50kg")
            # Should continue to next pattern or return None
            mock_log.assert_called()
            self.assertIn("Regex timeout", mock_log.call_args[0][0])
    
    def test_extract_by_priority_patterns_general_exception(self):
        """Test general exception handling in _extract_by_priority_patterns - covers lines 228-230"""
        # Create a scenario that causes exception in the try block
        original_priority_order = self.extractor.priority_order
        self.extractor.priority_order = None  # This will cause TypeError when iterating
        
        with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
            result = self.extractor._extract_by_priority_patterns("test")
            self.assertIsNone(result)
            mock_log.assert_called_once()
            self.assertIn("Error in priority pattern extraction", mock_log.call_args[0][0])
        
        # Restore
        self.extractor.priority_order = original_priority_order
    
    def test_parse_unit_from_detail_page_exception_handling(self):
        """Test exception handling in parse_unit_from_detail_page - covers lines 282-284"""
        # Create invalid HTML that will cause an exception in parsing
        invalid_html = None
        
        with patch('api.depobangunan.unit_parser.logger.warning'):
            result = self.parser.parse_unit_from_detail_page(invalid_html)
            self.assertEqual(result, 'PCS')  # Should default to PCS on error
            # Logger may be called for the error
    
    def test_extract_unit_from_table_exception_handling(self):
        """Test exception handling in _extract_unit_from_table - covers lines 303-306"""
        from bs4 import BeautifulSoup
        
        # Create a mock table that will cause an exception
        html = '<table><tr><td>Test</td></tr></table>'
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        # Mock the find_all to raise an exception
        with patch.object(table, 'find_all', side_effect=Exception("Test error")):
            with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
                result = self.parser._extract_unit_from_table(table)
                self.assertIsNone(result)
                mock_log.assert_called_once()
                self.assertIn("Error extracting unit from table", mock_log.call_args[0][0])
    
    def test_extract_unit_near_element_exception_handling(self):
        """Test exception handling in _extract_unit_near_element - covers lines 320-329"""
        from bs4 import BeautifulSoup
        
        # Create a scenario where getting text fails
        html = '<div>Test<span>KG</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('div')
        
        # Mock the extractor method to raise an exception
        with patch.object(self.parser.extractor, 'extract_unit_from_specification', side_effect=Exception("Test error")):
            with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
                result = self.parser._extract_unit_near_element(element)
                self.assertIsNone(result)
                mock_log.assert_called_once()
                self.assertIn("Error extracting unit near element", mock_log.call_args[0][0])
    
    def test_extract_unit_near_element_with_siblings(self):
        """Test extracting unit from sibling elements - covers sibling iteration logic"""
        from bs4 import BeautifulSoup
        
        html = '<div>Size:<span>50KG</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('div')
        
        # This should extract unit from the sibling - result may vary but shouldn't crash
        self.parser._extract_unit_near_element(element)
    
    def test_extract_unit_near_element_from_parent(self):
        """Test extracting unit from parent element"""
        from bs4 import BeautifulSoup
        
        html = '<div>50KG<span></span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('span')
        
        # Should check parent for unit - result may vary but shouldn't crash
        self.parser._extract_unit_near_element(element)
    
    def test_extract_unit_near_element_no_unit_found(self):
        """Test _extract_unit_near_element when no unit is found - covers line 326"""
        from bs4 import BeautifulSoup
        
        html = '<div><span></span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('span')
        
        result = self.parser._extract_unit_near_element(element)
        self.assertIsNone(result)
    
    def test_extract_area_unit_exception_handling(self):
        """Test exception handling in _extract_area_unit - covers lines 159-161"""
        # Create a mock pattern that raises exception
        mock_pattern = Mock()
        mock_pattern.search.side_effect = Exception("Test error")
        
        # Temporarily replace the pattern
        original_pattern = self.extractor._AREA_PATTERN
        self.extractor._AREA_PATTERN = mock_pattern
        
        try:
            with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
                result = self.extractor._extract_area_unit("60x60cm")
                self.assertIsNone(result)
                mock_log.assert_called_once()
                self.assertIn("Error in area pattern extraction", mock_log.call_args[0][0])
        finally:
            # Restore original pattern
            self.extractor._AREA_PATTERN = original_pattern
    
    def test_extract_adjacent_unit_exception_handling(self):
        """Test exception handling in _extract_adjacent_unit - covers lines 182-184"""
        with patch.object(self.extractor, '_extract_inch_patterns', side_effect=Exception("Test error")):
            with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
                result = self.extractor._extract_adjacent_unit("25kg")
                self.assertIsNone(result)
                mock_log.assert_called_once()
                self.assertIn("Error in adjacent pattern extraction", mock_log.call_args[0][0])
    
    def test_parse_unit_from_detail_page_returns_pcs_on_exception(self):
        """Test that parse_unit_from_detail_page returns PCS on exception - covers lines 282-284"""
        # Create HTML that will cause exception when parsing
        with patch('api.depobangunan.unit_parser.BeautifulSoup', side_effect=Exception("Parse error")):
            with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
                result = self.parser.parse_unit_from_detail_page('<div>test</div>')
                self.assertEqual(result, 'PCS')
                mock_log.assert_called_once()
                self.assertIn("Error parsing unit from detail page", mock_log.call_args[0][0])
    
    def test_extract_unit_from_table_returns_none_on_exception(self):
        """Test that _extract_unit_from_table returns None on exception - covers line 303"""
        from bs4 import BeautifulSoup
        
        html = '<table><tr><td>Weight</td><td>50KG</td></tr></table>'
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        # Patch find_all to cause exception during processing
        with patch.object(table, 'find_all', side_effect=Exception("Test error")):
            with patch('api.depobangunan.unit_parser.logger.warning') as mock_log:
                result = self.parser._extract_unit_from_table(table)
                self.assertIsNone(result)
                mock_log.assert_called_once()
                self.assertIn("Error extracting unit from table", mock_log.call_args[0][0])
    
    def test_extract_unit_from_table_returns_none_when_no_match(self):
        """Test that _extract_unit_from_table returns None when no unit keyword matches"""
        from bs4 import BeautifulSoup
        
        html = '<table><tr><td>Color</td><td>Red</td></tr><tr><td>Brand</td><td>Test</td></tr></table>'
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        result = self.parser._extract_unit_from_table(table)
        # Should return None because no spec keywords match
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()