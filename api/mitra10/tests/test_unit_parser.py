import unittest
from bs4 import BeautifulSoup
from api.mitra10.unit_parser import ErrorHandlingMixin
from api.mitra10.unit_parser import ContextChecker
from api.mitra10.unit_parser import TextProcessingHelper
from api.mitra10.unit_parser import (
    Mitra10UnitParser, Mitra10UnitExtractor, Mitra10UnitPatternRepository,
    Mitra10AreaPatternStrategy, Mitra10AdjacentPatternStrategy,
    Mitra10SpecificationFinder, Mitra10UnitParserConfiguration,
    UNIT_M2, UNIT_CM2, UNIT_INCH2, UNIT_MM2, UNIT_M3, UNIT_CM3,
    UNIT_KG, UNIT_GRAM, UNIT_TON, UNIT_POUND
)


class TestMitra10UnitPatternRepository(unittest.TestCase):
    
    def setUp(self):
        self.repository = Mitra10UnitPatternRepository()
    
    def test_get_patterns_existing_unit(self):
        patterns = self.repository.get_patterns('MM')
        self.assertIn('mm', patterns)
        self.assertIn('milimeter', patterns)
    
    def test_get_patterns_non_existing_unit(self):
        patterns = self.repository.get_patterns('NONEXISTENT')
        self.assertEqual(patterns, [])
    
    def test_get_all_units(self):
        units = self.repository.get_all_units()
        self.assertIn('MM', units)
        self.assertIn(UNIT_KG, units)
        self.assertIn('PCS', units)
    
    def test_priority_order(self):
        priority = self.repository.get_priority_order()
        self.assertIsInstance(priority, list)
        self.assertIn(UNIT_M2, priority)
        self.assertIn(UNIT_KG, priority)


class TestMitra10AreaPatternStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = Mitra10AreaPatternStrategy()
    
    def test_extract_area_cm(self):
        text = "Ukuran keramik 60x60 cm"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, UNIT_CM2)
    
    def test_extract_area_mm(self):
        text = "Dimensi 25x25 mm"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, UNIT_MM2)
    
    def test_extract_area_meter(self):
        text = "Luas 2x3 m"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, UNIT_M2)
    
    def test_extract_area_inch(self):
        text = "Size 12x12 inch"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, UNIT_INCH2)
    
    def test_no_match(self):
        text = "Berat 25 kg"
        unit = self.strategy.extract_unit(text.lower())
        self.assertIsNone(unit)
    
    def test_invalid_regex(self):
        # Test error handling
        unit = self.strategy.extract_unit("")
        self.assertIsNone(unit)


class TestMitra10AdjacentPatternStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = Mitra10AdjacentPatternStrategy()
    
    def test_extract_weight_kg(self):
        text = "Berat 25kg"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, UNIT_KG)
    
    def test_extract_pieces(self):
        text = "Isi 100pcs"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, 'PCS')
    
    def test_extract_diameter(self):
        text = "Diameter 25mm"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, 'MM')
    
    def test_extract_symbol_diameter(self):
        text = "Ø 25mm"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, 'MM')
    
    def test_extract_time_unit(self):
        text = "Garansi 1 tahun"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, 'TAHUN')
    
    def test_extract_cement_bag(self):
        text = "Semen 50 sak"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, 'SAK')
    
    def test_extract_roll(self):
        text = "Kabel 100 roll"
        unit = self.strategy.extract_unit(text.lower())
        self.assertEqual(unit, 'ROLL')
    
    def test_no_match(self):
        text = "Produk berkualitas tinggi"
        unit = self.strategy.extract_unit(text.lower())
        self.assertIsNone(unit)


class TestMitra10UnitExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = Mitra10UnitExtractor()
    
    def test_extract_area_unit(self):
        text = "Ukuran keramik 60x60 cm persegi"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, UNIT_CM2)
    
    def test_extract_weight_unit(self):
        text = "Berat semen 40kg per sak"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, UNIT_KG)
    
    def test_extract_length_unit(self):
        text = "Panjang pipa 3 meter"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, 'M')
    
    def test_extract_pieces_unit(self):
        text = "Isi kemasan 25 pcs baut"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, 'PCS')
    
    def test_empty_input(self):
        unit = self.extractor.extract_unit("")
        self.assertIsNone(unit)
    
    def test_none_input(self):
        unit = self.extractor.extract_unit(None)
        self.assertIsNone(unit)
    
    def test_non_string_input(self):
        unit = self.extractor.extract_unit(123)
        self.assertIsNone(unit)
    
    def test_very_long_text(self):
        long_text = "test " * 2000  # Create long text
        unit = self.extractor.extract_unit(long_text + " 25kg")
        # Should still work despite truncation warning - unit is found because it's at the end
        self.assertEqual(unit, UNIT_KG)  # Unit found despite truncation

    def test_whitespace_only_input(self):
        # Cover validate_and_clean_text branch where stripped text becomes empty (~180)
        unit = self.extractor.extract_unit("   \t \n  ")
        self.assertIsNone(unit)

    def test_adjacent_branch_via_extractor(self):
        # Force adjacent-pattern path by using a unit ('sak') not present in standard patterns (~345)
        text = "Semen kualitas tinggi 50 sak"
        self.assertEqual(self.extractor.extract_unit(text), 'SAK')


