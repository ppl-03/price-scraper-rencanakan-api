import unittest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup

from api.mitra10.location_parser import Mitra10LocationParser, SelectorConfig
from api.interfaces import HtmlParserError


class TestSelectorConfig(unittest.TestCase):
    
    def test_selector_config_initialization(self):
        """Test SelectorConfig default values"""
        config = SelectorConfig()
        
        self.assertEqual(config.dropdown_container, 'div[role="presentation"].MuiPopover-root')
        self.assertEqual(config.location_list, 'ul.MuiList-root')
        self.assertEqual(config.location_item, 'li.MuiButtonBase-root')
        self.assertEqual(config.location_text, 'span')


class TestMitra10LocationParser(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = Mitra10LocationParser()
        self.custom_config = SelectorConfig()
        self.custom_config.dropdown_container = 'div.custom-dropdown'
        self.custom_config.location_list = 'ul.custom-list'
        self.custom_config.location_item = 'li.custom-item'
        self.custom_config.location_text = 'span.custom-text'
    
    def test_parser_initialization_default_config(self):
        """Test parser initialization with default config"""
        parser = Mitra10LocationParser()
        
        self.assertIsInstance(parser._selectors, SelectorConfig)
        self.assertEqual(parser.MITRA10_PREFIX, "MITRA10 ")
    
    def test_parser_initialization_custom_config(self):
        """Test parser initialization with custom config"""
        parser = Mitra10LocationParser(self.custom_config)
        
        self.assertEqual(parser._selectors, self.custom_config)
        self.assertEqual(parser._selectors.dropdown_container, 'div.custom-dropdown')
    
    def test_parse_locations_empty_html(self):
        """Test parsing with empty HTML content"""
        result = self.parser.parse_locations("")
        self.assertEqual(result, [])
        
        result = self.parser.parse_locations(None)
        self.assertEqual(result, [])
    
    def test_parse_locations_valid_html(self):
        """Test parsing with valid HTML content"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>MITRA10 Jakarta Selatan</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>MITRA10 Bandung</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>MITRA10 Surabaya</span>
                </li>
            </ul>
        </div>
        '''
        
        result = self.parser.parse_locations(html_content)
        
        expected = ['Jakarta Selatan', 'Bandung', 'Surabaya']
        self.assertEqual(result, expected)
    
    def test_parse_locations_without_mitra10_prefix(self):
        """Test parsing locations without MITRA10 prefix"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>Jakarta Utara</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>Bekasi</span>
                </li>
            </ul>
        </div>
        '''
        
        result = self.parser.parse_locations(html_content)
        
        expected = ['Jakarta Utara', 'Bekasi']
        self.assertEqual(result, expected)
    
    def test_parse_locations_no_dropdown_container(self):
        """Test parsing when dropdown container is not found"""
        html_content = '''
        <div class="other-container">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>Jakarta</span>
                </li>
            </ul>
        </div>
        '''
        
        with patch('api.mitra10.location_parser.logger') as mock_logger:
            result = self.parser.parse_locations(html_content)
            
            self.assertEqual(result, [])
            mock_logger.warning.assert_called_once()
    
    def test_parse_locations_no_location_list(self):
        """Test parsing when location list is not found"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <div class="other-list">
                <li class="MuiButtonBase-root">
                    <span>Jakarta</span>
                </li>
            </div>
        </div>
        '''
        
        with patch('api.mitra10.location_parser.logger') as mock_logger:
            result = self.parser.parse_locations(html_content)
            
            self.assertEqual(result, [])
            mock_logger.warning.assert_called_once()
    
    def test_parse_locations_no_location_items(self):
        """Test parsing when location items are not found"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <div class="other-item">
                    <span>Jakarta</span>
                </div>
            </ul>
        </div>
        '''
        
        with patch('api.mitra10.location_parser.logger') as mock_logger:
            result = self.parser.parse_locations(html_content)
            
            self.assertEqual(result, [])
            mock_logger.warning.assert_called_once()
    
    def test_parse_locations_items_without_span(self):
        """Test parsing location items without span elements"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <div>Jakarta</div>
                </li>
                <li class="MuiButtonBase-root">
                    <span>Bandung</span>
                </li>
            </ul>
        </div>
        '''
        
        result = self.parser.parse_locations(html_content)
        
        # Only items with span elements should be included
        expected = ['Bandung']
        self.assertEqual(result, expected)
    
    def test_parse_locations_with_invalid_names(self):
        """Test parsing with invalid location names"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>Jakarta Selatan</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>AB</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>Select Location</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>Bandung</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>Choose Option</span>
                </li>
            </ul>
        </div>
        '''
        
        result = self.parser.parse_locations(html_content)
        
        # Only valid location names should be included
        expected = ['Jakarta Selatan', 'Bandung']
        self.assertEqual(result, expected)
    
    def test_parse_with_lxml_success(self):
        """Test _parse_with_lxml method directly"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>Jakarta</span>
                </li>
            </ul>
        </div>
        '''
        
        result = self.parser._parse_with_lxml(html_content)
        
        expected = ['Jakarta']
        self.assertEqual(result, expected)
    
    def test_parse_with_fallback_success(self):
        """Test _parse_with_fallback method when it succeeds"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>Jakarta</span>
                </li>
            </ul>
        </div>
        '''
        
        original_error = Exception("lxml failed")
        result = self.parser._parse_with_fallback(html_content, original_error)
        
        expected = ['Jakarta']
        self.assertEqual(result, expected)
    
    def test_parse_with_fallback_raises_error(self):
        """Test _parse_with_fallback method when it fails"""
        invalid_html = '<invalid><xml>'
        original_error = Exception("lxml failed")
        
        with patch('api.mitra10.location_parser.BeautifulSoup') as mock_soup:
            mock_soup.side_effect = Exception("html.parser also failed")
            
            with self.assertRaises(HtmlParserError) as context:
                self.parser._parse_with_fallback(invalid_html, original_error)
            
            self.assertIn("Failed to parse location HTML: lxml failed", str(context.exception))
    
    def test_lxml_parser_fallback_flow(self):
        """Test that lxml failure triggers fallback to html.parser"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>Jakarta</span>
                </li>
            </ul>
        </div>
        '''
        
        with patch.object(self.parser, '_parse_with_lxml') as mock_lxml:
            with patch.object(self.parser, '_parse_with_fallback') as mock_fallback:
                mock_lxml.side_effect = Exception("lxml failed")
                mock_fallback.return_value = ['Jakarta']
                
                result = self.parser.parse_locations(html_content)
                
                mock_lxml.assert_called_once_with(html_content)
                mock_fallback.assert_called_once()
                self.assertEqual(result, ['Jakarta'])
    
    def test_is_valid_location_name_valid_names(self):
        """Test _is_valid_location_name with valid names"""
        valid_names = [
            'Jakarta Selatan',
            'Bandung Utara',
            'Surabaya',
            'Tangerang City Mall',
            'Bekasi Junction'
        ]
        
        for name in valid_names:
            with self.subTest(name=name):
                self.assertTrue(self.parser._is_valid_location_name(name))
    
    def test_is_valid_location_name_invalid_names(self):
        """Test _is_valid_location_name with invalid names"""
        invalid_names = [
            '',  # Empty string
            '  ',  # Whitespace only
            'AB',  # Too short
            'Select Location',  # Contains 'select'
            'Choose Store',  # Contains 'choose'
            'Menu Options',  # Contains 'menu'
            'Close Window',  # Contains 'close'
            'Search Here',  # Contains 'search'
            'Filter Results',  # Contains 'filter'
            'Water Dispenser',  # Contains 'dispenser'
            'Portable Device',  # Contains 'portable'
            'Product Category',  # Contains 'category'
            'Brand Name',  # Contains 'brand'
            'Promo Offers'  # Contains 'promo'
        ]
        
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(self.parser._is_valid_location_name(name))
    
    def test_get_selectors_methods(self):
        """Test selector getter methods"""
        parser = Mitra10LocationParser(self.custom_config)
        
        self.assertEqual(parser.get_dropdown_selector(), 'div.custom-dropdown')
        self.assertEqual(parser.get_location_list_selector(), 'ul.custom-list')
        self.assertEqual(parser.get_location_item_selector(), 'li.custom-item')
    
    def test_extract_locations_with_custom_config(self):
        """Test _extract_locations with custom selector config"""
        parser = Mitra10LocationParser(self.custom_config)
        
        html_content = '''
        <div class="custom-dropdown">
            <ul class="custom-list">
                <li class="custom-item">
                    <span class="custom-text">Jakarta</span>
                </li>
                <li class="custom-item">
                    <span class="custom-text">Bandung</span>
                </li>
            </ul>
        </div>
        '''
        
        soup = BeautifulSoup(html_content, 'html.parser')
        result = parser._extract_locations(soup)
        
        expected = ['Jakarta', 'Bandung']
        self.assertEqual(result, expected)
    
    def test_mitra10_prefix_removal(self):
        """Test MITRA10 prefix removal from location names"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>MITRA10 Jakarta Selatan</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>MITRA10 Bandung Central</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>Surabaya</span>
                </li>
            </ul>
        </div>
        '''
        
        result = self.parser.parse_locations(html_content)
        
        expected = ['Jakarta Selatan', 'Bandung Central', 'Surabaya']
        self.assertEqual(result, expected)
    
    def test_location_text_stripping(self):
        """Test that location text is properly stripped of whitespace"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>  Jakarta Selatan  </span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>
                        Bandung
                    </span>
                </li>
            </ul>
        </div>
        '''
        
        result = self.parser.parse_locations(html_content)
        
        expected = ['Jakarta Selatan', 'Bandung']
        self.assertEqual(result, expected)
    
    def test_logging_behavior(self):
        """Test that appropriate logging occurs during parsing"""
        html_content = '''
        <div role="presentation" class="MuiPopover-root">
            <ul class="MuiList-root">
                <li class="MuiButtonBase-root">
                    <span>Jakarta</span>
                </li>
                <li class="MuiButtonBase-root">
                    <span>Bandung</span>
                </li>
            </ul>
        </div>
        '''
        
        with patch('api.mitra10.location_parser.logger') as mock_logger:
            result = self.parser.parse_locations(html_content)
            
            # Verify logging calls were made
            mock_logger.info.assert_any_call("Found dropdown container with exact selector")
            mock_logger.info.assert_any_call("Found location list within container")
            mock_logger.info.assert_any_call("Found 2 location items")
            mock_logger.info.assert_any_call("Successfully extracted 2 valid locations")
            
            self.assertEqual(result, ['Jakarta', 'Bandung'])


if __name__ == '__main__':
    unittest.main()
