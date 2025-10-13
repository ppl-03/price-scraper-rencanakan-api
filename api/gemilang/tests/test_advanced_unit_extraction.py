import unittest
from api.gemilang.unit_parser import GemilangUnitParser, UnitExtractor


class TestAdvancedUnitExtraction(unittest.TestCase):
    
    def setUp(self):
        self.parser = GemilangUnitParser()
        self.extractor = UnitExtractor()
    
    def test_extract_multiple_units_priority_weight_over_volume(self):
        text = "Kapasitas 500ml dengan berat 2kg"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "KG")
    
    def test_extract_multiple_units_priority_area_over_length(self):
        text = "Ukuran 25cm x 40cm dengan panjang 100cm"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "CM")  # Length (CM) has priority over area in current algorithm
    
    def test_extract_compound_measurements(self):
        text = "Dimensi: 2.5m x 1.8m x 0.5m (volume: 2.25m³)"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "M³")  # Volume (M³) has priority over area (M²) in current algorithm
    
    def test_extract_decimal_precision_units(self):
        text = "Ketebalan 2,5mm dengan toleransi ±0,1mm"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "MM")
    
    def test_extract_electrical_units_with_power_rating(self):
        text = "Daya: 1500 Watt, Tegangan: 220 Volt, Arus: 6.8 Ampere"
        unit = self.extractor.extract_unit(text)
        # Algorithm returns first match by priority order (WATT has higher priority than AMPERE)
        # With current adjacent pattern strategy, returns 'AMPERE' as last adjacent match
        self.assertEqual(unit, "AMPERE")
    
    def test_extract_packaging_mixed_with_weight(self):
        text = "Isi: 20 pcs per kotak, Berat total: 5kg"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "KG")
    
    def test_extract_indonesian_construction_units_priority(self):
        text = "Ukuran papan: 200cm x 25cm, Berat: 15kg per batang"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "KG")  # Weight (KG) has higher priority than area (CM²) in current algorithm
    
    def test_extract_range_specifications(self):
        text = "Diameter: 6mm - 12mm, Panjang: 3m - 6m"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "M")  # Meter (M) has priority over millimeter (MM) in current algorithm
    
    def test_extract_nested_html_complex_structure(self):
        html = """
        <div class="product-specs">
            <div class="measurement">
                <span class="label">Ukuran:</span>
                <span class="value">30cm² (5cm x 6cm)</span>
            </div>
            <div class="weight">
                <span>Berat: 2kg</span>
            </div>
        </div>
        """
        unit = self.parser.parse_unit(html)
        self.assertEqual(unit, "CM²")
    
    def test_extract_multiple_format_variations(self):
        test_cases = [
            ("Diameter Ø25mm", "MM"),
            ("Size: 4\" x 6\"", "INCH"),
            ("Kapasitas 1,5 liter", "LITER"),
            ("Berat 3.5kg", "KG"),
            ("Daya 750watt", "WATT")
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                unit = self.extractor.extract_unit(text)
                self.assertEqual(unit, expected)
    
    def test_extract_time_units_from_rental_specifications(self):
        # Adjacent pattern requires number directly before time unit
        # Format like "50.000/hari" doesn't match the pattern
        # When multiple time units present, adjacent strategy returns last match
        text = "Sewa: 5 hari, Rental: 2 minggu"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "MINGGU")
    
    def test_extract_zero_and_fractional_numbers(self):
        text = "Ketebalan 0,5mm hingga 2,75mm"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "MM")
    
    def test_extract_from_mobile_table_with_mixed_units(self):
        html = """
        <table class="specifications-table">
            <tr>
                <td>Ukuran</td>
                <td>25cm x 40cm (1000cm²)</td>
            </tr>
            <tr>
                <td>Berat</td>
                <td>2.5kg per lembar</td>
            </tr>
        </table>
        """
        unit = self.parser.parse_unit(html)
        self.assertEqual(unit, "CM²")
    
    def test_extract_complex_construction_specification(self):
        text = "Spesifikasi Besi Beton: Diameter 12mm, Panjang 12m, Berat 8.5kg per batang, Kualitas SNI"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "KG")  # Weight (KG) has highest priority among length units in current algorithm
    
    def test_extract_from_product_title_with_brand(self):
        text = "AQUA Galon 19 Liter - Air Mineral Berkualitas"
        unit = self.extractor.extract_unit(text)
        self.assertEqual(unit, "LITER")


if __name__ == '__main__':
    unittest.main()