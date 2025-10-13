import unittest
import re
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from api.gemilang.unit_parser import (
    GemilangUnitParser,
    UnitExtractor,
    UnitPatternRepository,
    AreaPatternStrategy,
    AdjacentPatternStrategy,
    SpecificationFinder,
    UnitParserConfiguration
)


class TestGemilangUnitParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = GemilangUnitParser()
        self.extractor = UnitExtractor()
    
    def test_extract_basic_length_units(self):
        test_cases = [
            ("Ukuran 25cm", "CM"),
            ("Panjang 100mm", "MM"),
            ("Diameter 2 meter", "M"),
            ("Size 4 inch", "INCH"),
            ("Height 6 feet", "FEET")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_extract_basic_area_units(self):
        test_cases = [
            ("Luas 100cm²", "CM²"),
            ("Area 25 m²", "M²"),
            ("Size 10 inch²", "INCH²")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_extract_basic_weight_units(self):
        test_cases = [
            ("Berat 5kg", "KG"),
            ("Weight 250 gram", "GRAM"),
            ("Mass 2 ton", "TON"),
            ("Weight 10 pound", "POUND")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_extract_basic_volume_units(self):
        test_cases = [
            ("Kapasitas 1 liter", "LITER"),
            ("Volume 500ml", "ML"),
            ("Capacity 5 gallon", "GALLON"),
            ("Volume 2m³", "M³")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_extract_electrical_units(self):
        test_cases = [
            ("Daya 100 watt", "WATT"),
            ("Tegangan 220 volt", "VOLT"),
            ("Arus 5 ampere", "AMPERE"),
            ("Konsumsi 1000 kwh", "KWH")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_extract_packaging_units(self):
        test_cases = [
            ("Isi 12 pcs", "PCS"),
            ("Jumlah 1 set", "SET"),
            ("Kemasan 5 pack", "PACK"),
            ("Per kotak 10 box", "BOX"),
            ("Per gulungan 1 roll", "ROLL")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_extract_construction_units(self):
        test_cases = [
            ("Per papan", "PAPAN"),
            ("Per batang", "BATANG"),
            ("Per lembar", "SHEET"),  # "lembar" now maps to SHEET (English equivalent)
            ("Per unit", "UNIT")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_extract_time_units(self):
        test_cases = [
            ("Sewa per hari", "HARI"),
            ("Per minggu", "MINGGU"),
            ("Per bulan", "BULAN"),
            ("Per tahun", "TAHUN"),
            ("Per jam", "JAM")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_no_unit_found(self):
        test_cases = [
            "Produk berkualitas tinggi",
            "Harga murah meriah", 
            "Toko terpercaya",
            "Garansi resmi"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertIsNone(unit)
    
    def test_html_parsing(self):
        html = """
        <div class="product-info">
            <h1>Semen Portland 50kg</h1>
            <p>Berat: 50 kilogram per sak</p>
        </div>
        """
        unit = self.parser.parse_unit(html)
        self.assertEqual(unit, "KG")
    
    def test_empty_input(self):
        self.assertIsNone(self.extractor.extract_unit(""))
        self.assertIsNone(self.extractor.extract_unit(None))
        self.assertIsNone(self.parser.parse_unit(""))
        self.assertIsNone(self.parser.parse_unit(None))


class TestUnitPatternRepository(unittest.TestCase):
    
    def test_get_patterns_for_nonexistent_unit(self):
        repo = UnitPatternRepository()
        result = repo.get_patterns("NONEXISTENT")
        self.assertEqual(result, [])
    
    def test_get_all_units_returns_complete_list(self):
        repo = UnitPatternRepository()
        units = repo.get_all_units()
        self.assertIn("KG", units)
        self.assertIn("M²", units)
        self.assertTrue(len(units) > 40)


class TestAreaPatternStrategy(unittest.TestCase):
    
    def test_area_pattern_regex_error_handling(self):
        strategy = AreaPatternStrategy()
        with patch('re.search', side_effect=re.error("bad pattern")):
            result = strategy.extract_unit("10 x 20 cm")
            self.assertIsNone(result)
    
    def test_area_pattern_generic_exception_handling(self):
        strategy = AreaPatternStrategy()
        with patch('re.search', side_effect=ValueError("generic error")):
            result = strategy.extract_unit("10 x 20 cm")
            self.assertIsNone(result)
    
    def test_area_pattern_no_match_returns_none(self):
        strategy = AreaPatternStrategy()
        result = strategy.extract_unit("just some text without dimensions")
        self.assertIsNone(result)
    
    def test_area_pattern_consolidated_match(self):
        strategy = AreaPatternStrategy()
        # Test that the consolidated pattern matches various formats
        test_cases = [
            ("size 10x20mm", "MM²"),
            ("10 x 20 cm", "CM²"),
            ("15x25 m", "M²"),
            ("5x10inch", "INCH²"),
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = strategy.extract_unit(text)
                self.assertEqual(result, expected)


class TestAdjacentPatternStrategy(unittest.TestCase):
    
    def test_adjacent_pattern_match_group_error(self):
        strategy = AdjacentPatternStrategy()
        mock_match = Mock()
        mock_match.group.side_effect = IndexError("no such group")
        
        with patch('re.finditer', return_value=[mock_match]):
            result = strategy.extract_unit("12kg")
            self.assertIsNone(result)
    
    def test_adjacent_pattern_attribute_error(self):
        strategy = AdjacentPatternStrategy()
        mock_match = Mock()
        mock_match.group.side_effect = AttributeError("attribute error")
        
        with patch('re.finditer', return_value=[mock_match]):
            result = strategy.extract_unit("12kg")
            self.assertIsNone(result)
    
    def test_adjacent_pattern_unit_key_not_in_map(self):
        strategy = AdjacentPatternStrategy()
        mock_match = Mock()
        mock_match.group.return_value = "unknown_unit"
        
        with patch('re.finditer', return_value=[mock_match]):
            result = strategy.extract_unit("12unknown")
            self.assertIsNone(result)
    
    def test_adjacent_pattern_match_continues_on_error(self):
        strategy = AdjacentPatternStrategy()
        mock_match1 = Mock()
        mock_match1.group.side_effect = IndexError("error")
        mock_match2 = Mock()
        mock_match2.group.return_value = "kg"
        
        with patch('re.finditer', return_value=[mock_match1, mock_match2]):
            result = strategy.extract_unit("12kg")
            self.assertEqual(result, "KG")
    
    def test_adjacent_pattern_regex_error(self):
        strategy = AdjacentPatternStrategy()
        with patch('re.finditer', side_effect=re.error("regex error")):
            result = strategy.extract_unit("12kg")
            self.assertIsNone(result)
    
    def test_adjacent_pattern_generic_exception(self):
        strategy = AdjacentPatternStrategy()
        with patch('re.finditer', side_effect=RuntimeError("generic error")):
            result = strategy.extract_unit("12kg")
            self.assertIsNone(result)
    
    def test_adjacent_pattern_no_match_in_map(self):
        strategy = AdjacentPatternStrategy()
        result = strategy.extract_unit("some random text")
        self.assertIsNone(result)


class TestUnitExtractorAdvanced(unittest.TestCase):
    
    def test_extract_unit_with_none_input(self):
        extractor = UnitExtractor()
        result = extractor.extract_unit(None)
        self.assertIsNone(result)
    
    def test_extract_unit_with_non_string_input(self):
        extractor = UnitExtractor()
        result = extractor.extract_unit(123)
        self.assertIsNone(result)
    
    def test_extract_unit_with_empty_string(self):
        extractor = UnitExtractor()
        result = extractor.extract_unit("")
        self.assertIsNone(result)
    
    def test_extract_unit_with_whitespace_only(self):
        extractor = UnitExtractor()
        result = extractor.extract_unit("   ")
        self.assertIsNone(result)
    
    def test_extract_unit_exception_during_extraction(self):
        extractor = UnitExtractor()
        extractor._area_pattern_strategy = Mock()
        extractor._area_pattern_strategy.extract_unit.side_effect = RuntimeError("error")
        
        result = extractor.extract_unit("test")
        self.assertIsNone(result)
    
    def test_extract_unit_fallback_to_adjacent_pattern(self):
        extractor = UnitExtractor()
        result = extractor.extract_unit("diameter 25mm")
        self.assertEqual(result, "MM")
    
    def test_extract_unit_returns_area_unit_when_found(self):
        extractor = UnitExtractor()
        result = extractor.extract_unit("10 x 20 cm")
        self.assertEqual(result, "CM²")
    
    def test_extract_unit_returns_priority_unit_when_no_area(self):
        extractor = UnitExtractor()
        result = extractor.extract_unit("5 kg")
        self.assertEqual(result, "KG")
    
    def test_extract_unit_returns_none_when_no_unit_found(self):
        extractor = UnitExtractor()
        with patch.object(extractor._area_pattern_strategy, 'extract_unit', return_value=None):
            with patch.object(extractor, '_extract_by_priority_patterns', return_value=None):
                with patch.object(extractor._adjacent_pattern_strategy, 'extract_unit', return_value=None):
                    result = extractor.extract_unit("no unit here")
                    self.assertIsNone(result)
    
    def test_extract_unit_adjacent_pattern_returns_unit(self):
        extractor = UnitExtractor()
        with patch.object(extractor._area_pattern_strategy, 'extract_unit', return_value=None):
            with patch.object(extractor, '_extract_by_priority_patterns', return_value=None):
                with patch.object(extractor._adjacent_pattern_strategy, 'extract_unit', return_value="KG"):
                    result = extractor.extract_unit("test")
                    self.assertEqual(result, "KG")
    
    def test_extract_by_priority_regex_error(self):
        extractor = UnitExtractor()
        with patch('re.search', side_effect=re.error("bad regex")):
            result = extractor._extract_by_priority_patterns("test kg")
            self.assertIsNone(result)
    
    def test_extract_by_priority_generic_exception(self):
        extractor = UnitExtractor()
        mock_repo = Mock()
        mock_repo.get_priority_order.side_effect = RuntimeError("error")
        extractor._pattern_repository = mock_repo
        
        result = extractor._extract_by_priority_patterns("test")
        self.assertIsNone(result)
    
    def test_extract_by_priority_truncates_long_text(self):
        extractor = UnitExtractor()
        long_text = "x" * 6000 + " 5 kg"
        result = extractor._extract_by_priority_patterns(long_text)
        self.assertIsNone(result)
    
    def test_extract_by_priority_handles_text_at_limit(self):
        extractor = UnitExtractor()
        text_at_limit = "a" * 4990 + " 5 kg"
        result = extractor._extract_by_priority_patterns(text_at_limit)
        self.assertEqual(result, "KG")
    
    def test_extract_area_units_method(self):
        extractor = UnitExtractor()
        result = extractor._extract_area_units("10 x 20 cm")
        self.assertEqual(result, "CM²")
    
    def test_priority_order_property(self):
        extractor = UnitExtractor()
        priority = extractor.priority_order
        self.assertIsInstance(priority, list)
        self.assertTrue(len(priority) > 0)
    
    def test_unit_patterns_property(self):
        extractor = UnitExtractor()
        patterns = extractor.unit_patterns
        self.assertIsInstance(patterns, dict)
        self.assertIn("KG", patterns)


class TestSpecificationFinder(unittest.TestCase):
    
    def test_find_specification_values_with_table_error(self):
        finder = SpecificationFinder()
        html = "<table><tr><td>Ukuran</td><td>40cm</td></tr></table>"
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(finder, '_extract_from_tables', side_effect=Exception("table error")):
            specs = finder.find_specification_values(soup)
            self.assertIsInstance(specs, list)
    
    def test_find_specification_values_with_span_error(self):
        finder = SpecificationFinder()
        html = "<span>Spesifikasi</span>"
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(finder, '_extract_from_spans', side_effect=Exception("span error")):
            specs = finder.find_specification_values(soup)
            self.assertIsInstance(specs, list)
    
    def test_find_specification_values_with_div_error(self):
        finder = SpecificationFinder()
        html = '<div class="spec">Details</div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(finder, '_extract_from_divs', side_effect=Exception("div error")):
            specs = finder.find_specification_values(soup)
            self.assertIsInstance(specs, list)
    
    def test_extract_from_tables_with_row_error(self):
        finder = SpecificationFinder()
        html = "<table><tr><td>Ukuran</td><td>40cm</td></tr></table>"
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table')
        original_find_all = table.find_all
        
        def mock_find_all(*args, **kwargs):
            if args and args[0] == 'tr':
                raise Exception("row error")
            return original_find_all(*args, **kwargs)
        
        with patch.object(table, 'find_all', side_effect=mock_find_all):
            specs = finder._extract_from_tables(soup)
            self.assertEqual(specs, [])
    
    def test_extract_from_tables_find_all_error(self):
        finder = SpecificationFinder()
        html = "<div></div>"
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(soup, 'find_all', side_effect=Exception("find_all error")):
            specs = finder._extract_from_tables(soup)
            self.assertEqual(specs, [])
    
    def test_extract_from_tables_with_cell_processing_error(self):
        finder = SpecificationFinder()
        html = "<table><tr><td>Ukuran</td><td>40cm</td></tr></table>"
        soup = BeautifulSoup(html, 'html.parser')
        
        mock_cell = Mock()
        mock_cell.get_text.side_effect = IndexError("index error")
        
        row = soup.find('tr')
        with patch.object(row, 'find_all', return_value=[mock_cell, mock_cell]):
            specs = finder._extract_from_tables(soup)
            self.assertEqual(specs, [])
    
    def test_extract_from_spans_attribute_error(self):
        finder = SpecificationFinder()
        html = "<span>Spesifikasi</span>"
        soup = BeautifulSoup(html, 'html.parser')
        
        span = soup.find('span')
        with patch.object(span, 'get_text', side_effect=AttributeError("attr error")):
            specs = finder._extract_from_spans(soup)
            self.assertEqual(specs, [])
    
    def test_extract_from_spans_find_all_error(self):
        finder = SpecificationFinder()
        html = "<div></div>"
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(soup, 'find_all', side_effect=Exception("find_all error")):
            specs = finder._extract_from_spans(soup)
            self.assertEqual(specs, [])
    
    def test_extract_from_spans_success_with_keywords(self):
        finder = SpecificationFinder()
        html = '''
            <span>Product spesifikasi: Test spec</span>
            <span>Ukuran: 10x20 cm</span>
            <span>Dimensi dan ukuran produk</span>
            <span>Random text without keywords</span>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        specs = finder._extract_from_spans(soup)
        self.assertIn("Product spesifikasi: Test spec", specs)
        self.assertIn("Ukuran: 10x20 cm", specs)
        self.assertIn("Dimensi dan ukuran produk", specs)
        self.assertNotIn("Random text without keywords", specs)
    
    def test_extract_from_divs_attribute_error(self):
        finder = SpecificationFinder()
        html = '<div class="spec-info">Details</div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        div = soup.find('div')
        with patch.object(div, 'get_text', side_effect=AttributeError("attr error")):
            specs = finder._extract_from_divs(soup)
            self.assertEqual(specs, [])
    
    def test_extract_from_divs_find_all_error(self):
        finder = SpecificationFinder()
        html = "<div></div>"
        soup = BeautifulSoup(html, 'html.parser')
        
        with patch.object(soup, 'find_all', side_effect=Exception("find_all error")):
            specs = finder._extract_from_divs(soup)
            self.assertEqual(specs, [])
    
    def test_extract_from_divs_success_with_keywords(self):
        finder = SpecificationFinder()
        html = '''
            <div class="spec-info">Specification text</div>
            <div class="product-detail">Detail text</div>
            <div class="item-description">Description text</div>
            <div class="other-class">Should be included</div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        specs = finder._extract_from_divs(soup)
        self.assertIn("Specification text", specs)
        self.assertIn("Detail text", specs)
        self.assertIn("Description text", specs)


class TestUnitParserConfiguration(unittest.TestCase):
    
    def test_is_construction_context_with_none(self):
        config = UnitParserConfiguration()
        result = config.is_construction_context(None)
        self.assertFalse(result)
    
    def test_is_construction_context_with_non_string(self):
        config = UnitParserConfiguration()
        result = config.is_construction_context(123)
        self.assertFalse(result)
    
    def test_is_construction_context_exception_handling(self):
        config = UnitParserConfiguration()
        mock_text = Mock()
        mock_text.lower.side_effect = RuntimeError("error")
        
        result = config.is_construction_context(mock_text)
        self.assertFalse(result)
    
    def test_is_construction_context_positive(self):
        config = UnitParserConfiguration()
        result = config.is_construction_context("semen portland 50kg")
        self.assertTrue(result)
    
    def test_is_construction_context_keyword_iteration_error(self):
        config = UnitParserConfiguration()
        
        def mock_any(iterable):
            for _ in iterable:
                raise RuntimeError("iteration error")
        
        with patch('builtins.any', side_effect=mock_any):
            result = config.is_construction_context("semen")
            self.assertFalse(result)
    
    def test_is_electrical_context_with_none(self):
        config = UnitParserConfiguration()
        result = config.is_electrical_context(None)
        self.assertFalse(result)
    
    def test_is_electrical_context_with_non_string(self):
        config = UnitParserConfiguration()
        result = config.is_electrical_context(123)
        self.assertFalse(result)
    
    def test_is_electrical_context_exception_handling(self):
        config = UnitParserConfiguration()
        mock_text = Mock()
        mock_text.lower.side_effect = RuntimeError("error")
        
        result = config.is_electrical_context(mock_text)
        self.assertFalse(result)
    
    def test_is_electrical_context_positive(self):
        config = UnitParserConfiguration()
        result = config.is_electrical_context("lampu listrik 15 watt")
        self.assertTrue(result)
    
    def test_is_electrical_context_keyword_iteration_error(self):
        config = UnitParserConfiguration()
        
        def mock_any(iterable):
            for _ in iterable:
                raise RuntimeError("iteration error")
        
        with patch('builtins.any', side_effect=mock_any):
            result = config.is_electrical_context("lampu")
            self.assertFalse(result)


class TestGemilangUnitParserAdvanced(unittest.TestCase):
    
    def test_parse_unit_with_none_input(self):
        parser = GemilangUnitParser()
        result = parser.parse_unit(None)
        self.assertIsNone(result)
    
    def test_parse_unit_with_non_string_input(self):
        parser = GemilangUnitParser()
        result = parser.parse_unit(123)
        self.assertIsNone(result)
    
    def test_parse_unit_with_soup_creation_failure(self):
        parser = GemilangUnitParser()
        with patch.object(parser, '_create_soup_safely', return_value=None):
            result = parser.parse_unit("<div>test</div>")
            self.assertIsNone(result)
    
    def test_parse_unit_with_generic_exception(self):
        parser = GemilangUnitParser()
        with patch.object(parser, '_create_soup_safely', side_effect=RuntimeError("error")):
            result = parser.parse_unit("<div>test</div>")
            self.assertIsNone(result)
    
    def test_create_soup_safely_exception(self):
        parser = GemilangUnitParser()
        with patch('api.gemilang.unit_parser.BeautifulSoup', side_effect=Exception("parse error")):
            result = parser._create_soup_safely("<div>test</div>")
            self.assertIsNone(result)
    
    def test_extract_specifications_safely_exception(self):
        parser = GemilangUnitParser()
        soup = BeautifulSoup("<div>test</div>", 'html.parser')
        
        with patch.object(parser.spec_finder, 'find_specification_values', side_effect=Exception("error")):
            result = parser._extract_specifications_safely(soup)
            self.assertEqual(result, [])
    
    def test_extract_units_from_specifications_with_exception(self):
        parser = GemilangUnitParser()
        
        with patch.object(parser.extractor, 'extract_unit', side_effect=Exception("error")):
            result = parser._extract_units_from_specifications(["test spec"])
            self.assertEqual(result, [])
    
    def test_apply_priority_rules_empty_list(self):
        parser = GemilangUnitParser()
        result = parser._apply_priority_rules([])
        self.assertIsNone(result)
    
    def test_apply_priority_rules_with_area_unit(self):
        parser = GemilangUnitParser()
        result = parser._apply_priority_rules(["CM²", "KG"])
        self.assertEqual(result, "CM²")
    
    def test_apply_priority_rules_with_volume_unit(self):
        parser = GemilangUnitParser()
        result = parser._apply_priority_rules(["M³", "KG"])
        self.assertEqual(result, "M³")
    
    def test_apply_priority_rules_with_weight_unit(self):
        parser = GemilangUnitParser()
        result = parser._apply_priority_rules(["KG", "PCS"])
        self.assertEqual(result, "KG")
    
    def test_apply_priority_rules_with_other_unit(self):
        parser = GemilangUnitParser()
        result = parser._apply_priority_rules(["PCS"])
        self.assertEqual(result, "PCS")
    
    def test_apply_priority_rules_exception_handling(self):
        parser = GemilangUnitParser()
        mock_units = MagicMock()
        mock_units.__iter__.side_effect = RuntimeError("error")
        mock_units.__getitem__.return_value = "KG"
        
        result = parser._apply_priority_rules(mock_units)
        self.assertEqual(result, "KG")
    
    def test_extract_from_full_text_success(self):
        parser = GemilangUnitParser()
        soup = BeautifulSoup("<div>Berat 5kg</div>", 'html.parser')
        
        result = parser._extract_from_full_text(soup)
        self.assertEqual(result, "KG")
    
    def test_extract_from_full_text_exception(self):
        parser = GemilangUnitParser()
        mock_soup = Mock()
        mock_soup.get_text.side_effect = Exception("error")
        
        result = parser._extract_from_full_text(mock_soup)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()