import unittest
from unittest.mock import Mock, patch, MagicMock
from api.depobangunan.scraper import DepoPriceScraper
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, Product, ScrapingResult


class TestDepoPriceScraperWithUnits(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_http_client = Mock(spec=IHttpClient)
        self.mock_url_builder = Mock(spec=IUrlBuilder)
        self.mock_html_parser = Mock(spec=IHtmlParser)
        
        self.scraper = DepoPriceScraper(
            http_client=self.mock_http_client,
            url_builder=self.mock_url_builder,
            html_parser=self.mock_html_parser
        )
    
    @patch('api.depobangunan.scraper.BasePriceScraper.scrape_products')
    def test_scrape_products_enhances_products_without_units(self, mock_super_scrape):
        """Test that products without units are enhanced with detail page information."""
        # Mock the base scraper result
        products = [
            Product(name="Product with unit", price=1000, url="https://example.com/1", unit="KG"),
            Product(name="Product without unit", price=2000, url="https://example.com/2", unit=None),
        ]
        mock_result = ScrapingResult(products=products, success=True)
        mock_super_scrape.return_value = mock_result
        
        # Mock detail page HTML
        detail_html = "<table><tr><td>Ukuran</td><td>1KG</td></tr></table>"
        self.mock_http_client.get.return_value = detail_html
        
        # Mock unit parser to return a unit from detail page
        with patch.object(self.scraper.unit_parser, 'parse_unit_from_detail_page') as mock_parse_detail:
            mock_parse_detail.return_value = "KG"
            
            # Execute
            result = self.scraper.scrape_products("test", sort_by_price=True, page=0)
            
            # Assertions
            self.assertTrue(result.success)
            self.assertEqual(len(result.products), 2)
            
            # First product should remain unchanged (already has unit)
            self.assertEqual(result.products[0].unit, "KG")
            
            # Second product should be enhanced with unit from detail page
            self.assertEqual(result.products[1].unit, "KG")
            
            # Verify detail page was fetched
            self.mock_http_client.get.assert_called_once_with("https://example.com/2", timeout=60)
            mock_parse_detail.assert_called_once_with(detail_html)
    
    @patch('api.depobangunan.scraper.BasePriceScraper.scrape_products')
    def test_scrape_products_handles_detail_page_fetch_failure(self, mock_super_scrape):
        # Mock the base scraper result with product without unit
        products = [
            Product(name="Product without unit", price=2000, url="https://example.com/2", unit=None),
        ]
        mock_result = ScrapingResult(products=products, success=True)
        mock_super_scrape.return_value = mock_result
        
        # Mock HTTP client to raise exception
        self.mock_http_client.get.side_effect = Exception("Network error")
        
        # Execute
        result = self.scraper.scrape_products("test", sort_by_price=True, page=0)
        
        # Assertions
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 1)
        
        # Product should remain unchanged (unit still None)
        self.assertIsNone(result.products[0].unit)
    
    @patch('api.depobangunan.scraper.BasePriceScraper.scrape_products')
    def test_scrape_products_handles_product_without_url(self, mock_super_scrape):
        # Mock the base scraper result with product without URL
        products = [
            Product(name="Product without URL", price=2000, url=None, unit=None),
        ]
        mock_result = ScrapingResult(products=products, success=True)
        mock_super_scrape.return_value = mock_result
        
        # Execute
        result = self.scraper.scrape_products("test", sort_by_price=True, page=0)
        
        # Assertions
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 1)
        
        # Product should remain unchanged
        self.assertIsNone(result.products[0].unit)
        
        # HTTP client should not be called
        self.mock_http_client.get.assert_not_called()
    
    @patch('api.depobangunan.scraper.BasePriceScraper.scrape_products')
    def test_scrape_products_returns_original_result_on_base_failure(self, mock_super_scrape):
        # Mock base scraper failure
        mock_result = ScrapingResult(products=[], success=False, error_message="Base scraper error")
        mock_super_scrape.return_value = mock_result
        
        # Execute
        result = self.scraper.scrape_products("test", sort_by_price=True, page=0)
        
        # Assertions
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Base scraper error")
        self.assertEqual(len(result.products), 0)
        
        # No enhancement should be attempted
        self.mock_http_client.get.assert_not_called()
    
    def test_enhance_product_with_unit_from_detail_page_success(self):
        # Create test product
        product = Product(name="Test Product", price=1000, url="https://example.com/test", unit=None)
        
        # Mock detail page HTML
        detail_html = "<table><tr><td>Ukuran</td><td>2KG</td></tr></table>"
        self.mock_http_client.get.return_value = detail_html
        
        # Mock unit parser
        with patch.object(self.scraper.unit_parser, 'parse_unit_from_detail_page') as mock_parse_detail:
            mock_parse_detail.return_value = "KG"
            
            # Execute
            result = self.scraper._enhance_product_with_unit_from_detail_page(product)
            
            # Assertions
            self.assertEqual(result.name, "Test Product")
            self.assertEqual(result.price, 1000)
            self.assertEqual(result.url, "https://example.com/test")
            self.assertEqual(result.unit, "KG")
    
    def test_enhance_product_with_unit_from_detail_page_no_unit_found(self):
        # Create test product
        product = Product(name="Test Product", price=1000, url="https://example.com/test", unit=None)
        
        # Mock detail page HTML
        detail_html = "<html><body>No specifications</body></html>"
        self.mock_http_client.get.return_value = detail_html
        
        # Mock unit parser to return None
        with patch.object(self.scraper.unit_parser, 'parse_unit_from_detail_page') as mock_parse_detail:
            mock_parse_detail.return_value = None
            
            # Execute
            result = self.scraper._enhance_product_with_unit_from_detail_page(product)
            
            # Assertions - product should remain unchanged
            self.assertEqual(result.name, "Test Product")
            self.assertEqual(result.price, 1000)
            self.assertEqual(result.url, "https://example.com/test")
            self.assertIsNone(result.unit)
    
    def test_enhance_product_with_unit_from_detail_page_no_url(self):
        # Create test product without URL
        product = Product(name="Test Product", price=1000, url=None, unit=None)
        
        # Execute
        result = self.scraper._enhance_product_with_unit_from_detail_page(product)
        
        # Assertions - product should remain unchanged
        self.assertEqual(result, product)
        
        # HTTP client should not be called
        self.mock_http_client.get.assert_not_called()


