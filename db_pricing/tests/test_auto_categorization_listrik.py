from django.test import TestCase
from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct
from db_pricing.categorization import ProductCategorizer


class ListrikCategorizationTest(TestCase):
    def setUp(self):
        self.categorizer = ProductCategorizer()

    def test_categorize_kabel(self):
        self.assertEqual(self.categorizer.categorize("Kabel NYY 3x2.5mm"), "Material Listrik")
    
    def test_categorize_saklar(self):
        self.assertEqual(self.categorizer.categorize("Saklar Broco Engkel"), "Material Listrik")

    def test_categorize_mcb(self):
        self.assertEqual(self.categorizer.categorize("MCB Schneider 16A"), "Material Listrik")
    
    def test_categorize_fitting_lampu(self):
        self.assertEqual(self.categorizer.categorize("Fitting Lampu E27"), "Material Listrik")
    
    def test_categorize_stop_kontak(self):
        self.assertEqual(self.categorizer.categorize("Stop Kontak Universal"), "Material Listrik")
    
    def test_non_listrik(self):
        result = self.categorizer.categorize("Semen Portland 50kg")
        self.assertNotEqual(result, "Material Listrik")

    def test_avoid_pipe_false_positive(self):
        # Regular PVC pipe should NOT be categorized as electrical
        result = self.categorizer.categorize("Pipa PVC 1/2 inch")
        self.assertNotEqual(result, "Material Listrik")
    
    def test_bulk_positive_cases(self):
        positives = [
            "Kabel NYYHY 2x1.5mm",
            "Saklar Engkel Broco",
            "Stop Kontak Arde Universal",
            "MCB 10 Ampere Schneider",
            "Fitting Lampu E27 Putih",
            "Pipa Conduit Elektrik 20mm",
            "Junction Box Instalasi",
            "Cable Tie 20cm Hitam",
            "Isolasi Listrik Hitam",
            "Lampu LED 5 Watt",
            "Kabel NYA 2.5mm Merah",
            "Circuit Breaker 32A",
            "Flexible Conduit 16mm"
        ]
        for name in positives:
            with self.subTest(name=name):
                self.assertEqual(self.categorizer.categorize(name), "Material Listrik")
    
    def test_bulk_negative_cases(self):
        """Test that non-electrical products are NOT categorized as 'Material Listrik'"""
        negatives = [
            "Pipa PVC SDR 41 3/4\"",     # Regular plumbing pipe
            "Semen Portland 50kg",        # Construction material
            "Cat Tembok Interior",        # Paint
            "Keramik Lantai 60x60",      # Tiles
            "Besi Hollow 4x4",           # Steel
            "Baut Stainless M8",         # Fastener
            "Tangga Aluminium 2m",       # Ladder
            "Pintu Kayu Panel"           # Door
        ]
        for name in negatives:
            with self.subTest(name=name):
                result = self.categorizer.categorize(name)
                self.assertNotEqual(
                    result, 
                    "Material Listrik",
                    msg=f"'{name}' should NOT be categorized as Material Listrik, but got: {result}"
                )


class ListrikAutoCategorizationIntegrationTest(TestCase):
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_mixed_products(self):
        products = [
            GemilangProduct.objects.create(name="Kabel NYY 3x2.5mm", price=150000, url="https://t/1", unit="meter"),
            Mitra10Product.objects.create(name="Saklar Engkel Broco", price=15000, url="https://t/2", unit="pcs"),
            DepoBangunanProduct.objects.create(name="Cat Kayu", price=85000, url="https://t/3", unit="kaleng"),
            JuraganMaterialProduct.objects.create(name="MCB Schneider 16A", price=35000, url="https://t/4", unit="pcs"),
        ]

        results = self.categorizer.categorize_batch([p.name for p in products])

        self.assertEqual(results[0], "Material Listrik")
        self.assertEqual(results[1], "Material Listrik")
        self.assertNotEqual(results[2], "Material Listrik")
        self.assertEqual(results[3], "Material Listrik")