class TestMitra10SpecificationFinder(unittest.TestCase):
    
    def setUp(self):
        self.finder = Mitra10SpecificationFinder()
    
    def test_find_table_specifications(self):
        html = """
        <table>
            <tr><td>Berat</td><td>25 kg</td></tr>
            <tr><td>Ukuran</td><td>60x60 cm</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')
        specs = self.finder.find_specification_values(soup)
        
        self.assertIn("25 kg", specs)
        self.assertIn("60x60 cm", specs)
    
    def test_find_div_specifications(self):
        html = """
        <div class="product-info">Berat: 40kg, Dimensi: 30x30 cm</div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        specs = self.finder.find_specification_values(soup)
        
        self.assertTrue(any("40kg" in spec for spec in specs))
    
    def test_find_span_specifications(self):
        html = """
        <span>Ukuran produk 25x25 mm</span>
        """
        soup = BeautifulSoup(html, 'html.parser')
        specs = self.finder.find_specification_values(soup)
        
        self.assertTrue(any("25x25 mm" in spec for spec in specs))
    
    def test_empty_html(self):
        soup = BeautifulSoup("", 'html.parser')
        specs = self.finder.find_specification_values(soup)
        self.assertEqual(specs, [])


class TestMitra10UnitParserConfiguration(unittest.TestCase):
    
    def setUp(self):
        self.config = Mitra10UnitParserConfiguration()
    
    def test_construction_context(self):
        text = "Semen portland 40kg untuk konstruksi bangunan"
        self.assertTrue(self.config.is_construction_context(text))
    
    def test_electrical_context(self):
        text = "Kabel listrik 100 watt untuk instalasi"
        self.assertTrue(self.config.is_electrical_context(text))
    
    def test_plumbing_context(self):
        text = "Pipa PVC diameter 4 inch untuk saluran air"
        self.assertTrue(self.config.is_plumbing_context(text))
    
    def test_no_context_match(self):
        text = "Produk umum tanpa konteks spesifik"
        self.assertFalse(self.config.is_construction_context(text))
        self.assertFalse(self.config.is_electrical_context(text))
        self.assertFalse(self.config.is_plumbing_context(text))
    
    def test_empty_text(self):
        self.assertFalse(self.config.is_construction_context(""))
        self.assertFalse(self.config.is_electrical_context(""))
        self.assertFalse(self.config.is_plumbing_context(""))
    
    def test_none_input(self):
        self.assertFalse(self.config.is_construction_context(None))
        self.assertFalse(self.config.is_electrical_context(None))
        self.assertFalse(self.config.is_plumbing_context(None))


class TestMitra10UnitParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = Mitra10UnitParser()
    
    def test_parse_construction_product(self):
        html = """
        <div class="product-detail">
            <h1>Semen Portland 40kg</h1>
            <table>
                <tr><td>Berat</td><td>40 kg</td></tr>
                <tr><td>Kemasan</td><td>Per sak</td></tr>
            </table>
        </div>
        """
        unit = self.parser.parse_unit(html)
        self.assertEqual(unit, UNIT_KG)
    
    def test_parse_electrical_product(self):
        html = """
        <div class="product-info">
            <span>Lampu LED 15 watt hemat energi</span>
            <div>Tegangan: 220 volt</div>
        </div>
        """
        unit = self.parser.parse_unit(html)
        self.assertEqual(unit, 'WATT')
    
    def test_parse_area_product(self):
        html = """
        <div class="specification">
            <p>Keramik lantai ukuran 60x60 cm</p>
            <span>Luas coverage per box</span>
        </div>
        """
        unit = self.parser.parse_unit(html)
        self.assertEqual(unit, UNIT_CM2)
    
    def test_parse_plumbing_product(self):
        html = """
        <div class="product-spec">
            <h2>Pipa PVC 4 inch</h2>
            <p>Diameter: 4 inch, Panjang: 3 meter</p>
        </div>
        """
        unit = self.parser.parse_unit(html)
        # Should prioritize length units in plumbing context
        self.assertIn(unit, ['INCH', 'M'])
    
    def test_parse_no_unit_found(self):
        html = """
        <div>
            <p>Produk berkualitas tinggi</p>
            <span>Tahan lama dan awet</span>
        </div>
        """
        unit = self.parser.parse_unit(html)
        # Should default to 'PCS' when no unit is found
        self.assertEqual(unit, 'PCS')
    
    def test_empty_html(self):
        unit = self.parser.parse_unit("")
        # Should default to 'PCS' for empty HTML
        self.assertEqual(unit, 'PCS')
    
    def test_none_input(self):
        unit = self.parser.parse_unit(None)
        # Should default to 'PCS' for None input
        self.assertEqual(unit, 'PCS')
    
    def test_invalid_html(self):
        unit = self.parser.parse_unit("Not valid HTML content")
        # Should default to 'PCS' when no unit can be extracted
        self.assertEqual(unit, 'PCS')


