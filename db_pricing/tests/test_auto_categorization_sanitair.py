from django.test import TestCase
from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct, TokopediaProduct
from db_pricing.categorization import ProductCategorizer


class SanitairCategorizationTest(TestCase):
    def setUp(self):
        self.categorizer = ProductCategorizer()

    def test_categorize_closet(self):
        self.assertEqual(self.categorizer.categorize("Closet Duduk Toto Eco"), "Material Sanitair")

    def test_categorize_kran(self):
        self.assertEqual(self.categorizer.categorize("Kran Air Dapur Stainless"), "Material Sanitair")

    def test_categorize_shower_set(self):
        self.assertEqual(self.categorizer.categorize("Shower Set Chrome"), "Material Sanitair")

    def test_categorize_wastafel(self):
        self.assertEqual(self.categorizer.categorize("Wastafel Keramik Putih"), "Material Sanitair")

    def test_categorize_floor_drain(self):
        self.assertEqual(self.categorizer.categorize("Floor Drain 4 inch Stainless"), "Material Sanitair")

    def test_non_sanitair(self):
        self.assertNotEqual(self.categorizer.categorize("Cat Tembok Eksterior"), "Material Sanitair")

    def test_avoid_pipe_false_positive(self):
        self.assertNotEqual(self.categorizer.categorize("Pipa PVC 1/2 inch"), "Material Sanitair")

    def test_bulk_positive_cases(self):
        positives = [
            "Closet Jongkok Putih",
            "Toilet Bowl One Piece",
            "Wastafel Cuci Tangan Minimalis",
            "Kran Air Panas Dingin Mixer",
            "Keran Taman Brass 1/2",
            "Faucet Dapur Chrome",
            "Shower Set Rainshower",
            "Hand Shower 5 Mode",
            "Bidet Spray Stainless",
            "Urinoir Dinding",
            "Floor Drain Anti Bau",
            "P-Trap Siphon Wastafel",
            "Flexible Hose 1/2 x 50cm",
            "Paper Holder Stainless",
            "Soap Dispenser Dinding",
            "Cermin Kamar Mandi Bundar",
            "TOTO Shower Head",
            "American Standard Mixer",
            "Wasser Stop Kran"
        ]
        for name in positives:
            with self.subTest(name=name):
                self.assertEqual(self.categorizer.categorize(name), "Material Sanitair")

    def test_bulk_negative_cases(self):
        negatives = [
            "Pipa PVC SDR 41 3/4\"", 
            "Conduit Pipa Listrik 20mm",
            "Semen Portland 50kg",
            "Cat Tembok Interior",
            "Keramik Lantai 60x60",
            "Besi Hollow 4x4",
            "Baut Stainless M8",
            "Kabel NYA 2.5mm",
            "Tangga Aluminium 2m",
            "Pintu Kayu Panel",
            "Engsel Pintu Stainless",
            "Plafon Gypsum 9mm"
        ]
        for name in negatives:
            with self.subTest(name=name):
                self.assertNotEqual(self.categorizer.categorize(name), "Material Sanitair")


class SanitairAutoCategorizationIntegrationTest(TestCase):
    def setUp(self):
        self.categorizer = ProductCategorizer()

    def test_categorize_mixed_products(self):
        products = [
            GemilangProduct.objects.create(name="Closet Jongkok INA", price=350000, url="https://t/1", unit="unit"),
            Mitra10Product.objects.create(name="Shower Set Minimalis", price=150000, url="https://t/2", unit="set"),
            DepoBangunanProduct.objects.create(name="Cat Kayu", price=85000, url="https://t/3", unit="kaleng"),
            JuraganMaterialProduct.objects.create(name="Kran Air Wastafel", price=95000, url="https://t/4", unit="unit"),
            TokopediaProduct.objects.create(name="Bidet Spray Stainless", price=120000, url="https://t/5", unit="unit"),
        ]

        results = self.categorizer.categorize_batch([p.name for p in products])

        self.assertEqual(results[0], "Material Sanitair")
        self.assertEqual(results[1], "Material Sanitair")
        self.assertNotEqual(results[2], "Material Sanitair")
        self.assertEqual(results[3], "Material Sanitair")
