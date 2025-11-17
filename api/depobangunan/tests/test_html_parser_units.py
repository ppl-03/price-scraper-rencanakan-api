import unittest
from unittest.mock import Mock, patch
from api.depobangunan.html_parser import DepoHtmlParser
from api.depobangunan.price_cleaner import DepoPriceCleaner
from api.depobangunan.unit_parser import DepoBangunanUnitParser
from api.interfaces import Product


class TestDepoHtmlParserWithUnits(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_price_cleaner = Mock(spec=DepoPriceCleaner)
        self.mock_unit_parser = Mock(spec=DepoBangunanUnitParser)
        self.parser = DepoHtmlParser(
            price_cleaner=self.mock_price_cleaner,
            unit_parser=self.mock_unit_parser
        )
    
    def test_extract_product_from_item_includes_unit(self):
        """Test that product extraction includes unit information."""
        # Mock HTML item
        mock_item = Mock()
        
        # Mock product name extraction
        mock_name_element = Mock()
        mock_link = Mock()
        mock_link.get_text.return_value = "MAGIX WIN TILE GROUT WHITE 1KG"
        mock_name_element.find.return_value = mock_link
        mock_item.find.return_value = mock_name_element
        
        # Mock URL extraction - return None for simplicity
        mock_item.find.return_value.find.return_value.get.return_value = "https://example.com/product"
        
        # Mock price extraction
        mock_price_element = Mock()
        mock_price_element.get_text.return_value = "Rp 8,499"
        
        # Configure the mock to return different elements based on selector
        def mock_find_side_effect(*args, **kwargs):
            if 'product name' in str(kwargs.get('class_', '')):
                return mock_name_element
            elif 'price' in str(kwargs.get('class_', '')):
                return mock_price_element
            return None
        
        mock_item.find.side_effect = mock_find_side_effect
        
        # Mock price cleaner
        self.mock_price_cleaner.clean_price.return_value = 8499
        self.mock_price_cleaner.is_valid_price.return_value = True
        
        # Mock unit parser
        self.mock_unit_parser.parse_unit_from_product_name.return_value = "KG"
        
        # Test the extraction
        result = self.parser._extract_product_from_item(mock_item)
        
        # Assertions
        self.assertIsInstance(result, Product)
        self.assertEqual(result.name, "MAGIX WIN TILE GROUT WHITE 1KG")
        self.assertEqual(result.price, 8499)
        self.assertEqual(result.unit, "KG")
        self.mock_unit_parser.parse_unit_from_product_name.assert_called_once_with("MAGIX WIN TILE GROUT WHITE 1KG")
    
    def test_extract_product_from_item_with_no_unit_found(self):
        """Test product extraction when no unit is found."""
        # Mock HTML item
        mock_item = Mock()
        
        # Mock product name extraction
        mock_name_element = Mock()
        mock_link = Mock()
        mock_link.get_text.return_value = "RANDOM PRODUCT"
        mock_name_element.find.return_value = mock_link
        
        # Configure mock
        def mock_find_side_effect(*args, **kwargs):
            if 'product name' in str(kwargs.get('class_', '')):
                return mock_name_element
            return Mock()
        
        mock_item.find.side_effect = mock_find_side_effect
        
        # Mock price cleaner
        self.mock_price_cleaner.clean_price.return_value = 5000
        self.mock_price_cleaner.is_valid_price.return_value = True
        
        # Mock unit parser returns None
        self.mock_unit_parser.parse_unit_from_product_name.return_value = None
        
        # Test the extraction
        result = self.parser._extract_product_from_item(mock_item)
        
        # Assertions
        self.assertIsInstance(result, Product)
        self.assertEqual(result.name, "RANDOM PRODUCT")
        self.assertEqual(result.price, 5000)
        self.assertIsNone(result.unit)
    
    def test_extract_product_from_item_returns_none_for_invalid_price(self):
        """Test that invalid price returns None even if unit is found."""
        # Mock HTML item
        mock_item = Mock()
        
        # Mock product name extraction
        mock_name_element = Mock()
        mock_link = Mock()
        mock_link.get_text.return_value = "PRODUCT WITH INVALID PRICE"
        mock_name_element.find.return_value = mock_name_element
        
        # Configure mock for price extraction failure
        mock_item.find.return_value = mock_name_element
        mock_item.find_all.return_value = []  # For text search
        
        # Mock price cleaner with invalid price
        self.mock_price_cleaner.clean_price.return_value = None
        self.mock_price_cleaner.is_valid_price.return_value = False
        
        # Test the extraction
        result = self.parser._extract_product_from_item(mock_item)
        
        # Assertions
        self.assertIsNone(result)
        # Unit parser should not be called if price is invalid
        self.mock_unit_parser.parse_unit_from_product_name.assert_not_called()


class TestDepoHtmlParserUnitParserIntegration(unittest.TestCase):
    """Integration tests for HTML parser with real unit parser."""
    
    def setUp(self):
        """Set up test fixtures with real unit parser."""
        self.price_cleaner = Mock(spec=DepoPriceCleaner)
        self.parser = DepoHtmlParser(price_cleaner=self.price_cleaner)
        # Using real unit parser for integration testing
    
    def test_real_unit_extraction_from_product_names(self):
        """Test unit extraction with real unit parser."""
        test_cases = [
            ("MAGIX WIN TILE GROUT WHITE 1KG", "KG"),
            ("PYLOX SOLID 102 WHITE 300CC", "CC"),
            ('DBS FILAMENT PAINT BRUSH, 3"', "INCH"),
            ("UNIK SPONGE (ANGKA 8)", "PCS"),
        ]
        
        for product_name, expected_unit in test_cases:
            with self.subTest(product_name=product_name):
                result = self.parser.unit_parser.parse_unit_from_product_name(product_name)
                self.assertEqual(result, expected_unit)


if __name__ == '__main__':
    unittest.main()