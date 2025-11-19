from django.test import TestCase
from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct, TokopediaProduct
from db_pricing.categorization import ProductCategorizer


class PeralatanKerjaCategorizationTest(TestCase):
    def setUp(self):
        self.categorizer = ProductCategorizer()

    def test_categorize_palu(self):
        self.assertEqual(self.categorizer.categorize("Palu Besi 1kg"), "Peralatan Kerja")

    def test_categorize_obeng(self):
        self.assertEqual(self.categorizer.categorize("Obeng Set Plus Minus"), "Peralatan Kerja")

    def test_categorize_gergaji(self):
        self.assertEqual(self.categorizer.categorize("Gergaji Kayu 20 inch"), "Peralatan Kerja")

    def test_categorize_meteran(self):
        self.assertEqual(self.categorizer.categorize("Meteran Laser Digital 50m"), "Peralatan Kerja")

    def test_categorize_bor(self):
        self.assertEqual(self.categorizer.categorize("Bor Listrik Impact Drill"), "Peralatan Kerja")

    def test_categorize_tang(self):
        self.assertEqual(self.categorizer.categorize("Tang Kombinasi 8 inch"), "Peralatan Kerja")

    def test_categorize_kunci(self):
        self.assertEqual(self.categorizer.categorize("Kunci Inggris 10 inch"), "Peralatan Kerja")

    def test_categorize_sekop(self):
        self.assertEqual(self.categorizer.categorize("Sekop Taman Besi"), "Peralatan Kerja")

    def test_categorize_waterpass(self):
        self.assertEqual(self.categorizer.categorize("Waterpass Aluminium 60cm"), "Peralatan Kerja")

    def test_non_peralatan_kerja(self):
        # Materials should be categorized to their respective categories
        result = self.categorizer.categorize("Semen Portland 50kg")
        self.assertNotEqual(result, "Peralatan Kerja")

    def test_avoid_material_false_positive(self):
        # Fasteners should not be categorized as tools
        self.assertIsNone(self.categorizer.categorize("Paku 5cm Biasa"))

    def test_bulk_positive_cases(self):
        positives = [
            "Palu Konde 500gr",
            "Palu Besi 1kg",
            "Obeng Ketok",
            "Obeng Plus Minus Set",
            "Tang Potong 8 inch",
            "Tang Kombinasi",
            "Tang Buaya 10 inch",
            "Gergaji Besi Manual",
            "Gergaji Mesin Circular Saw",
            "Gergaji Kayu Tangan",
            "Meteran Gulung 5m",
            "Meteran Dorong Stanley",
            "Meteran Laser Digital",
            "Bor Tangan Manual",
            "Bor Beton Hammer Drill",
            "Bor Listrik Bosch",
            "Gerinda Tangan 4 inch",
            "Gerinda Potong Besi",
            "Mesin Potong Kayu",
            "Pahat Kayu Set",
            "Pahat Beton SDS",
            "Kunci Inggris 10 inch",
            "Kunci Ring Pas Set",
            "Kunci Sok Set 21pcs",
            "Sekop Taman Besi",
            "Cangkul Tanah Gagang Kayu",
            "Linggis Besi 150cm",
            "Waterpass Aluminium 60cm",
            "Waterpass Digital",
            "Siku Tukang 30cm",
            "Penggaris Aluminium 100cm",
            "Ragum Meja 4 inch",
            "Klem F Clamp 12 inch",
            "Tatah Kayu Set 6pcs",
            "Kikir Besi Halus",
            "Amplas Tangan",
            "Gunting Seng 12 inch",
            "Timba Cor Plastik",
            "Ember Cat 20L",
            "Roskam Kayu",
            "Sendok Semen Tukang",
        ]
        for name in positives:
            with self.subTest(name=name):
                self.assertEqual(self.categorizer.categorize(name), "Peralatan Kerja")

    def test_bulk_negative_cases(self):
        negatives = [
            "Paku 5cm Biasa",
            "Mur Baut M10",
            "Sekrup 4x40mm",
            "Semen Portland 50kg",
            "Cat Tembok Interior",
            "Keramik Lantai 60x60",
            "Besi Beton 10mm",
            "Pipa PVC 3/4 inch",
            "Kabel NYM 2x2.5mm",
            "Closet Duduk Toto",
            "Kran Air Dapur",
            "Pintu Kayu Panel",
            "Engsel Pintu Stainless",
            "Pasir Beton",
            "Batu Split 2/3",
        ]
        for name in negatives:
            with self.subTest(name=name):
                self.assertNotEqual(self.categorizer.categorize(name), "Peralatan Kerja")


class PeralatanKerjaAutoCategorizationIntegrationTest(TestCase):
    def setUp(self):
        self.categorizer = ProductCategorizer()

    def test_categorize_mixed_products(self):
        products = [
            GemilangProduct.objects.create(name="Palu Besi 1kg", price=35000, url="https://t/1", unit="pcs"),
            Mitra10Product.objects.create(name="Obeng Set 6pcs", price=45000, url="https://t/2", unit="set"),
            DepoBangunanProduct.objects.create(name="Semen Gresik", price=65000, url="https://t/3", unit="sak"),
            JuraganMaterialProduct.objects.create(name="Tang Kombinasi 8 inch", price=55000, url="https://t/4", unit="unit"),
            TokopediaProduct.objects.create(name="Gergaji Besi Manual", price=40000, url="https://t/5", unit="unit"),
        ]

        results = self.categorizer.categorize_batch([p.name for p in products])

        self.assertEqual(results[0], "Peralatan Kerja")
        # "Obeng Set 6pcs" should match Peralatan Kerja
        self.assertEqual(results[1], "Peralatan Kerja")
        self.assertEqual(results[2], "Tanah, Pasir, Batu, dan Semen")  # Semen is material, not tool
        self.assertEqual(results[3], "Peralatan Kerja")

    def test_categorize_all_tool_types(self):
        products = [
            GemilangProduct.objects.create(name="Palu Konde", price=35000, url="https://t/1", unit="unit"),
            Mitra10Product.objects.create(name="Gergaji Kayu", price=45000, url="https://t/2", unit="unit"),
            DepoBangunanProduct.objects.create(name="Meteran 5m", price=25000, url="https://t/3", unit="unit"),
            JuraganMaterialProduct.objects.create(name="Kunci Inggris", price=65000, url="https://t/4", unit="unit"),
            TokopediaProduct.objects.create(name="Bor Listrik", price=150000, url="https://t/5", unit="unit"),
        ]

        results = self.categorizer.categorize_batch([p.name for p in products])

        for result in results:
            self.assertEqual(result, "Peralatan Kerja")

    def test_categorize_empty_list(self):
        results = self.categorizer.categorize_batch([])
        self.assertEqual(results, [])

    def test_categorize_batch_preserves_order(self):
        names = ["Palu Besi", "Semen Portland", "Obeng Set", "Pasir Beton", "Tang Potong"]
        results = self.categorizer.categorize_batch(names)

        self.assertEqual(len(results), 5)
        self.assertEqual(results[0], "Peralatan Kerja")
        self.assertEqual(results[1], "Tanah, Pasir, Batu, dan Semen")  # Semen is material
        self.assertEqual(results[2], "Peralatan Kerja")
        self.assertEqual(results[3], "Tanah, Pasir, Batu, dan Semen")  # Pasir is material
        self.assertEqual(results[4], "Peralatan Kerja")
