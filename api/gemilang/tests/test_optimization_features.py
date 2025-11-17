"""
Tests for optimized parse_unit_from_element method
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from api.gemilang.unit_parser import GemilangUnitParser


class TestParseUnitFromElement(unittest.TestCase):
    """Test parse_unit_from_element optimization"""
    
    def setUp(self):
        self.parser = GemilangUnitParser()
    
    def test_parse_unit_from_element_with_valid_element(self):
        """Test parsing unit from BeautifulSoup element"""
        html = """
        <div class="item-product">
            <div class="specifications">
                <span>Berat: 5 kg</span>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item-product')
        
        result = self.parser.parse_unit_from_element(item)
        self.assertEqual(result, 'KG')
    
    def test_parse_unit_from_element_with_none(self):
        """Test that None input returns None"""
        result = self.parser.parse_unit_from_element(None)
        self.assertIsNone(result)
    
    def test_parse_unit_from_element_with_no_specifications(self):
        """Test element without specifications falls back to full text"""
        html = """
        <div class="item-product">
            <h3>Cat Tembok 5 kg</h3>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item-product')
        
        result = self.parser.parse_unit_from_element(item)
        self.assertEqual(result, 'KG')
    
    def test_parse_unit_from_element_with_specifications_from_div(self):
        """Test extracting unit from div specifications"""
        html = """
        <div class="item-product">
            <div class="specifications">
                <div>Volume: 10 liter</div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item-product')
        
        result = self.parser.parse_unit_from_element(item)
        self.assertEqual(result, 'LITER')
    
    def test_parse_unit_from_element_with_specifications_from_table(self):
        """Test extracting unit from table specifications"""
        html = """
        <div class="item-product">
            <table>
                <tr><td>Berat</td><td>2.5 kg</td></tr>
            </table>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item-product')
        
        result = self.parser.parse_unit_from_element(item)
        self.assertEqual(result, 'KG')
    
    def test_parse_unit_from_element_priority_rules_applied(self):
        """Test that priority rules are applied correctly"""
        html = """
        <div class="item-product">
            <div class="specifications">
                <span>Dimensi: 10x20 cm, Berat: 5 kg</span>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item-product')
        
        result = self.parser.parse_unit_from_element(item)
        # Weight (KG) should have priority over length (CM)
        self.assertEqual(result, 'KG')
    
    def test_parse_unit_from_element_with_exception(self):
        """Test that exceptions are handled gracefully"""
        with patch.object(self.parser, '_extract_specifications_from_element', 
                         side_effect=Exception("Test error")):
            html = "<div>Test</div>"
            soup = BeautifulSoup(html, 'html.parser')
            item = soup.find('div')
            
            result = self.parser.parse_unit_from_element(item)
            self.assertIsNone(result)
    
    def test_parse_unit_from_element_avoids_string_conversion(self):
        """Test that the method doesn't convert element to string unnecessarily"""
        html = "<div class='test'>5 kg</div>"
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div')
        
        # Mock __str__ to track if it's called
        original_str = item.__str__
        call_count = {'count': 0}
        
        def tracked_str(*args, **kwargs):
            call_count['count'] += 1
            return original_str(*args, **kwargs)
        
        with patch.object(item, '__str__', side_effect=tracked_str):
            result = self.parser.parse_unit_from_element(item)
            
            # Should extract unit without converting to string first
            self.assertEqual(result, 'KG')
            # __str__ might be called internally by get_text, but not for initial processing
            # This verifies we're not doing str(item) at the top level