class TestDepoPriceScraperIntegration(unittest.TestCase):
    """Integration tests for DepoPriceScraper with real components."""
    
    def setUp(self):
        """Set up test fixtures with real components."""
        from api.depobangunan.factory import create_depo_scraper
        # We'll use the factory but mock the HTTP calls
    
    def test_extract_adjacent_unit_various_patterns(self):
        """Test _extract_adjacent_unit with various adjacent patterns"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        test_cases = [
            ("cat 25kg", "KG"),
            ("paku 500g", "G"), 
            ("air 1l", "L"),
            ("tube 3ml", "ML"),
            ("pipe 4\"", "INCH"),
            ("wire 5'", "FEET"),
            ("cable 3 feet", "FEET"),
            ("rod 2 inch", "INCH"),
            ("no adjacent unit", None),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = extractor._extract_adjacent_unit(text.lower())
                self.assertEqual(result, expected)

    def test_extract_area_unit_various_patterns(self):
        """Test _extract_area_unit with various area patterns"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        test_cases = [
            ("keramik 60x60cm", "CM²"),
            ("tiles 30 x 30 mm", "MM²"), 
            ("plywood 120x240 m", "M²"),
            ("panel 80×120 cm", "CM²"),
            ("no dimensions here", None),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = extractor._extract_area_unit(text.lower())
                self.assertEqual(result, expected)

    def test_should_default_to_pcs_with_indicators(self):
        """Test _should_default_to_pcs with various indicators"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        pcs_items = [
            "sponge pembersih",
            "brush cat", 
            "kuas lukis",
            "sikat gigi",
            "saklar lampu",
            "stop kontak",
            "handle pintu",
            "pegangan lemari",
        ]
        
        for item in pcs_items:
            with self.subTest(item=item):
                result = extractor._should_default_to_pcs(item.lower())
                self.assertTrue(result)

    def test_extract_unit_from_specification_edge_cases(self):
        """Test extract_unit_from_specification with edge cases"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        test_cases = [
            (None, None),
            ("", None),
            ("   ", None),
            (123, None),
            ("VERYLONGUNITNAMETHATSHOULDRETURNNONEBECAUSEITSTOOLTOOLONG", None),
        ]
        
        for spec, expected in test_cases:
            with self.subTest(spec=spec):
                result = extractor.extract_unit_from_specification(spec)
                self.assertEqual(result, expected)

    def test_extract_unit_from_specification_with_various_mappings(self):
        """Test unit mapping in extract_unit_from_specification"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        test_cases = [
            ("KILOGRAM", "KG"),
            ("GRAM", "G"),
            ("LITER", "L"),
            ("MILLILITER", "ML"),
            ("METER", "M"),
            ("CENTIMETER", "CM"),
            ("MILLIMETER", "MM"),
            ("PIECES", "PCS"),
            ("SET", "SET"),
            ("PACK", "PACK"),
            ("BOX", "BOX"),
            ("ROLL", "ROLL"),
            ("SHEET", "SHEET"),
            ("BATANG", "BATANG"),
            ("UNIT", "UNIT"),
        ]
        
        for spec_text, expected in test_cases:
            with self.subTest(spec_text=spec_text):
                result = extractor.extract_unit_from_specification(spec_text)
                self.assertEqual(result, expected)

    def test_extract_by_priority_patterns_with_exception(self):
        """Test exception handling in _extract_by_priority_patterns"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        with patch('re.search', side_effect=Exception("Regex error")):
            with patch('api.depobangunan.unit_parser.logger') as mock_logger:
                result = extractor._extract_by_priority_patterns("test text")
                self.assertIsNone(result)
                mock_logger.warning.assert_called_once()

    def test_extract_adjacent_unit_with_exception(self):
        """Test _extract_adjacent_unit exception handling"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        with patch('re.finditer', side_effect=Exception("Regex error")):
            with patch('api.depobangunan.unit_parser.logger') as mock_logger:
                result = extractor._extract_adjacent_unit("test")
                self.assertIsNone(result)
                mock_logger.warning.assert_called_once()

    def test_extract_area_unit_with_exception(self):
        """Test _extract_area_unit exception handling"""  
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        with patch('re.search', side_effect=Exception("Regex error")):
            with patch('api.depobangunan.unit_parser.logger') as mock_logger:
                result = extractor._extract_area_unit("test")
                self.assertIsNone(result)
                mock_logger.warning.assert_called_once()

    def test_extract_unit_from_specification_with_exception(self):
        """Test exception handling in extract_unit_from_specification"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        with patch('re.search', side_effect=Exception("Regex error")):
            with patch('api.depobangunan.unit_parser.logger') as mock_logger:
                result = extractor.extract_unit_from_specification("1KG")
                self.assertIsNone(result)
                mock_logger.warning.assert_called_once()

    def test_extract_unit_from_name_with_exception(self):
        """Test exception handling in extract_unit_from_name"""
        from api.depobangunan.unit_parser import DepoBangunanUnitExtractor
        extractor = DepoBangunanUnitExtractor()
        
        # Mock all the internal methods to raise exceptions
        with patch.object(extractor, '_extract_by_priority_patterns', side_effect=Exception("Test error")):
            with patch.object(extractor, '_extract_adjacent_unit', side_effect=Exception("Test error")):
                with patch.object(extractor, '_extract_area_unit', side_effect=Exception("Test error")):
                    with patch('api.depobangunan.unit_parser.logger') as mock_logger:
                        result = extractor.extract_unit_from_name("random text without unit")
                        self.assertIsNone(result)
                        mock_logger.warning.assert_called()

    def test_unit_parser_from_detail_page_invalid_input(self):
        """Test parse_unit_from_detail_page with invalid inputs"""
        from api.depobangunan.unit_parser import DepoBangunanUnitParser
        parser = DepoBangunanUnitParser()
        
        test_cases = [None, "", "   ", 123, []]
        
        for invalid_html in test_cases:
            with self.subTest(html=invalid_html):
                result = parser.parse_unit_from_detail_page(invalid_html)
                self.assertEqual(result, 'PCS')  # Now defaults to PCS instead of None

    def test_unit_parser_initialization_properties(self):
        """Test that parser initializes with correct properties"""
        from api.depobangunan.unit_parser import DepoBangunanUnitParser
        parser = DepoBangunanUnitParser()
        
        self.assertIsNotNone(parser.extractor)
        self.assertIsInstance(parser.spec_keywords, list)
        self.assertIn('ukuran', parser.spec_keywords)
        self.assertIn('size', parser.spec_keywords)

    def test_parse_unit_from_product_name_delegation(self):
        """Test that parse_unit_from_product_name delegates to extractor"""
        from api.depobangunan.unit_parser import DepoBangunanUnitParser
        parser = DepoBangunanUnitParser()
        
        with patch.object(parser.extractor, 'extract_unit_from_name', return_value='KG') as mock_extract:
            result = parser.parse_unit_from_product_name("Cat Air 5KG")
            
            mock_extract.assert_called_once_with("Cat Air 5KG")
            self.assertEqual(result, 'KG')


if __name__ == '__main__':
    unittest.main()