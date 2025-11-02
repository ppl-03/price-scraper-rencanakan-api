from django.test import TestCase
from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct
from db_pricing.categorization import ProductCategorizer


class SteelCategorizationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_besi_beton(self):
        result = self.categorizer.categorize("Besi Beton 10mm")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_categorize_besi_tulangan(self):
        result = self.categorizer.categorize("Besi Tulangan Polos 12mm")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_categorize_wiremesh(self):
        result = self.categorizer.categorize("Wiremesh M8 2.10x5.40")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_categorize_baja_ringan(self):
        result = self.categorizer.categorize("Baja Ringan 0.75mm")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_categorize_hollow(self):
        result = self.categorizer.categorize("Hollow Galvanis 4x4")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_categorize_siku(self):
        result = self.categorizer.categorize("Besi Siku 40x40x4mm")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_categorize_cnp(self):
        result = self.categorizer.categorize("CNP 100mm")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_categorize_wf(self):
        result = self.categorizer.categorize("WF 200x200")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_categorize_non_steel_product(self):
        result = self.categorizer.categorize("Semen Portland 50kg")
        self.assertIsNone(result)
    
    def test_categorize_another_non_steel(self):
        result = self.categorizer.categorize("Cat Tembok Putih")
        self.assertIsNone(result)
    
    def test_case_insensitive(self):
        result = self.categorizer.categorize("BESI BETON 10MM")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_with_extra_spaces(self):
        result = self.categorizer.categorize("  Besi  Beton  10mm  ")
        self.assertEqual(result, "Baja dan Besi Tulangan")


class AutoCategorizationIntegrationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_gemilang_products(self):
        products = [
            GemilangProduct.objects.create(name="Besi Beton 10mm", price=95000, url="http://test.com/1", unit="batang"),
            GemilangProduct.objects.create(name="Semen Portland", price=65000, url="http://test.com/2", unit="sak"),
            GemilangProduct.objects.create(name="Wiremesh M8", price=120000, url="http://test.com/3", unit="lembar"),
        ]
        
        results = self.categorizer.categorize_batch([p.name for p in products])
        
        self.assertEqual(results[0], "Baja dan Besi Tulangan")
        self.assertIsNone(results[1])
        self.assertEqual(results[2], "Baja dan Besi Tulangan")
    
    def test_categorize_mitra10_products(self):
        products = [
            Mitra10Product.objects.create(name="Baja Ringan 0.75mm", price=35000, url="http://test.com/1", unit="batang"),
            Mitra10Product.objects.create(name="Cat Kayu", price=85000, url="http://test.com/2", unit="kaleng"),
        ]
        
        results = self.categorizer.categorize_batch([p.name for p in products])
        
        self.assertEqual(results[0], "Baja dan Besi Tulangan")
        self.assertIsNone(results[1])
    
    def test_categorize_empty_list(self):
        results = self.categorizer.categorize_batch([])
        self.assertEqual(results, [])
    
    def test_categorize_batch_preserves_order(self):
        names = ["Besi Beton", "Semen", "Hollow", "Cat"]
        results = self.categorizer.categorize_batch(names)
        
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0], "Baja dan Besi Tulangan")
        self.assertIsNone(results[1])
        self.assertEqual(results[2], "Baja dan Besi Tulangan")
        self.assertIsNone(results[3])
