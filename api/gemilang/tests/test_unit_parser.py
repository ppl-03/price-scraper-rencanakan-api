import unittest
from api.gemilang.unit_parser import GemilangUnitParser, UnitExtractor


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


if __name__ == '__main__':
    unittest.main()