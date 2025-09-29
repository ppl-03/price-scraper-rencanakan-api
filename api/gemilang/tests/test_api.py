from api.test_utils import BaseScraperAPITestCase
from unittest.mock import patch
from api.interfaces import ScrapingResult, Product


class TestGemilangAPI(BaseScraperAPITestCase):
    """Test cases for Gemilang API endpoint."""
    
    endpoint_url = '/api/gemilang/scrape/'
    patch_path = 'api.gemilang.views.create_gemilang_scraper'
    scraper_name = 'Gemilang'
    
    @patch('api.gemilang.views.create_gemilang_scraper')
    def test_gemilang_specific_success_case(self, mock_create_scraper):
        """Test Gemilang specific success case with custom products."""
        mock_scraper = mock_create_scraper.return_value
        mock_products = [
            Product(name="Gemilang Product 1", price=15000, url="/gemilang-product1"),
            Product(name="Gemilang Product 2", price=25000, url="/gemilang-product2")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://gemilang.co.id/search?keyword=test"
        )
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get('/api/gemilang/scrape/', {'keyword': 'test'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['products']), 2)
        self.assertEqual(data['products'][0]['name'], "Gemilang Product 1")
        self.assertEqual(data['products'][0]['price'], 15000)
        self.assertEqual(data['products'][0]['url'], "/gemilang-product1")
        self.assertEqual(data['url'], "https://gemilang.co.id/search?keyword=test")