class TestErrorHandlingMixin(unittest.TestCase):
    """Test ErrorHandlingMixin methods"""
    
    def test_safe_execute_success(self):
        mixin = ErrorHandlingMixin()
        
        def success_operation():
            return "success"
        
        result = mixin.safe_execute(success_operation, "test operation")
        self.assertEqual(result, "success")
    
    def test_safe_execute_with_exception(self):
        mixin = ErrorHandlingMixin()
        
        def failing_operation():
            raise ValueError("Test error")
        
        result = mixin.safe_execute(failing_operation, "test operation")
        self.assertIsNone(result)
    
    def test_safe_execute_with_default_success(self):
        mixin = ErrorHandlingMixin()
        
        def success_operation():
            return "success"
        
        result = mixin.safe_execute_with_default(success_operation, "default", "test operation")
        self.assertEqual(result, "success")
    
    def test_safe_execute_with_default_exception(self):
        mixin = ErrorHandlingMixin()
        
        def failing_operation():
            raise ValueError("Test error")
        
        result = mixin.safe_execute_with_default(failing_operation, "default_value", "test operation")
        self.assertEqual(result, "default_value")


class TestMitra10UnitParserEdgeCases(unittest.TestCase):
    """Test edge cases in UnitParser"""
    
    def setUp(self):
        self.parser = Mitra10UnitParser()
    
    def test_parse_unit_with_soup_creation_exception(self):
        # Mock BeautifulSoup to raise exception
        with unittest.mock.patch('api.mitra10.unit_parser.BeautifulSoup', side_effect=Exception("Parser error")):
            unit = self.parser.parse_unit("<div>test</div>")
            # Should default to 'PCS' when exception occurs
            self.assertEqual(unit, 'PCS')
    
    def test_extract_specifications_safely_with_empty_result(self):
        html = "<div>No specifications</div>"
        
        # This should handle cases where no specifications are found
        result = self.parser.parse_unit(html)
        # Should default to 'PCS' when no specifications found
        self.assertEqual(result, 'PCS')


class TestHelperAndStrategyCoverage(unittest.TestCase):
    """Additional coverage for helpers and strategy internals"""

    def test_safe_regex_search_and_finditer_error(self):
        self.assertIsNone(TextProcessingHelper.safe_regex_search('(', 'text'))
        self.assertEqual(list(TextProcessingHelper.safe_regex_finditer('(', 'text')), [])

    def test_context_checker_exception(self):
        self.assertFalse(ContextChecker.check_keywords_in_text('some text', None, 'ctx'))

    def test_adjacent_process_match_group_error(self):
        strat = Mitra10AdjacentPatternStrategy()
        # Object without .group attr triggers AttributeError branch in _process_match_group
        self.assertIsNone(strat._process_match_group(object(), 1))


class TestSpecificationFinderCoverage(unittest.TestCase):
    def setUp(self):
        from api.mitra10.unit_parser import Mitra10SpecificationFinder
        self.finder = Mitra10SpecificationFinder()

    def test_find_description_areas_exception(self):
        """Cover _find_description_areas exception branch: returns [] when soup.find_all raises."""
        class Dummy:
            def find_all(self, *args, **kwargs):
                raise RuntimeError()
        self.assertEqual(self.finder._find_description_areas(Dummy()), [])

    def test_extract_text_safely_exception(self):
        # object() has no get_text, should return None
        self.assertIsNone(self.finder._extract_text_safely(object()))

    def test_find_elements_safely_exception(self):
        """Cover _find_elements_safely exception branch: returns [] when find_all raises."""
        class Dummy:
            def find_all(self, *args, **kwargs):
                raise RuntimeError()
        self.assertEqual(self.finder._find_elements_safely(Dummy(), 'table'), [])

    def test_extract_spec_from_row_exception(self):
        """Cover _extract_spec_from_row except path when row.find_all raises."""
        class Row:
            def find_all(self, *args, **kwargs):
                raise AttributeError()
        self.assertIsNone(self.finder._extract_spec_from_row(Row()))

    def test_find_spec_divs_exception(self):
        """Cover _find_spec_divs exception branch: returns [] when soup.find_all raises."""
        class Dummy:
            def find_all(self, *args, **kwargs):
                raise RuntimeError()
        self.assertEqual(self.finder._find_spec_divs(Dummy()), [])
    def test_find_elements_safely_exception(self):
        """Cover _find_elements_safely exception branch (unit_parser: lines 437-439)."""
        class Dummy:
            def find_all(self, *args, **kwargs):
                raise RuntimeError('err')
        self.assertEqual(self.finder._find_elements_safely(Dummy(), 'table'), [])

    def test_extract_spec_from_row_exception(self):
        """Cover _extract_spec_from_row except path (unit_parser: lines 459-461)."""
        class Row:
            def find_all(self, *args, **kwargs):
                raise AttributeError('nope')
        self.assertIsNone(self.finder._extract_spec_from_row(Row()))

    def test_find_spec_divs_exception(self):
        """Cover _find_spec_divs exception branch (unit_parser: lines 482-484)."""
        class Dummy:
            def find_all(self, *args, **kwargs):
                raise RuntimeError('err')
        self.assertEqual(self.finder._find_spec_divs(Dummy()), [])

    def test_is_valid_spec_text_else_branch(self):
        # Unknown element_type path should return False
        self.assertFalse(self.finder._is_valid_spec_text('anything', 'p'))


