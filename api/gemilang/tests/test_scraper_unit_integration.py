import unittest
from unittest.mock import Mock, patch
from api.gemilang.scraper import GemilangPriceScraper
from api.gemilang.html_parser import GemilangHtmlParser
from api.gemilang.url_builder import GemilangUrlBuilder
from api.core import BaseHttpClient
from api.interfaces import Product


class TestGemilangScraperUnitIntegration(unittest.TestCase):
    
    def setUp(self):
        self.http_client = Mock()
        self.url_builder = GemilangUrlBuilder()
        self.html_parser = GemilangHtmlParser()
        self.scraper = GemilangPriceScraper(
            self.http_client, 
            self.url_builder, 
            self.html_parser
        )
    
    def test_scrape_products_with_units(self):
        mock_html = """
        <div class="item-product">
            <p class="product-name">Semen Portland 50kg per sak</p>
            <div class="price-wrapper">
                <p class="price">Rp 75,000</p>
            </div>
            <a href="/product/semen-portland-50kg">Details</a>
        </div>
        <div class="item-product">
            <p class="product-name">Keramik 25cm x 40cm</p>
            <div class="price-wrapper">
                <p class="price">Rp 15,000</p>
            </div>
            <a href="/product/keramik-25x40">Details</a>
        </div>
        """
        
        self.http_client.get.return_value = mock_html
        
        result = self.scraper.scrape_products("building materials")
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 2)
        
        product1 = result.products[0]
        self.assertEqual(product1.name, "Semen Portland 50kg per sak")
        self.assertEqual(product1.price, 75000)
        self.assertEqual(product1.unit, "KG")
        self.assertTrue(product1.url.startswith("https://gemilang-store.com"))
        
        product2 = result.products[1]
        self.assertEqual(product2.name, "Keramik 25cm x 40cm")
        self.assertEqual(product2.price, 15000)
        self.assertEqual(product2.unit, "CM")  # Length (CM) has priority over area (CM²) in current algorithm
        self.assertTrue(product2.url.startswith("https://gemilang-store.com"))
    
    def test_scrape_product_details_with_detailed_units(self):
        mock_detail_html = """
        <html>
            <head><title>Pipa PVC Diameter 6 inch - 4 meter</title></head>
            <body>
                <h1>Pipa PVC Diameter 6 inch - 4 meter</h1>
                <div class="price">Rp 125,000</div>
                <table class="specifications">
                    <tr><td>Diameter</td><td>6 inch</td></tr>
                    <tr><td>Panjang</td><td>4 meter</td></tr>
                    <tr><td>Berat</td><td>2.5 kg</td></tr>
                </table>
            </body>
        </html>
        """
        
        self.http_client.get.return_value = mock_detail_html
        
        product = self.scraper.scrape_product_details("https://gemilang-store.com/product/pipa-pvc-6inch-4m")
        
        self.assertIsNotNone(product)
        self.assertEqual(product.name, "Pipa PVC Diameter 6 inch - 4 meter")
        self.assertEqual(product.price, 125000)
        self.assertEqual(product.unit, "KG")  # Weight (KG) has priority over length (INCH) in current algorithm
        self.assertEqual(product.url, "https://gemilang-store.com/product/pipa-pvc-6inch-4m")
    
    def test_scrape_products_mixed_units(self):
        mock_html = """
        <div class="item-product">
            <p class="product-name">Cat Tembok 5 liter</p>
            <div class="price-wrapper"><p class="price">Rp 85,000</p></div>
        </div>
        <div class="item-product">
            <p class="product-name">Lampu LED 15 watt</p>
            <div class="price-wrapper"><p class="price">Rp 25,000</p></div>
        </div>
        <div class="item-product">
            <p class="product-name">Kabel Listrik per meter</p>
            <div class="price-wrapper"><p class="price">Rp 12,000</p></div>
        </div>
        <div class="item-product">
            <p class="product-name">Genteng per lembar</p>
            <div class="price-wrapper"><p class="price">Rp 8,500</p></div>
        </div>
        """
        
        self.http_client.get.return_value = mock_html
        
        result = self.scraper.scrape_products("building supplies")
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 4)
        
        units = [product.unit for product in result.products]
        expected_units = ["LITER", "WATT", "M", "SHEET"]  # "lembar" maps to SHEET in current algorithm
        
        for i, expected_unit in enumerate(expected_units):
            self.assertEqual(units[i], expected_unit, 
                           f"Product {i}: expected {expected_unit}, got {units[i]}")
    
    def test_scrape_products_no_units(self):
        mock_html = """
        <div class="item-product">
            <p class="product-name">Alat Pertukangan Set Lengkap</p>
            <div class="price-wrapper"><p class="price">Rp 450,000</p></div>
        </div>
        <div class="item-product">
            <p class="product-name">Helm Safety Premium</p>
            <div class="price-wrapper"><p class="price">Rp 75,000</p></div>
        </div>
        """
        
        self.http_client.get.return_value = mock_html
        
        result = self.scraper.scrape_products("tools")
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 2)
        
        for product in result.products:
            self.assertIn(product.unit, [None, "SET"])
    
    def test_full_url_generation(self):
        mock_html = """
        <div class="item-product">
            <p class="product-name">Test Product 1</p>
            <div class="price-wrapper"><p class="price">Rp 10,000</p></div>
            <a href="/product/test-1">Details</a>
        </div>
        <div class="item-product">
            <p class="product-name">Test Product 2</p>
            <div class="price-wrapper"><p class="price">Rp 20,000</p></div>
            <a href="product/test-2">Details</a>
        </div>
        <div class="item-product">
            <p class="product-name">Test Product 3</p>
            <div class="price-wrapper"><p class="price">Rp 30,000</p></div>
        </div>
        """
        
        self.http_client.get.return_value = mock_html
        
        result = self.scraper.scrape_products("test")
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 3)
        
        for product in result.products:
            self.assertTrue(product.url.startswith("https://gemilang-store.com"), 
                          f"URL '{product.url}' should start with 'https://gemilang-store.com'")
            self.assertIn("gemilang-store.com", product.url)
            
        self.assertEqual(result.products[0].url, "https://gemilang-store.com/product/test-1")
        self.assertEqual(result.products[1].url, "https://gemilang-store.com/product/test-2")
        self.assertTrue(result.products[2].url.startswith("https://gemilang-store.com/pusat/"))


if __name__ == '__main__':
    unittest.main()