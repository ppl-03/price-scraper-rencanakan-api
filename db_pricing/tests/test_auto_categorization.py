from django.test import TestCase
from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct
from db_pricing.categorization import ProductCategorizer


class SteelCategorizationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_besi_beton(self):
        result = self.categorizer.categorize("Besi Beton 10mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_categorize_besi_tulangan(self):
        result = self.categorizer.categorize("Besi Tulangan Polos 12mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_categorize_wiremesh(self):
        result = self.categorizer.categorize("Wiremesh M8 2.10x5.40")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_categorize_baja_ringan(self):
        result = self.categorizer.categorize("Baja Ringan 0.75mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_categorize_hollow(self):
        result = self.categorizer.categorize("Hollow Galvanis 4x4")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_categorize_siku(self):
        result = self.categorizer.categorize("Besi Siku 40x40x4mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_categorize_cnp(self):
        result = self.categorizer.categorize("CNP 100mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_categorize_wf(self):
        result = self.categorizer.categorize("WF 200x200")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_categorize_non_steel_product(self):
        result = self.categorizer.categorize("Semen Portland 50kg")
        self.assertEqual(result, ProductCategorizer.CATEGORY_TANAH_PASIR_BATU_SEMEN)
    
    def test_categorize_another_non_steel(self):
        result = self.categorizer.categorize("Pipa PVC 3 inch")
        self.assertEqual(result, ProductCategorizer.CATEGORY_PIPA_AIR)
    
    def test_case_insensitive(self):
        result = self.categorizer.categorize("BESI BETON 10MM")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_with_extra_spaces(self):
        result = self.categorizer.categorize("  Besi  Beton  10mm  ")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)


class InteriorMaterialCategorizationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_plafon(self):
        result = self.categorizer.categorize("Plafon Gypsum 9mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_gypsum(self):
        result = self.categorizer.categorize("Gypsum Board 12mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_wallpaper(self):
        result = self.categorizer.categorize("Wallpaper Dinding Motif")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_keramik(self):
        result = self.categorizer.categorize("Keramik Lantai 40x40")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_granit(self):
        result = self.categorizer.categorize("Granit Putih 60x60")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_marmer(self):
        result = self.categorizer.categorize("Marmer Import Italy")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_parket(self):
        result = self.categorizer.categorize("Parket Kayu Jati")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_vinyl(self):
        result = self.categorizer.categorize("Vinyl Flooring 3mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_laminate(self):
        result = self.categorizer.categorize("Laminate Flooring Oak")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_klist(self):
        result = self.categorizer.categorize("Klist Dinding PVC")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_ceiling(self):
        result = self.categorizer.categorize("Ceiling Grid System")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_skirting(self):
        result = self.categorizer.categorize("Skirting Board Kayu")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_case_insensitive_interior(self):
        result = self.categorizer.categorize("PLAFON GYPSUM")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_with_extra_spaces_interior(self):
        result = self.categorizer.categorize("  Keramik  Lantai  ")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_non_interior_product(self):
        result = self.categorizer.categorize("Pipa PVC 3 inch")
        self.assertNotEqual(result, ProductCategorizer.CATEGORY_INTERIOR)


class PatternMatchingTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_steel_pattern_with_besi_keyword(self):
        result = self.categorizer.categorize("Wire 10mm Besi")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_steel_pattern_with_baja_keyword(self):
        result = self.categorizer.categorize("Product 8x10 Baja")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_steel_pattern_with_wire_keyword(self):
        result = self.categorizer.categorize("Wire Mesh 5x5")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_steel_pattern_without_keywords(self):
        result = self.categorizer.categorize("Product 10mm")
        self.assertIsNone(result)
    
    def test_steel_pattern_with_metal_keyword(self):
        result = self.categorizer.categorize("Metal Sheet 10mm")
        self.assertEqual(result, ProductCategorizer.CATEGORY_STEEL)
    
    def test_interior_keyword_without_steel_or_exclusion(self):
        result = self.categorizer.categorize("Dinding Premium")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_lantai(self):
        result = self.categorizer.categorize("Lantai Premium")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_flooring(self):
        result = self.categorizer.categorize("Flooring Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_tile(self):
        result = self.categorizer.categorize("Tile Premium")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_ubin(self):
        result = self.categorizer.categorize("Ubin Lantai")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_plafon(self):
        result = self.categorizer.categorize("Plafon Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_gypsum(self):
        result = self.categorizer.categorize("Gypsum Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_keramik(self):
        result = self.categorizer.categorize("Keramik Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_granit(self):
        result = self.categorizer.categorize("Granit Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_marmer(self):
        result = self.categorizer.categorize("Marmer Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_parket(self):
        result = self.categorizer.categorize("Parket Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_vinyl(self):
        result = self.categorizer.categorize("Vinyl Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_laminate(self):
        result = self.categorizer.categorize("Laminate Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_only_without_keyword(self):
        result = self.categorizer.categorize("Material Plafon")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_gypsum_only(self):
        result = self.categorizer.categorize("Product Gypsum")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_not_in_pattern_ceiling(self):
        result = self.categorizer.categorize("Ceiling Material")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_not_in_pattern_glue(self):
        result = self.categorizer.categorize("Glue Product")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_word_boundary(self):
        result = self.categorizer.categorize("abc xyz 123")
        self.assertIsNone(result)
    
    def test_interior_pattern_exact_match(self):
        result = self.categorizer.categorize("plafon")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)


class ExclusionLogicTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_interior_keyword_line_67_ceiling(self):
        result = self.categorizer.categorize("ceiling premium")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_line_67_tiles(self):
        result = self.categorizer.categorize("tiles collection")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_line_67_paint(self):
        result = self.categorizer.categorize("paint berkualitas")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_keyword_line_67_glue(self):
        result = self.categorizer.categorize("glue kuat")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_line_75_exact_plafon(self):
        result = self.categorizer.categorize("jual plafon murah")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_line_75_exact_keramik(self):
        result = self.categorizer.categorize("jual keramik murah")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_interior_pattern_line_75_tapeta(self):
        result = self.categorizer.categorize("jual tapeta premium murah")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_pasir_beton_not_steel(self):
        # "Pasir Beton Berkualitas" should match Tanah/Pasir, not Steel or None
        result = self.categorizer.categorize("Pasir Beton Berkualitas")
        self.assertEqual(result, ProductCategorizer.CATEGORY_TANAH_PASIR_BATU_SEMEN)
    
    def test_semen_with_interior_keyword(self):
        result = self.categorizer.categorize("Semen Cat Dinding")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_pasir_with_keramik(self):
        result = self.categorizer.categorize("Pasir Keramik")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_cat_product(self):
        result = self.categorizer.categorize("Cat Tembok Putih")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_lem_product(self):
        result = self.categorizer.categorize("Lem Kayu Super")
        self.assertEqual(result, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_empty_string(self):
        result = self.categorizer.categorize("")
        self.assertIsNone(result)
    
    def test_none_input(self):
        result = self.categorizer.categorize(None)
        self.assertIsNone(result)
    
    def test_exclusion_without_interior_keyword(self):
        result = self.categorizer.categorize("Pasir Cuci Berkualitas")
        self.assertIsNone(result)
    
    def test_pattern_only_no_match(self):
        result = self.categorizer.categorize("Product 10mm Generic")
        self.assertIsNone(result)
    
    def test_no_keywords_no_patterns(self):
        # "Pipa PVC Generic" should match Material Pipa Air
        result = self.categorizer.categorize("Pipa PVC Generic")
        self.assertEqual(result, ProductCategorizer.CATEGORY_PIPA_AIR)


class AutoCategorizationIntegrationTest(TestCase):
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_gemilang_products(self):
        products = [
            GemilangProduct.objects.create(name="Besi Beton 10mm", price=95000, url="https://test.com/1", unit="batang"),
            GemilangProduct.objects.create(name="Semen Portland", price=65000, url="https://test.com/2", unit="sak"),
            GemilangProduct.objects.create(name="Wiremesh M8", price=120000, url="https://test.com/3", unit="lembar"),
            GemilangProduct.objects.create(name="Keramik Lantai 40x40", price=45000, url="https://test.com/4", unit="dus"),
        ]
        
        results = self.categorizer.categorize_batch([p.name for p in products])
        
        self.assertEqual(results[0], ProductCategorizer.CATEGORY_STEEL)
        self.assertEqual(results[1], ProductCategorizer.CATEGORY_TANAH_PASIR_BATU_SEMEN)
        self.assertEqual(results[2], ProductCategorizer.CATEGORY_STEEL)
        self.assertEqual(results[3], ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_mitra10_products(self):
        products = [
            Mitra10Product.objects.create(name="Baja Ringan 0.75mm", price=35000, url="https://test.com/1", unit="batang"),
            Mitra10Product.objects.create(name="Pipa PVC 3 inch", price=85000, url="https://test.com/2", unit="batang"),
            Mitra10Product.objects.create(name="Plafon Gypsum", price=55000, url="https://test.com/3", unit="lembar"),
        ]
        
        results = self.categorizer.categorize_batch([p.name for p in products])
        
        self.assertEqual(results[0], ProductCategorizer.CATEGORY_STEEL)
        self.assertEqual(results[1], ProductCategorizer.CATEGORY_PIPA_AIR)
        self.assertEqual(results[2], ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_empty_list(self):
        results = self.categorizer.categorize_batch([])
        self.assertEqual(results, [])
    
    def test_categorize_batch_preserves_order(self):
        names = ["Besi Beton", "Semen", "Hollow", "Kabel", "Keramik", "Pipa"]
        results = self.categorizer.categorize_batch(names)
        
        self.assertEqual(len(results), 6)
        self.assertEqual(results[0], ProductCategorizer.CATEGORY_STEEL)
        self.assertEqual(results[1], ProductCategorizer.CATEGORY_TANAH_PASIR_BATU_SEMEN)
        self.assertEqual(results[2], ProductCategorizer.CATEGORY_STEEL)
        self.assertEqual(results[3], ProductCategorizer.CATEGORY_LISTRIK)
        self.assertEqual(results[4], ProductCategorizer.CATEGORY_INTERIOR)
        self.assertEqual(results[5], ProductCategorizer.CATEGORY_PIPA_AIR)


class AutoCategorizationServiceTest(TestCase):
    
    def setUp(self):
        from db_pricing.auto_categorization_service import AutoCategorizationService
        self.service = AutoCategorizationService()
    
    def test_categorize_products_gemilang(self):
        p1 = GemilangProduct.objects.create(name="Besi Beton 10mm", price=95000, url="https://test.com/1", unit="batang")
        p2 = GemilangProduct.objects.create(name="Semen Portland", price=65000, url="https://test.com/2", unit="sak")
        p3 = GemilangProduct.objects.create(name="Keramik Lantai", price=45000, url="https://test.com/3", unit="dus")
        
        result = self.service.categorize_products('gemilang', [p1.id, p2.id, p3.id])
        
        self.assertEqual(result['total'], 3)
        # All 3 should now be categorized (Besi→Steel, Semen→Tanah/Pasir, Keramik→Interior)
        self.assertEqual(result['categorized'], 3)
        self.assertEqual(result['uncategorized'], 0)
        
        p1.refresh_from_db()
        p2.refresh_from_db()
        p3.refresh_from_db()
        
        self.assertEqual(p1.category, ProductCategorizer.CATEGORY_STEEL)
        self.assertEqual(p2.category, ProductCategorizer.CATEGORY_TANAH_PASIR_BATU_SEMEN)
        self.assertEqual(p3.category, ProductCategorizer.CATEGORY_INTERIOR)
    
    def test_categorize_products_mitra10(self):
        p1 = Mitra10Product.objects.create(name="Hollow Galvanis", price=35000, url="https://test.com/1", unit="batang")
        p2 = Mitra10Product.objects.create(name="Plafon Gypsum", price=55000, url="https://test.com/2", unit="lembar")
        
        result = self.service.categorize_products('mitra10', [p1.id, p2.id])
        
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['categorized'], 2)
        self.assertEqual(result['uncategorized'], 0)
    
    def test_categorize_products_depobangunan(self):
        p1 = DepoBangunanProduct.objects.create(name="Wiremesh M8", price=120000, url="https://test.com/1", unit="lembar")
        
        result = self.service.categorize_products('depobangunan', [p1.id])
        
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['categorized'], 1)
    
    def test_categorize_products_juragan_material(self):
        p1 = JuraganMaterialProduct.objects.create(name="Baja Ringan", price=35000, url="https://test.com/1", unit="batang", location="Jakarta")
        
        result = self.service.categorize_products('juragan_material', [p1.id])
        
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['categorized'], 1)
    
    def test_categorize_products_unknown_vendor(self):
        with self.assertRaises(ValueError) as context:
            self.service.categorize_products('unknown_vendor', [1, 2, 3])
        
        self.assertIn("Unknown vendor", str(context.exception))
    
    def test_categorize_all_products_gemilang(self):
        GemilangProduct.objects.create(name="Besi Beton 10mm", price=95000, url="https://test.com/1", unit="batang")
        GemilangProduct.objects.create(name="Semen Portland", price=65000, url="https://test.com/2", unit="sak")
        GemilangProduct.objects.create(name="Keramik Lantai", price=45000, url="https://test.com/3", unit="dus")
        GemilangProduct.objects.create(name="Hollow Galvanis", price=85000, url="https://test.com/4", unit="batang")
        
        result = self.service.categorize_all_products('gemilang')
        
        self.assertEqual(result['total'], 4)
        # All 4 should now be categorized (Besi, Semen, Keramik, Hollow all match categories)
        self.assertEqual(result['categorized'], 4)
        self.assertEqual(result['uncategorized'], 0)
    
    def test_categorize_all_products_mitra10(self):
        Mitra10Product.objects.create(name="Wiremesh M8", price=120000, url="https://test.com/1", unit="lembar")
        Mitra10Product.objects.create(name="Plafon Gypsum", price=55000, url="https://test.com/2", unit="lembar")
        
        result = self.service.categorize_all_products('mitra10')
        
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['categorized'], 2)
        self.assertEqual(result['uncategorized'], 0)
    
    def test_categorize_all_products_unknown_vendor(self):
        with self.assertRaises(ValueError) as context:
            self.service.categorize_all_products('invalid_vendor')
        
        self.assertIn("Unknown vendor", str(context.exception))
    
    def test_categorize_all_products_empty_database(self):
        result = self.service.categorize_all_products('gemilang')
        
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['categorized'], 0)
        self.assertEqual(result['uncategorized'], 0)
