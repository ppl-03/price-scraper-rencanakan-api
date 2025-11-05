import unittest
from bs4 import BeautifulSoup
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
        self.assertIsNone(unit)
    
    def test_empty_html(self):
        unit = self.parser.parse_unit("")
        self.assertIsNone(unit)
    
    def test_none_input(self):
        unit = self.parser.parse_unit(None)
        self.assertIsNone(unit)
    
    def test_invalid_html(self):
        unit = self.parser.parse_unit("Not valid HTML content")
        # Should still try to extract from text
        self.assertIsNone(unit)


class TestErrorHandlingMixin(unittest.TestCase):
    """Test ErrorHandlingMixin methods"""
    
    def test_safe_execute_success(self):
        from api.mitra10.unit_parser import ErrorHandlingMixin
        mixin = ErrorHandlingMixin()
        
        def success_operation():
            return "success"
        
        result = mixin.safe_execute(success_operation, "test operation")
        self.assertEqual(result, "success")
    
    def test_safe_execute_with_exception(self):
        from api.mitra10.unit_parser import ErrorHandlingMixin
        mixin = ErrorHandlingMixin()
        
        def failing_operation():
            raise ValueError("Test error")
        
        result = mixin.safe_execute(failing_operation, "test operation")
        self.assertIsNone(result)
    
    def test_safe_execute_with_default_success(self):
        from api.mitra10.unit_parser import ErrorHandlingMixin
        mixin = ErrorHandlingMixin()
        
        def success_operation():
            return "success"
        
        result = mixin.safe_execute_with_default(success_operation, "default", "test operation")
        self.assertEqual(result, "success")
    
    def test_safe_execute_with_default_exception(self):
        from api.mitra10.unit_parser import ErrorHandlingMixin
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
            self.assertIsNone(unit)
    
    def test_extract_specifications_safely_with_empty_result(self):
        html = "<div>No specifications</div>"
        
        # This should handle cases where no specifications are found
        result = self.parser._parse_unit_from_html(html)
        # Result depends on implementation, just verify it doesn't crash
        self.assertTrue(result is None or isinstance(result, str))


if __name__ == '__main__':
    unittest.main()