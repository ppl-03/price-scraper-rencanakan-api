from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, Client
from .scraper import clean_price_gemilang, scrape_products_from_gemilang_html, clean_price_depo, scrape_products_from_depo_html, scrape_products_from_depo_html, clean_price_juraganmaterial, scrape_products_from_juraganmaterial_html, clean_price_mitra10, scrape_products_from_mitra10_html

class ScraperLogicTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        fixture_path = base / "tests/fixtures/gemilang_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")
        depo_fp = base / "tests/fixtures/depo_mock_results.html"
        cls.mock_html_depo = depo_fp.read_text(encoding="utf-8")
        juragan_fp = base / "tests/fixtures/juraganmaterial_mock_results.html"
        cls.mock_html_juragan = juragan_fp.read_text(encoding="utf-8")
        mitra_fp = base / "tests/fixtures/mitra10_mock_results.html"
        cls.mock_html_mitra = mitra_fp.read_text(encoding="utf-8")

    def test_clean_price(self):
        cleaned_price = clean_price_gemilang("Rp 55.000")
        self.assertEqual(cleaned_price, 55000)
    
    def test_clean_price_depo(self):
        cleaned_price = clean_price_depo("Rp 125.000")
        self.assertEqual(cleaned_price, 125000)
    
    def test_clean_price_juraganmaterial(self):
        cleaned_price = clean_price_juraganmaterial("Rp 75.000")
        self.assertEqual(cleaned_price, 75000)

    def test_clean_price_mitra10(self):
        cleaned_price = clean_price_mitra10("IDR 12,000")
        self.assertEqual(cleaned_price, 12000)

    def test_scrape_products_returns_a_list(self):
        products = scrape_products_from_gemilang_html(self.mock_html)
        self.assertIsInstance(products, list)
        self.assertEqual(len(products), 2)

        products_depo = scrape_products_from_depo_html(self.mock_html_depo)
        self.assertIsInstance(products_depo, list)
        self.assertEqual(len(products_depo), 2)
        self.assertEqual(products_depo[0]["name"], "Produk A")
        self.assertEqual(products_depo[0]["price"], 3600)
        self.assertTrue(products_depo[0]["url"]) 

        products_juragan = scrape_products_from_juraganmaterial_html(self.mock_html_juragan)
        self.assertIsInstance(products_juragan, list)
        self.assertEqual(len(products_juragan), 3)
        self.assertEqual(products_juragan[0]["name"], "Semen Holcim 40Kg")
        self.assertEqual(products_juragan[0]["price"], 60500)
        self.assertEqual(products_juragan[0]["url"], "/products/semen-holcim-40kg")

        products_mitra10 = scrape_products_from_mitra10_html(self.mock_html_mitra)
        self.assertIsInstance(products_mitra10, list)
        self.assertEqual(len(products_mitra10), 2)
        self.assertEqual(products_mitra10[0]["name"], "Demix Nat Ubin Dasar 1 Kg Ungu Borneo")
        self.assertEqual(products_mitra10[0]["price"], 12000)
        self.assertTrue(products_mitra10[0]["url"])

class ScraperAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_endpoint = '/api/scrape/'

    @patch('api.views.scrape_gemilang_store')
    def test_api_response_is_successful_and_json(self, mock_scraper):
        mock_scraper.return_value = []
        response = self.client.get(self.api_endpoint, {'keyword': 'test'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_requires_keyword(self):
        response = self.client.get(self.api_endpoint)
        self.assertEqual(response.status_code, 400)


