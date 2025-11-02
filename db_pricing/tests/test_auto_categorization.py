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
        result = self.categorizer.categorize("Pipa PVC 3 inch")
        self.assertIsNone(result)
    
    def test_case_insensitive(self):
        result = self.categorizer.categorize("BESI BETON 10MM")
        self.assertEqual(result, "Baja dan Besi Tulangan")
    
    def test_with_extra_spaces(self):
        result = self.categorizer.categorize("  Besi  Beton  10mm  ")
        self.assertEqual(result, "Baja dan Besi Tulangan")


class InteriorMaterialCategorizationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_plafon(self):
        result = self.categorizer.categorize("Plafon Gypsum 9mm")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_gypsum(self):
        result = self.categorizer.categorize("Gypsum Board 12mm")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_wallpaper(self):
        result = self.categorizer.categorize("Wallpaper Dinding Motif")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_keramik(self):
        result = self.categorizer.categorize("Keramik Lantai 40x40")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_granit(self):
        result = self.categorizer.categorize("Granit Putih 60x60")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_marmer(self):
        result = self.categorizer.categorize("Marmer Import Italy")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_parket(self):
        result = self.categorizer.categorize("Parket Kayu Jati")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_vinyl(self):
        result = self.categorizer.categorize("Vinyl Flooring 3mm")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_laminate(self):
        result = self.categorizer.categorize("Laminate Flooring Oak")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_klist(self):
        result = self.categorizer.categorize("Klist Dinding PVC")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_ceiling(self):
        result = self.categorizer.categorize("Ceiling Grid System")
        self.assertEqual(result, "Material Interior")
    
    def test_categorize_skirting(self):
        result = self.categorizer.categorize("Skirting Board Kayu")
        self.assertEqual(result, "Material Interior")
    
    def test_case_insensitive_interior(self):
        result = self.categorizer.categorize("PLAFON GYPSUM")
        self.assertEqual(result, "Material Interior")
    
    def test_with_extra_spaces_interior(self):
        result = self.categorizer.categorize("  Keramik  Lantai  ")
        self.assertEqual(result, "Material Interior")
    
    def test_non_interior_product(self):
        result = self.categorizer.categorize("Pipa PVC 3 inch")
        self.assertIsNone(result)


class AutoCategorizationIntegrationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_gemilang_products(self):
        products = [
            GemilangProduct.objects.create(name="Besi Beton 10mm", price=95000, url="http://test.com/1", unit="batang"),
            GemilangProduct.objects.create(name="Semen Portland", price=65000, url="http://test.com/2", unit="sak"),
            GemilangProduct.objects.create(name="Wiremesh M8", price=120000, url="http://test.com/3", unit="lembar"),
            GemilangProduct.objects.create(name="Keramik Lantai 40x40", price=45000, url="http://test.com/4", unit="dus"),
        ]
        
        results = self.categorizer.categorize_batch([p.name for p in products])
        
        self.assertEqual(results[0], "Baja dan Besi Tulangan")
        self.assertIsNone(results[1])
        self.assertEqual(results[2], "Baja dan Besi Tulangan")
        self.assertEqual(results[3], "Material Interior")
    
    def test_categorize_mitra10_products(self):
        products = [
            Mitra10Product.objects.create(name="Baja Ringan 0.75mm", price=35000, url="http://test.com/1", unit="batang"),
            Mitra10Product.objects.create(name="Pipa PVC 3 inch", price=85000, url="http://test.com/2", unit="batang"),
            Mitra10Product.objects.create(name="Plafon Gypsum", price=55000, url="http://test.com/3", unit="lembar"),
        ]
        
        results = self.categorizer.categorize_batch([p.name for p in products])
        
        self.assertEqual(results[0], "Baja dan Besi Tulangan")
        self.assertIsNone(results[1])
        self.assertEqual(results[2], "Material Interior")
    
    def test_categorize_empty_list(self):
        results = self.categorizer.categorize_batch([])
        self.assertEqual(results, [])
    
    def test_categorize_batch_preserves_order(self):
        names = ["Besi Beton", "Semen", "Hollow", "Kabel", "Keramik", "Pipa"]
        results = self.categorizer.categorize_batch(names)
        
        self.assertEqual(len(results), 6)
        self.assertEqual(results[0], "Baja dan Besi Tulangan")
        self.assertIsNone(results[1])
        self.assertEqual(results[2], "Baja dan Besi Tulangan")
        self.assertIsNone(results[3])
        self.assertEqual(results[4], "Material Interior")
        self.assertIsNone(results[5])
