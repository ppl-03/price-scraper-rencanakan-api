from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, Client
from .scraper import clean_price_juraganmaterial, scrape_products_from_juraganmaterial_html

class ScraperLogicTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        # Only load the fixture we actually use
        juragan_fp = base / "juragan_material" / "tests" / "juraganmaterial_mock_results.html"
        cls.mock_html_juragan = juragan_fp.read_text(encoding="utf-8")
    
    # NOTE: Legacy tests removed - clean_price_depo and mitra10 functions have been moved to module-specific test files
    
    def test_clean_price_juraganmaterial(self):
        cleaned_price = clean_price_juraganmaterial("Rp 75.000")
        self.assertEqual(cleaned_price, 75000)

    def test_scrape_juraganmaterial(self):
        """Test only Juragan Material scraper functionality"""
        products_juragan = scrape_products_from_juraganmaterial_html(self.mock_html_juragan)
        self.assertIsInstance(products_juragan, list)
        self.assertEqual(len(products_juragan), 3)
        self.assertEqual(products_juragan[0]["name"], "Semen Holcim 40Kg")
        self.assertEqual(products_juragan[0]["price"], 60500)
        self.assertEqual(products_juragan[0]["url"], "/products/semen-holcim-40kg")
        

class ScraperAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_endpoint = '/api/scrape/'

    def test_api_requires_keyword(self):
        response = self.client.get(self.api_endpoint)
        self.assertEqual(response.status_code, 404)