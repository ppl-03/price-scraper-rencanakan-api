from api.test_utils import BaseScraperAPITestCase
from unittest.mock import patch, Mock
from api.interfaces import ScrapingResult, Product
from django.test import TestCase, RequestFactory
from api.juragan_material import views


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
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_view_with_all_parameters(self, mock_create_scraper):
        """Test view with all query parameters."""
        mock_scraper = mock_create_scraper.return_value
        mock_products = [Product(name="Test", price=10000, url="/test")]
        mock_result = ScrapingResult(products=mock_products, success=True, url="https://test.com")
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.endpoint_url, {
            'keyword': 'besi',
            'sort_by_price': 'true',
            'page': '2'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='besi',
            sort_by_price=True,
            page=2
        )
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_view_with_false_sort_by_price(self, mock_create_scraper):
        """Test view with sort_by_price=false."""
        mock_scraper = mock_create_scraper.return_value
        mock_result = ScrapingResult(products=[], success=True, url="https://test.com")
        mock_scraper.scrape_products.return_value = mock_result
        
        response = self.client.get(self.endpoint_url, {
            'keyword': 'pasir',
            'sort_by_price': 'false'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='pasir',
            sort_by_price=False,
            page=0
        )
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_view_creates_scraper_on_each_request(self, mock_create_scraper):
        """Test that a new scraper is created for each request."""
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True, url="https://test.com")
        mock_scraper.scrape_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        # Make two requests
        self.client.get(self.endpoint_url, {'keyword': 'test1'})
        self.client.get(self.endpoint_url, {'keyword': 'test2'})
        
        # Scraper factory should be called twice
        self.assertEqual(mock_create_scraper.call_count, 2)
    
    @patch('api.juragan_material.views.handle_scraping_exception')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_view_handles_scraper_exception(self, mock_create_scraper, mock_handle_exception):
        """Test view handles exceptions from scraper."""
        mock_scraper = mock_create_scraper.return_value
        mock_scraper.scrape_products.side_effect = RuntimeError("Scraping failed")
        mock_handle_exception.return_value = Mock(status_code=500, content=b'{"error": "Internal error"}')
        mock_handle_exception.assert_called_once()
        args = mock_handle_exception.call_args[0]
        self.assertIsInstance(args[0], RuntimeError)
        self.assertEqual(args[1], "Juragan Material scraper")


class TestJuraganMaterialViewsDirect(TestCase):
    """Direct tests for views functions without going through URLs."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    @patch('api.juragan_material.views.validate_scraping_request')
    @patch('api.juragan_material.views.format_scraping_response')
    def test_scrape_products_view_success_flow(self, mock_format, mock_validate, mock_create):
        """Test complete success flow of scrape_products view."""
        # Setup mocks
        mock_validate.return_value = ('test keyword', True, 0, None)
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True, url="https://test.com")
        mock_scraper.scrape_products.return_value = mock_result
        mock_create.return_value = mock_scraper
        mock_format.return_value = {'success': True, 'products': []}
        
        # Create request
        request = self.factory.get('/api/juragan_material/scrape/?keyword=test')
        
        # Call view
        response = views.scrape_products(request)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        mock_validate.assert_called_once_with(request)
        mock_create.assert_called_once()
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test keyword',
            sort_by_price=True,
            page=0
        )
        mock_format.assert_called_once_with(mock_result)
    
    @patch('api.juragan_material.views.validate_scraping_request')
    def test_scrape_products_view_validation_error(self, mock_validate):
        """Test scrape_products view with validation error."""
        from django.http import JsonResponse
        error_response = JsonResponse({'error': 'Invalid keyword'}, status=400)
        mock_validate.return_value = (None, None, None, error_response)
        
        request = self.factory.get('/api/juragan_material/scrape/')
        response = views.scrape_products(request)
        
        self.assertEqual(response, error_response)
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    @patch('api.juragan_material.views.validate_scraping_request')
    @patch('api.juragan_material.views.handle_scraping_exception')
    def test_scrape_products_view_exception_handling(self, mock_handle, mock_validate, mock_create):
        """Test scrape_products view exception handling."""
        from django.http import JsonResponse
        
        mock_validate.return_value = ('test', True, 0, None)
        mock_scraper = Mock()
        mock_scraper.scrape_products.side_effect = Exception("Network error")
        mock_create.return_value = mock_scraper
        error_response = JsonResponse({'error': 'Internal error'}, status=500)
        mock_handle.return_value = error_response
        
        request = self.factory.get('/api/juragan_material/scrape/?keyword=test')
        response = views.scrape_products(request)
        
        self.assertEqual(response, error_response)
        mock_handle.assert_called_once()
        args = mock_handle.call_args[0]
        self.assertIsInstance(args[0], Exception)
        self.assertEqual(args[1], "Juragan Material scraper")
    
    def test_scrape_products_view_requires_get(self):
        """Test that scrape_products only accepts GET requests."""
        request = self.factory.post('/api/juragan_material/scrape/')
        response = views.scrape_products(request)
        
        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    @patch('api.juragan_material.views.validate_scraping_request')
    @patch('api.juragan_material.views.format_scraping_response')
    def test_scrape_products_parameters_passed_correctly(self, mock_format, mock_validate, mock_create):
        """Test that parameters are passed correctly to scraper."""
        mock_validate.return_value = ('cement', False, 5, None)
        mock_scraper = Mock()
        mock_result = ScrapingResult(products=[], success=True, url="https://test.com")
        mock_scraper.scrape_products.return_value = mock_result
        mock_create.return_value = mock_scraper
        mock_format.return_value = {'success': True}
        
        request = self.factory.get('/api/juragan_material/scrape/')
        
        # Verify scraper was called with correct parameters
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='cement',
            sort_by_price=False,
            page=5
        )