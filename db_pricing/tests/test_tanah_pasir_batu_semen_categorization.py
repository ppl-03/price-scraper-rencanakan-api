from django.test import TestCase
from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct
from db_pricing.categorization import ProductCategorizer


class TanahPasirBatuSemenCategorizationTest(TestCase):
    def setUp(self):
        self.categorizer = ProductCategorizer()

    def test_categorize_semen_portland(self):
        self.assertEqual(self.categorizer.categorize("Semen Portland 50kg"), "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_semen_putih(self):
        self.assertEqual(self.categorizer.categorize("Semen Putih 40kg"), "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_pasir_pasang(self):
        self.assertEqual(self.categorizer.categorize("Pasir Pasang per Kubik"), "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_pasir_beton(self):
        self.assertEqual(self.categorizer.categorize("Pasir Beton Curah"), "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_batu_split(self):
        self.assertEqual(self.categorizer.categorize("Batu Split 1/2"), "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_batu_kali(self):
        self.assertEqual(self.categorizer.categorize("Batu Kali Belah"), "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_kerikil(self):
        self.assertEqual(self.categorizer.categorize("Kerikil Halus 1m3"), "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_tanah_urug(self):
        self.assertEqual(self.categorizer.categorize("Tanah Urug per Truk"), "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_tanah_merah(self):
        self.assertEqual(self.categorizer.categorize("Tanah Merah Subur"), "Tanah, Pasir, Batu, dan Semen")

    def test_non_tanah_pasir_batu_semen(self):
        # "Cat Tembok Interior" should match Interior category, not Tanah/Pasir
        result = self.categorizer.categorize("Cat Tembok Interior")
        self.assertNotEqual(result, "Tanah, Pasir, Batu, dan Semen")

    def test_avoid_false_positive(self):
        # "Keramik Batu Alam" should match Interior (keramik), not Tanah/Pasir (batu)
        result = self.categorizer.categorize("Keramik Batu Alam")
        self.assertNotEqual(result, "Tanah, Pasir, Batu, dan Semen")

    def test_bulk_positive_cases(self):
        positives = [
            "Semen Portland Tiga Roda 50kg",
            "Semen Gresik Putih 40kg",
            "Semen Baturaja Abu-abu",
            "Semen Instan Mortar",
            "Pasir Pasang Bangunan",
            "Pasir Beton Cor Halus",
            "Pasir Urug per m3",
            "Pasir Silika",
            "Batu Split 2/3 per Kubik",
            "Batu Split 1/2 Curah",
            "Batu Kali Bulat",
            "Batu Belah Pondasi",
            "Batu Koral Besar",
            "Kerikil Beton",
            "Sirtu per Truk",
            "Tanah Urug Merah",
            "Tanah Hitam Subur",
            "Tanah Liat",
            "Abu Batu",
            "Agregat Halus"
        ]
        for name in positives:
            with self.subTest(name=name):
                self.assertEqual(self.categorizer.categorize(name), "Tanah, Pasir, Batu, dan Semen")

    def test_bulk_negative_cases(self):
        negatives = [
            "Keramik Lantai Batu Alam",
            "Cat Pasir Warna Abu",
            "Batu Baterai AA",
            "Tanaman Hias Pot",
            "Pipa PVC 3 inch",
            "Cat Tembok Putih",
            "Kabel NYA 2.5mm",
            "Pintu Kayu Solid",
            "Genteng Keramik",
            "Plafon Gypsum",
            "Closet Duduk TOTO"
        ]
        for name in negatives:
            with self.subTest(name=name):
                self.assertNotEqual(self.categorizer.categorize(name),"Tanah, Pasir, Batu, dan Semen")


class TanahPasirBatuSemenAutoCategorizationIntegrationTest(TestCase):
    def setUp(self):
        self.categorizer = ProductCategorizer()

    def test_categorize_mixed_products(self):
        products = [
            GemilangProduct.objects.create(name="Semen Portland 50kg", price=65000, url="https://t/1", unit="sak"),
            Mitra10Product.objects.create(name="Pasir Beton per m3", price=250000, url="https://t/2", unit="kubik"),
            DepoBangunanProduct.objects.create(name="Cat Kayu Jati", price=85000, url="https://t/3", unit="kaleng"),
            JuraganMaterialProduct.objects.create(name="Batu Split 2/3", price=300000, url="https://t/4", unit="kubik"),
        ]

        results = self.categorizer.categorize_batch([p.name for p in products])

        self.assertEqual(results[0], "Tanah, Pasir, Batu, dan Semen")
        self.assertEqual(results[1], "Tanah, Pasir, Batu, dan Semen")
        # "Cat Kayu Jati" is a paint product, should match Interior
        self.assertEqual(results[2], "Material Interior")
        self.assertEqual(results[3], "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_all_subcategories(self):
        products = [
            GemilangProduct.objects.create(name="Semen Gresik", price=60000, url="https://t/1", unit="sak"),
            Mitra10Product.objects.create(name="Pasir Pasang", price=200000, url="https://t/2", unit="m3"),
            DepoBangunanProduct.objects.create(name="Batu Kali", price=180000, url="https://t/3", unit="m3"),
            JuraganMaterialProduct.objects.create(name="Tanah Urug", price=150000, url="https://t/4", unit="truk"),
        ]

        results = self.categorizer.categorize_batch([p.name for p in products])

        for result in results:
            self.assertEqual(result, "Tanah, Pasir, Batu, dan Semen")

    def test_categorize_empty_list(self):
        results = self.categorizer.categorize_batch([])
        self.assertEqual(results, [])

    def test_categorize_batch_preserves_order(self):
        names = ["Semen Portland", "Cat Tembok", "Batu Split", "Pasir Beton", "Keramik"]
        results = self.categorizer.categorize_batch(names)

        self.assertEqual(len(results), 5)
        self.assertEqual(results[0], "Tanah, Pasir, Batu, dan Semen")
        # "Cat Tembok" is interior paint, should match Interior
        self.assertEqual(results[1], "Material Interior")
        self.assertEqual(results[2], "Tanah, Pasir, Batu, dan Semen")
        self.assertEqual(results[3], "Tanah, Pasir, Batu, dan Semen")
        # "Keramik" is ceramic tiles, should match Interior
        self.assertEqual(results[4], "Material Interior")
