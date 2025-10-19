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
        self.assertIsNone(result)
    
    def test_parse_unit_from_detail_page_with_none_html(self):
        """Test parsing unit from None HTML content."""
        result = self.parser.parse_unit_from_detail_page(None)
        self.assertIsNone(result)


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


if __name__ == '__main__':
    unittest.main()