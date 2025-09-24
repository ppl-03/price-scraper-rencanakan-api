from unittest import TestCase
from unittest.mock import Mock, patch
from pathlib import Path
from api.interfaces import IPriceScraper, HttpClientError, Product
from api.juragan_material.factory import create_juraganmaterial_scraper
from api.juragan_material.scraper import JuraganMaterialPriceScraper
from api.juragan_material.url_builder import JuraganMaterialUrlBuilder
from api.juragan_material.html_parser import JuraganMaterialHtmlParser
from api.core import BaseHttpClient


class TestJuraganMaterialIntegration(TestCase):
    """Integration tests for Juragan Material scraper."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent.parent.parent
        fixture_path = base / "tests/fixtures/juraganmaterial_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")
    
    def setUp(self):
        self.mock_http_client = Mock(spec=BaseHttpClient)
        self.url_builder = JuraganMaterialUrlBuilder()
        self.html_parser = JuraganMaterialHtmlParser()
        self.scraper = JuraganMaterialPriceScraper(
            self.mock_http_client,
            self.url_builder,
            self.html_parser
        )
    
    def test_complete_scraping_pipeline_success(self):
        """Test the complete scraping pipeline with successful result."""
        keyword = "semen"
        self.mock_http_client.get.return_value = self.mock_html
        
        result = self.scraper.scrape_products(keyword)
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertIsNotNone(result.url)
        self.assertIn("keyword=semen", result.url)
        self.assertIn("sort=lowest_price", result.url)
        
        self.assertEqual(len(result.products), 3)
        
        product1 = result.products[0]
        self.assertEqual(product1.name, "Semen Holcim 40Kg")
        self.assertEqual(product1.price, 60500)
        self.assertEqual(product1.url, "/products/semen-holcim-40kg")
    
    def test_factory_function(self):
        """Test the factory function creates proper scraper instance."""
        scraper = create_juraganmaterial_scraper()
        self.assertIsInstance(scraper, IPriceScraper)
        self.assertIsInstance(scraper, JuraganMaterialPriceScraper)
        self.assertIsNotNone(scraper.http_client)
        self.assertIsNotNone(scraper.url_builder)
        self.assertIsNotNone(scraper.html_parser)