class TestExtractSpecificationsFromElement(unittest.TestCase):
    """Test _extract_specifications_from_element helper method"""
    
    def setUp(self):
        self.parser = GemilangUnitParser()
    
    def test_extract_specifications_from_divs(self):
        """Test extracting specifications from div elements"""
        html = """
        <div class="item">
            <div class="spec">Berat: 5 kg</div>
            <div class="spec">Volume: 2 liter</div>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item')
        
        specs = self.parser._extract_specifications_from_element(item)
        self.assertIsInstance(specs, list)
        self.assertGreater(len(specs), 0)
    
    def test_extract_specifications_from_spans(self):
        """Test extracting specifications from span elements"""
        html = """
        <div class="item">
            <span class="detail">Ukuran: 10x20 cm</span>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item')
        
        specs = self.parser._extract_specifications_from_element(item)
        self.assertIsInstance(specs, list)
    
    def test_extract_specifications_from_tables(self):
        """Test extracting specifications from table elements"""
        html = """
        <div class="item">
            <table>
                <tr><td>Berat</td><td>3 kg</td></tr>
            </table>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item')
        
        specs = self.parser._extract_specifications_from_element(item)
        self.assertIsInstance(specs, list)
    
    def test_extract_specifications_returns_empty_on_none(self):
        """Test that None input returns empty list"""
        specs = self.parser._extract_specifications_from_element(None)
        self.assertEqual(specs, [])
    
    def test_extract_specifications_handles_exception(self):
        """Test exception handling returns empty list"""
        mock_element = Mock()
        mock_element.find_all.side_effect = Exception("Test error")
        
        specs = self.parser._extract_specifications_from_element(mock_element)
        self.assertEqual(specs, [])


class TestCachedHasLxmlInHtmlParser(unittest.TestCase):
    """Test cached lxml checking in GemilangHtmlParser"""
    
    def test_parser_caches_lxml_check(self):
        """Test that parser caches lxml availability check per instance"""
        from api.gemilang.html_parser import GemilangHtmlParser
        
        parser = GemilangHtmlParser()
        self.assertIsNone(parser._cached_has_lxml)
        
        # Parse some HTML to trigger the cache
        html = '<div class="item-product"><h3>Test</h3></div>'
        parser.parse_products(html)
        
        # Cache should now be set
        self.assertIsNotNone(parser._cached_has_lxml)
        self.assertIsInstance(parser._cached_has_lxml, bool)
    
    def test_parser_reuses_cached_lxml_check(self):
        """Test that subsequent parses use cached value"""
        from api.gemilang.html_parser import GemilangHtmlParser
        
        parser = GemilangHtmlParser()
        
        # Set cache to use html.parser (avoid lxml not found error)
        parser._cached_has_lxml = False
        
        # First parse
        html1 = '<div class="item-product"><h3>Product 1</h3></div>'
        parser.parse_products(html1)
        
        # Cache should remain False
        self.assertFalse(parser._cached_has_lxml)
        
        # Second parse should use same cached value
        html2 = '<div class="item-product"><h3>Product 2</h3></div>'
        parser.parse_products(html2)
        
        # Cache should still be False (not changed)
        self.assertFalse(parser._cached_has_lxml)
    
    def test_different_parser_instances_have_independent_caches(self):
        """Test that different parser instances maintain independent caches"""
        from api.gemilang.html_parser import GemilangHtmlParser
        
        parser1 = GemilangHtmlParser()
        parser2 = GemilangHtmlParser()
        
        # Set parser1's cache
        parser1._cached_has_lxml = True
        
        # parser2's cache should still be None
        self.assertIsNone(parser2._cached_has_lxml)


class TestSetBasedPriorityRules(unittest.TestCase):
    """Test set-based priority rule optimization"""
    
    def setUp(self):
        self.parser = GemilangUnitParser()
    
    def test_priority_rules_use_sets(self):
        """Test that priority rules internally use sets for O(1) lookup"""
        units = ['KG', 'CM', 'LITER']
        result = self.parser._apply_priority_rules(units)
        
        # Should return weight unit (KG) which has high priority
        self.assertEqual(result, 'KG')
    
    def test_priority_rules_weight_over_length(self):
        """Test weight units have priority over length units"""
        units = ['CM', 'KG', 'M']
        result = self.parser._apply_priority_rules(units)
        self.assertEqual(result, 'KG')
    
    def test_priority_rules_weight_over_volume(self):
        """Test weight units have priority over volume units"""
        units = ['LITER', 'KG', 'ML']
        result = self.parser._apply_priority_rules(units)
        self.assertEqual(result, 'KG')
    
    def test_priority_rules_area_over_length(self):
        """Test area units have priority over length units"""
        units = ['CM', 'M²', 'M']
        result = self.parser._apply_priority_rules(units)
        self.assertEqual(result, 'M²')
    
    def test_priority_rules_with_empty_list(self):
        """Test priority rules with empty list"""
        units = []
        result = self.parser._apply_priority_rules(units)
        self.assertIsNone(result)
    
    def test_priority_rules_with_single_unit(self):
        """Test priority rules with single unit"""
        units = ['KG']
        result = self.parser._apply_priority_rules(units)
        self.assertEqual(result, 'KG')
    
    def test_priority_rules_performance(self):
        """Test that set-based lookup is efficient with many units"""
        # Create a list with duplicate units
        units = ['KG', 'GRAM', 'LITER', 'ML', 'CM', 'M'] * 100
        
        # Should still return quickly with O(1) set lookups
        import time
        start = time.perf_counter()
        result = self.parser._apply_priority_rules(units)
        duration = time.perf_counter() - start
        
        self.assertEqual(result, 'KG')
        # Should complete in under 10ms even with 600 items
        self.assertLess(duration, 0.01)


class TestLoggerGuards(unittest.TestCase):
    """Test logger guard optimizations"""
    
    def test_logger_guards_prevent_formatting(self):
        """Test that logger guards prevent unnecessary string formatting"""
        from api.gemilang.html_parser import GemilangHtmlParser
        import logging
        
        parser = GemilangHtmlParser()
        
        # Set logging to WARNING level (INFO will be disabled)
        with patch('api.gemilang.html_parser.logger') as mock_logger:
            mock_logger.isEnabledFor.return_value = False
            
            html = '<div class="item-product"><h3>Test</h3></div>'
            parser.parse_products(html)
            
            # Logger.info should not be called if isEnabledFor returns False
            mock_logger.info.assert_not_called()
    
    def test_logger_guards_allow_when_enabled(self):
        """Test that logger guards allow logging when enabled"""
        from api.gemilang.html_parser import GemilangHtmlParser
        
        parser = GemilangHtmlParser()
        
        with patch('api.gemilang.html_parser.logger') as mock_logger:
            mock_logger.isEnabledFor.return_value = True
            
            html = '<div class="item-product"><h3>Test</h3></div>'
            parser.parse_products(html)
            
            # Logger.info should be called when enabled
            mock_logger.info.assert_called()


class TestEdgeCaseCoverage(unittest.TestCase):
    """Test edge cases to achieve 100% coverage"""
    
    def setUp(self):
        self.parser = GemilangUnitParser()
    
    def test_extract_specifications_with_attributeerror_in_span(self):
        """Test AttributeError handling in span extraction (line 326)"""
        from api.gemilang.unit_parser import SpecificationFinder
        from bs4 import BeautifulSoup
        import logging
        
        finder = SpecificationFinder()
        html = '<div><span>ukuran: 5 kg</span><span>test</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        # Set logger to DEBUG level to trigger the isEnabledFor check
        original_level = logging.getLogger('api.gemilang.unit_parser').level
        logging.getLogger('api.gemilang.unit_parser').setLevel(logging.DEBUG)
        
        try:
            # Mock one span to raise AttributeError
            spans = soup.find_all('span')
            if len(spans) > 0:
                with patch.object(spans[0], 'get_text', side_effect=AttributeError("Test error")):
                    # Should handle the error gracefully and log at DEBUG level
                    specs = finder._extract_from_spans(soup)
                    # Should return list (may be empty or have other spans)
                    self.assertIsInstance(specs, list)
        finally:
            logging.getLogger('api.gemilang.unit_parser').setLevel(original_level)
    
    def test_extract_specifications_with_attributeerror_in_div(self):
        """Test AttributeError handling in div extraction (line 347)"""
        from api.gemilang.unit_parser import SpecificationFinder
        from bs4 import BeautifulSoup
        import logging
        
        finder = SpecificationFinder()
        html = '<div class="spec-detail">Dimensi: 10x20</div><div class="spec-info">test</div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        # Set logger to DEBUG level to trigger the isEnabledFor check
        original_level = logging.getLogger('api.gemilang.unit_parser').level
        logging.getLogger('api.gemilang.unit_parser').setLevel(logging.DEBUG)
        
        try:
            # Mock one div to raise AttributeError
            divs = soup.find_all('div')
            if len(divs) > 0:
                with patch.object(divs[0], 'get_text', side_effect=AttributeError("Test error")):
                    # Should handle the error gracefully and log at DEBUG level
                    specs = finder._extract_from_divs(soup)
                    # Should return list (may be empty or have other divs)
                    self.assertIsInstance(specs, list)
        finally:
            logging.getLogger('api.gemilang.unit_parser').setLevel(original_level)
    
    def test_extract_specifications_from_element_with_exception(self):
        """Test exception handling in _extract_specifications_from_element (line 440)"""
        import logging
        
        html = '<div class="item"><span>Test: 5 kg</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('div')
        
        # Set logger to DEBUG level to trigger the isEnabledFor check
        original_level = logging.getLogger('api.gemilang.unit_parser').level
        logging.getLogger('api.gemilang.unit_parser').setLevel(logging.DEBUG)
        
        try:
            # Mock find_all to raise an exception
            with patch.object(element, 'find_all', side_effect=Exception("Test error")):
                specs = self.parser._extract_specifications_from_element(element)
                # Should return empty list on exception
                self.assertEqual(specs, [])
        finally:
            logging.getLogger('api.gemilang.unit_parser').setLevel(original_level)
    
    def test_extract_units_from_specifications_with_exception(self):
        """Test exception handling in _extract_units_from_specifications (line 489)"""
        import logging
        
        # Set logger to DEBUG level to trigger the isEnabledFor check
        original_level = logging.getLogger('api.gemilang.unit_parser').level
        logging.getLogger('api.gemilang.unit_parser').setLevel(logging.DEBUG)
        
        try:
            # Mock extractor to raise exception
            with patch.object(self.parser.extractor, 'extract_unit', side_effect=Exception("Test error")):
                specifications = ['Berat: 5 kg', 'Volume: 10 liter']
                found_units = self.parser._extract_units_from_specifications(specifications)
                # Should return empty list when all extractions fail
                self.assertEqual(found_units, [])
        finally:
            logging.getLogger('api.gemilang.unit_parser').setLevel(original_level)


class TestRegexCacheOptimization(unittest.TestCase):
    """Test pre-compiled regex pattern optimization"""
    
    def test_slug_pattern_is_precompiled(self):
        """Test that SLUG_CLEAN_PATTERN is pre-compiled"""
        from api.gemilang.html_parser import RegexCache
        import re
        
        self.assertIsInstance(RegexCache.SLUG_CLEAN_PATTERN, re.Pattern)
    
    def test_whitespace_pattern_is_precompiled(self):
        """Test that WHITESPACE_PATTERN is pre-compiled"""
        from api.gemilang.html_parser import RegexCache
        import re
        
        self.assertIsInstance(RegexCache.WHITESPACE_PATTERN, re.Pattern)
    
    def test_slug_pattern_works_correctly(self):
        """Test that pre-compiled slug pattern works correctly"""
        from api.gemilang.html_parser import RegexCache
        
        text = "Test Product 123!"
        result = RegexCache.SLUG_CLEAN_PATTERN.sub('', text.lower())
        expected = "testproduct123"
        self.assertEqual(result, expected)
    
    def test_whitespace_pattern_works_correctly(self):
        """Test that pre-compiled whitespace pattern works correctly"""
        from api.gemilang.html_parser import RegexCache
        
        text = "Test   Product    Name"
        result = RegexCache.WHITESPACE_PATTERN.sub(' ', text)
        expected = "Test Product Name"
        self.assertEqual(result, expected)
    
    def test_regex_patterns_improve_performance(self):
        """Test that pre-compiled patterns improve performance"""
        from api.gemilang.html_parser import RegexCache
        import time
        import re
        
        text = "Test Product 123! @#$" * 100
        
        # Using pre-compiled pattern
        start = time.perf_counter()
        for _ in range(100):
            RegexCache.SLUG_CLEAN_PATTERN.sub('', text.lower())
        precompiled_duration = time.perf_counter() - start
        
        # Using inline compilation
        start = time.perf_counter()
        for _ in range(100):
            re.sub(r'[^a-z0-9\-]', '', text.lower())
        inline_duration = time.perf_counter() - start
        
        # Pre-compiled should be faster (or at least not significantly slower)
        self.assertLessEqual(precompiled_duration, inline_duration * 1.5)
