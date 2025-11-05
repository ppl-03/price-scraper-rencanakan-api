from django.test import TestCase
from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct
from db_pricing.categorization import ProductCategorizer


class PipaAirCategorizationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_pipa_pvc(self):
        result = self.categorizer.categorize("Pipa PVC 3 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_pipa_ppr(self):
        result = self.categorizer.categorize("Pipa PPR 20mm")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_pipa_hdpe(self):
        result = self.categorizer.categorize("Pipa HDPE 1 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_pralon(self):
        result = self.categorizer.categorize("Pralon Pipa Air 1/2 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_elbow(self):
        result = self.categorizer.categorize("Elbow PVC 20mm")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_tee(self):
        result = self.categorizer.categorize("Tee PVC 3/4 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_ball_valve(self):
        result = self.categorizer.categorize("Ball Valve 1 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_gate_valve(self):
        result = self.categorizer.categorize("Gate Valve 2 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_check_valve(self):
        result = self.categorizer.categorize("Check Valve 1/2 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_socket(self):
        result = self.categorizer.categorize("Socket PVC 25mm")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_reducer(self):
        result = self.categorizer.categorize("Reducer 1 inch x 3/4 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_coupling(self):
        result = self.categorizer.categorize("Coupling PVC 20mm")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_flange(self):
        result = self.categorizer.categorize("Flange PVC 3 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_end_cap(self):
        result = self.categorizer.categorize("End Cap PVC 1 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_lem_pvc(self):
        result = self.categorizer.categorize("Lem PVC 250ml")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_teflon(self):
        result = self.categorizer.categorize("Teflon Seal Tape")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_pipa_air_bersih(self):
        result = self.categorizer.categorize("Pipa Air Bersih PVC 1 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_pipa_limbah(self):
        result = self.categorizer.categorize("Pipa Limbah 4 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_non_pipa_product(self):
        result = self.categorizer.categorize("Semen Portland 50kg")
        self.assertNotEqual(result, "Material Pipa Air")
    
    def test_categorize_steel_not_pipa(self):
        result = self.categorizer.categorize("Besi Beton 10mm")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_case_insensitive(self):
        result = self.categorizer.categorize("PIPA PVC 3 INCH")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_with_extra_spaces(self):
        result = self.categorizer.categorize("  Pipa  PVC  1 inch  ")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_union(self):
        result = self.categorizer.categorize("Union PVC 1/2 inch")
        self.assertEqual(result, "Material Pipa Air")
    
    def test_categorize_saddle(self):
        result = self.categorizer.categorize("Saddle Clamp 20mm")
        self.assertEqual(result, "Material Pipa Air")


class PipaAirIntegrationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_gemilang_pipa_products(self):
        products = [
            GemilangProduct.objects.create(name="Pipa PVC 3 inch", price=45000, url="https://test.com/1", unit="batang"),
            GemilangProduct.objects.create(name="Semen Portland", price=65000, url="https://test.com/2", unit="sak"),
            GemilangProduct.objects.create(name="Elbow PVC 20mm", price=5000, url="https://test.com/3", unit="pcs"),
        ]
        
        results = self.categorizer.categorize_batch([p.name for p in products])
        
        self.assertEqual(results[0], "Material Pipa Air")
        self.assertNotEqual(results[1], "Material Pipa Air")
        self.assertEqual(results[2], "Material Pipa Air")
    
    def test_categorize_mitra10_pipa_products(self):
        products = [
            Mitra10Product.objects.create(name="Ball Valve 1 inch", price=35000, url="https://test.com/1", unit="pcs"),
            Mitra10Product.objects.create(name="Cat Kayu", price=85000, url="https://test.com/2", unit="kaleng"),
            Mitra10Product.objects.create(name="Pralon 1/2 inch", price=15000, url="https://test.com/3", unit="batang"),
        ]
        
        results = self.categorizer.categorize_batch([p.name for p in products])
        
        self.assertEqual(results[0], "Material Pipa Air")
        # "Cat Kayu" should match Interior (paint product)
        self.assertEqual(results[1], "Material Interior")
        self.assertEqual(results[2], "Material Pipa Air")
    
    def test_categorize_mixed_categories(self):
        names = ["Pipa PVC", "Besi Beton", "Ball Valve", "Semen", "Elbow PVC"]
        results = self.categorizer.categorize_batch(names)
        
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0], "Material Pipa Air")
        self.assertEqual(results[1], "Baja dan Besi Tulangan")
        self.assertEqual(results[2], "Material Pipa Air")
        self.assertEqual(results[3], "Tanah, Pasir, Batu, dan Semen")
        self.assertEqual(results[4], "Material Pipa Air")
    
    def test_categorize_batch_preserves_order(self):
        names = ["Lem PVC", "Wiremesh", "Reducer", "Cat"]
        results = self.categorizer.categorize_batch(names)
        
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0], "Material Pipa Air")
        self.assertEqual(results[1], "Baja dan Besi Tulangan")
        self.assertEqual(results[2], "Material Pipa Air")
        # "Cat" (paint) should match Interior
        self.assertEqual(results[3], "Material Interior")
    
    def test_categorize_empty_list(self):
        results = self.categorizer.categorize_batch([])
        self.assertEqual(results, [])