class TestParserPriorityAndContext(unittest.TestCase):
    def setUp(self):
        from api.mitra10.unit_parser import Mitra10UnitParser
        self.parser = Mitra10UnitParser()

    def test_apply_priority_rules_empty(self):
        # No units found returns None
        self.assertIsNone(self.parser._apply_mitra10_priority_rules([], 'no ctx'))

    def test_general_priority_fallback_first_element(self):
        # If none of the units are in the priority list, return first element
        self.assertEqual(self.parser._get_general_priority_unit(['CUSTOM1', 'CUSTOM2']), 'CUSTOM1')

    def test_fallback_extract_from_full_text(self):
        # Ensure fallback path extracts from full text when specs are absent
        html = '<div>Produk umum tanpa spesifikasi. Isi 2 pcs.</div>'
        self.assertEqual(self.parser.parse_unit(html), 'PCS')


class TestAdditionalCoverageTargets(unittest.TestCase):
    """Extra tests to cover specific uncovered branches/lines."""

    def test_text_processing_helper_truncation(self):
        # Force truncation path in validate_and_clean_text (line ~180)
        long_text = ("abc " * 200) + "tail-unit"
        result = TextProcessingHelper.validate_and_clean_text(long_text, max_length=100)
        # Expect smart truncation indicator and tail preserved
        self.assertIn(" ... ", result)
        self.assertTrue(result.endswith("tail-unit"))

    def test_extractor_standard_pattern_branch(self):
        # Ensure the standard pattern branch (not area/adjacent) is used (~345)
        extractor = Mitra10UnitExtractor()
        # No number before unit to avoid adjacent-pattern path; should hit standard pattern
        text = "berat dalam kg untuk pengujian"
        self.assertEqual(extractor.extract_unit(text), UNIT_KG)

    def test_extractor_no_match_returns_none(self):
        extractor = Mitra10UnitExtractor()
        self.assertIsNone(extractor.extract_unit("teks tanpa satuan apapun"))

    def test_is_valid_spec_text_no_text_branch(self):
        finder = Mitra10SpecificationFinder()
        self.assertFalse(finder._is_valid_spec_text("", "span"))
        # Pass empty string instead of None to match expected argument type (str)
        self.assertFalse(finder._is_valid_spec_text("", "div"))

    def test_context_specific_unit_return_none(self):
        parser = Mitra10UnitParser()
        # Provide some found units but a context string with no keywords
        found_units = ["PCS", "SET"]
        self.assertIsNone(parser._get_context_specific_unit(found_units, "produk umum tanpa konteks"))

    def test_priority_pattern_search_direct_match(self):
        extractor = Mitra10UnitExtractor()
        self.assertEqual(extractor._priority_pattern_search("berat dalam kg untuk pengujian"), UNIT_KG)

    def test_priority_pattern_search_direct_no_match(self):
        extractor = Mitra10UnitExtractor()
        self.assertIsNone(extractor._priority_pattern_search("teks tanpa satuan apapun"))

    def test_priority_pattern_search_whitespace(self):
        extractor = Mitra10UnitExtractor()
        self.assertIsNone(extractor._priority_pattern_search("   \t \n  "))

    def test_plumbing_context_length_preference(self):        
        class StubConfig:
            def is_construction_context(self, _):
                return False
            def is_electrical_context(self, _):
                return False
            def is_plumbing_context(self, _):
                return True

        parser = Mitra10UnitParser(config=StubConfig())
        found_units = ["PCS", "CM", "M"]
        self.assertIn(parser._get_context_specific_unit(found_units, "any html"), ["CM", "M"])

if __name__ == '__main__':
    unittest.main()