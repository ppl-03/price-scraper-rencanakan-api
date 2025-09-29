from api.test_utils import BaseScraperAPITestCase
from unittest.mock import patch
from api.interfaces import ScrapingResult, Product


class TestJuraganMaterialAPI(BaseScraperAPITestCase):
    """Test cases for Juragan Material API endpoint."""
    
    endpoint_url = '/api/juragan_material/scrape/'
    patch_path = 'api.juragan_material.views.create_juraganmaterial_scraper'
    scraper_name = 'Juragan Material'
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_juragan_material_specific_success_case(self, mock_create_scraper):
        """Test Juragan Material specific success case with custom products."""
        mock_scraper = mock_create_scraper.return_value
        mock_products = [
            Product(name="Semen Holcim 40Kg", price=60500, url="/products/semen-holcim-40kg"),
            Product(name="Pasir Bangunan", price=120000, url="/products/pasir-bangunan-murah")
        ]
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://juraganmaterial.id/produk?keyword=semen"
        )
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get('/api/juragan_material/scrape/', {'keyword': 'semen'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['products']), 2)
        self.assertEqual(data['products'][0]['name'], "Semen Holcim 40Kg")
        self.assertEqual(data['products'][0]['price'], 60500)
        self.assertEqual(data['products'][0]['url'], "/products/semen-holcim-40kg")
        self.assertEqual(data['url'], "https://juraganmaterial.id/produk?keyword=semen")