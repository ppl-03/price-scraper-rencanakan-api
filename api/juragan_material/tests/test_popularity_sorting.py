"""
Tests for JuraganMaterial popularity sorting functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock, Mock
import json
from api.interfaces import Product, ScrapingResult

# Valid API token for testing
TEST_API_TOKEN = 'dev-token-12345'


class JuraganMaterialPopularitySortingTests(TestCase):
    """Test suite for popularity sorting endpoints"""
    
    def setUp(self):
        self.client = Client()
        self.scrape_url = reverse('juragan_material:scrape_products')
        self.scrape_and_save_url = reverse('juragan_material:scrape_and_save_products')
        self.scrape_popularity_url = reverse('juragan_material:scrape_popularity')
    
    def create_mock_product(self, name, price, url, unit='PCS', location='Jakarta'):
        """Helper to create mock product"""
        return Product(
            name=name,
            price=price,
            url=url,
            unit=unit,
            location=location
        )
    
    def create_mock_scraper(self, products, success=True, error_message=None):
        """Helper to create mock scraper"""
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            products=products,
            success=success,
            error_message=error_message,
            url="https://juraganmaterial.id/test"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper.scrape_popularity_products.return_value = mock_result
        return mock_scraper


class TestScrapeAndSaveWithSortType(JuraganMaterialPopularitySortingTests):
    """Tests for scrape_and_save endpoint with sort_type parameter"""
    
    @patch('api.juragan_material.views.JuraganMaterialDatabaseService')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_with_sort_type_cheapest(self, mock_create_scraper, mock_db_service):
        """Test scrape-and-save with sort_type=cheapest saves all products"""
        products = [
            self.create_mock_product('Product A', 10000, '/a'),
            self.create_mock_product('Product B', 20000, '/b'),
            self.create_mock_product('Product C', 30000, '/c'),
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        # Mock database service to return dict format expected by new implementation
        mock_db_instance = Mock()
        mock_db_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 3,
            'updated': 0,
            'anomalies': [],
            'categorized': 0
        }
        mock_db_service.return_value = mock_db_instance
        
        response = self.client.get(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'cheapest'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['sort_type'], 'cheapest')
        self.assertEqual(data['saved'], 3)  # All 3 products saved
        
        # Verify scraper was called with sort_by_price=True
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0
        )
        
        # Verify all products were saved
        mock_db_instance.save_with_price_update.assert_called_once()
        saved_products = mock_db_instance.save_with_price_update.call_args[0][0]
        self.assertEqual(len(saved_products), 3)
    
    @patch('api.juragan_material.views.JuraganMaterialDatabaseService')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_with_sort_type_popularity(self, mock_create_scraper, mock_db_service):
        """Test scrape-and-save with sort_type=popularity saves only top 5 products"""
        products = [
            self.create_mock_product(f'Product {i}', 10000 * i, f'/product-{i}')
            for i in range(1, 11)  # 10 products
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        # Mock database service to return dict format expected by new implementation
        mock_db_instance = Mock()
        mock_db_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 5,
            'updated': 0,
            'anomalies': [],
            'categorized': 0
        }
        mock_db_service.return_value = mock_db_instance
        
        response = self.client.get(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'popularity'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['sort_type'], 'popularity')
        self.assertEqual(data['saved'], 5)  # Only top 5 saved
        
        # Verify scraper was called with sort_by_price=False (relevance)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=False,
            page=0
        )
        
        # Verify only top 5 products were saved
        mock_db_instance.save_with_price_update.assert_called_once()
        saved_products = mock_db_instance.save_with_price_update.call_args[0][0]
        self.assertEqual(len(saved_products), 5)
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_with_default_sort_type(self, mock_create_scraper):
        """Test scrape-and-save defaults to cheapest when sort_type not provided"""
        products = [self.create_mock_product('Product A', 10000, '/a')]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        with patch('api.juragan_material.views.JuraganMaterialDatabaseService') as mock_db_service:
            mock_db_instance = Mock()
            mock_db_instance.save_with_price_update.return_value = {
                'success': True,
                'inserted': 1,
                'updated': 0,
                'anomalies': [],
                'categorized': 0
            }
            mock_db_service.return_value = mock_db_instance
            
            response = self.client.get(self.scrape_and_save_url, {
                'keyword': 'semen'
            }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['sort_type'], 'cheapest')
            
            # Should call with sort_by_price=True (cheapest)
            mock_scraper.scrape_products.assert_called_once_with(
                keyword='semen',
                sort_by_price=True,
                page=0
            )
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_with_invalid_sort_type(self, mock_create_scraper):
        """Test scrape-and-save rejects invalid sort_type"""
        response = self.client.get(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'invalid'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('cheapest', data['error'])
        self.assertIn('popularity', data['error'])
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_missing_keyword(self, mock_create_scraper):
        """Test scrape-and-save requires keyword parameter"""
        response = self.client.get(self.scrape_and_save_url, {
            'sort_type': 'cheapest'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Keyword', data['error'])
    
    @patch('api.juragan_material.views.JuraganMaterialDatabaseService')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_no_products_found(self, mock_create_scraper, mock_db_service):
        """Test scrape-and-save when no products are found"""
        mock_scraper = self.create_mock_scraper([])  # Empty products
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_and_save_url, {
            'keyword': 'nonexistent',
            'sort_type': 'cheapest'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['saved'], 0)
        self.assertIn('No products found', data['message'])
    
    @patch('api.juragan_material.views.JuraganMaterialDatabaseService')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_database_failure(self, mock_create_scraper, mock_db_service):
        """Test scrape-and-save handles database save failure"""
        products = [self.create_mock_product('Product A', 10000, '/a')]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        # Mock database service to fail
        mock_db_instance = Mock()
        mock_db_instance.save.return_value = False
        mock_db_service.return_value = mock_db_instance
        
        response = self.client.get(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'cheapest'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Failed to save', data['error'])


class TestScrapePopularityEndpoint(JuraganMaterialPopularitySortingTests):
    """Tests for scrape_popularity endpoint"""
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_popularity_success(self, mock_create_scraper):
        """Test scrape_popularity returns top N products"""
        products = [
            self.create_mock_product(f'Product {i}', 10000 * i, f'/product-{i}')
            for i in range(1, 11)  # 10 products
        ]
        mock_scraper = MagicMock()
        # Only top 5 returned by scraper
        mock_result = ScrapingResult(
            products=products[:5],
            success=True,
            error_message=None,
            url="https://juraganmaterial.id/test"
        )
        mock_scraper.scrape_popularity_products.return_value = mock_result
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'top_n': '5'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['products']), 5)
        self.assertEqual(data['total_products'], 5)
        
        # Verify scraper was called correctly
        mock_scraper.scrape_popularity_products.assert_called_once_with(
            keyword='semen',
            page=0,
            top_n=5
        )
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_popularity_default_top_n(self, mock_create_scraper):
        """Test scrape_popularity uses default top_n=5"""
        mock_scraper = self.create_mock_scraper([])
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_popularity_products.assert_called_once_with(
            keyword='semen',
            page=0,
            top_n=5
        )
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_popularity_custom_top_n(self, mock_create_scraper):
        """Test scrape_popularity with custom top_n"""
        mock_scraper = self.create_mock_scraper([])
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'top_n': '10'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_popularity_products.assert_called_once_with(
            keyword='semen',
            page=0,
            top_n=10
        )
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_popularity_invalid_top_n(self, mock_create_scraper):
        """Test scrape_popularity with invalid top_n parameter"""
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'top_n': 'invalid'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('top_n', data['error'])
    
    def test_scrape_popularity_missing_keyword(self):
        """Test scrape_popularity requires keyword parameter"""
        response = self.client.get(self.scrape_popularity_url, {}, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Keyword', data['error'])
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_popularity_with_page_parameter(self, mock_create_scraper):
        """Test scrape_popularity with page parameter"""
        mock_scraper = self.create_mock_scraper([])
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'page': '2',
            'top_n': '5'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_popularity_products.assert_called_once_with(
            keyword='semen',
            page=2,
            top_n=5
        )


class TestHelperFunctions(JuraganMaterialPopularitySortingTests):
    """Tests for helper functions"""
    
    def test_validate_sort_type_cheapest(self):
        """Test _validate_sort_type with 'cheapest'"""
        from api.juragan_material.views import _validate_sort_type
        
        sort_type, error = _validate_sort_type('cheapest')
        self.assertEqual(sort_type, 'cheapest')
        self.assertIsNone(error)
    
    def test_validate_sort_type_popularity(self):
        """Test _validate_sort_type with 'popularity'"""
        from api.juragan_material.views import _validate_sort_type
        
        sort_type, error = _validate_sort_type('popularity')
        self.assertEqual(sort_type, 'popularity')
        self.assertIsNone(error)
    
    def test_validate_sort_type_default(self):
        """Test _validate_sort_type with None defaults to 'cheapest'"""
        from api.juragan_material.views import _validate_sort_type
        
        sort_type, error = _validate_sort_type(None)
        self.assertEqual(sort_type, 'cheapest')
        self.assertIsNone(error)
    
    def test_validate_sort_type_invalid(self):
        """Test _validate_sort_type with invalid value"""
        from api.juragan_material.views import _validate_sort_type
        
        sort_type, error = _validate_sort_type('invalid')
        self.assertIsNone(sort_type)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 400)
    
    def test_pick_products_cheapest_returns_all(self):
        """Test _pick_products with cheapest returns all products"""
        from api.juragan_material.views import _pick_products
        
        products = [
            self.create_mock_product(f'Product {i}', 10000 * i, f'/p{i}')
            for i in range(1, 11)
        ]
        
        result = _pick_products('cheapest', products)
        self.assertEqual(len(result), 10)
        self.assertEqual(result, products)
    
    def test_pick_products_popularity_returns_top_5(self):
        """Test _pick_products with popularity returns top 5"""
        from api.juragan_material.views import _pick_products
        
        products = [
            self.create_mock_product(f'Product {i}', 10000 * i, f'/p{i}')
            for i in range(1, 11)
        ]
        
        result = _pick_products('popularity', products)
        self.assertEqual(len(result), 5)
        self.assertEqual(result, products[:5])
    
    def test_pick_products_popularity_with_less_than_5(self):
        """Test _pick_products with popularity when less than 5 products"""
        from api.juragan_material.views import _pick_products
        
        products = [
            self.create_mock_product(f'Product {i}', 10000 * i, f'/p{i}')
            for i in range(1, 4)
        ]
        
        result = _pick_products('popularity', products)
        self.assertEqual(len(result), 3)
        self.assertEqual(result, products)


class TestJuraganMaterialScraperPopularity(JuraganMaterialPopularitySortingTests):
    """Tests for scraper's scrape_popularity_products method"""
    
    @patch('api.juragan_material.scraper.logger')
    def test_scrape_popularity_products_success(self, mock_logger):
        """Test scrape_popularity_products returns top N products"""
        from api.juragan_material.scraper import JuraganMaterialPriceScraper
        
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        
        scraper = JuraganMaterialPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        # Setup mocks
        mock_url_builder.build_search_url.return_value = 'https://juraganmaterial.id/test'
        mock_http_client.get.return_value = '<html>test</html>'
        
        products = [
            self.create_mock_product(f'Product {i}', 10000 * i, f'/product-{i}')
            for i in range(1, 11)  # 10 products
        ]
        mock_html_parser.parse_products.return_value = products
        
        # Execute
        result = scraper.scrape_popularity_products(
            keyword='semen',
            page=0,
            top_n=5
        )
        
        # Assert
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 5)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.url, 'https://juraganmaterial.id/test')
        
        # Verify URL builder called with sort_by_price=False (relevance)
        mock_url_builder.build_search_url.assert_called_once_with(
            'semen',
            sort_by_price=False,
            page=0
        )
        
        # Verify HTTP client called
        mock_http_client.get.assert_called_once_with(
            'https://juraganmaterial.id/test',
            timeout=30
        )
    
    @patch('api.juragan_material.scraper.logger')
    def test_scrape_popularity_products_no_products(self, mock_logger):
        """Test when no products are found"""
        from api.juragan_material.scraper import JuraganMaterialPriceScraper
        
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        
        scraper = JuraganMaterialPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        mock_url_builder.build_search_url.return_value = 'https://test.com'
        mock_http_client.get.return_value = '<html></html>'
        mock_html_parser.parse_products.return_value = []
        
        result = scraper.scrape_popularity_products(
            keyword='nonexistent',
            page=0,
            top_n=5
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 0)
        self.assertEqual(result.error_message, "No products found")
        self.assertEqual(result.url, 'https://test.com')
    
    @patch('api.juragan_material.scraper.logger')
    def test_scrape_popularity_products_http_error(self, mock_logger):
        """Test when HTTP request fails"""
        from api.juragan_material.scraper import JuraganMaterialPriceScraper
        
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        
        scraper = JuraganMaterialPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        mock_url_builder.build_search_url.return_value = 'https://test.com'
        mock_http_client.get.side_effect = Exception("Connection error")
        
        result = scraper.scrape_popularity_products(
            keyword='test',
            page=0,
            top_n=5
        )
        
        self.assertFalse(result.success)
        self.assertEqual(len(result.products), 0)
        self.assertIn("Failed to scrape popularity products", result.error_message)
        self.assertIn("Connection error", result.error_message)
        self.assertIsNone(result.url)
    
    @patch('api.juragan_material.scraper.logger')
    def test_scrape_popularity_products_fewer_than_top_n(self, mock_logger):
        """Test when fewer products than top_n are found"""
        from api.juragan_material.scraper import JuraganMaterialPriceScraper
        
        mock_http_client = Mock()
        mock_url_builder = Mock()
        mock_html_parser = Mock()
        
        scraper = JuraganMaterialPriceScraper(
            http_client=mock_http_client,
            url_builder=mock_url_builder,
            html_parser=mock_html_parser
        )
        
        mock_url_builder.build_search_url.return_value = 'https://test.com'
        mock_http_client.get.return_value = '<html></html>'
        
        products = [
            self.create_mock_product(f'Product {i}', 10000, f'/p{i}')
            for i in range(1, 4)  # Only 3 products
        ]
        mock_html_parser.parse_products.return_value = products
        
        result = scraper.scrape_popularity_products(
            keyword='test',
            page=0,
            top_n=5  # Request 5 but only 3 available
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 3)  # Should return all 3


class TestScrapeAndSaveErrorHandling(JuraganMaterialPopularitySortingTests):
    """Tests for error handling in scrape_and_save"""
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_scraping_failed(self, mock_create_scraper):
        """Test scrape-and-save when scraping fails"""
        mock_scraper = self.create_mock_scraper(
            products=[],
            success=False,
            error_message="Scraping failed"
        )
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'cheapest'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Scraping failed', data['error'])
        self.assertEqual(data['saved'], 0)
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_and_save_invalid_page(self, mock_create_scraper):
        """Test scrape-and-save with invalid page parameter"""
        response = self.client.get(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'cheapest',
            'page': 'invalid'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Page', data['error'])


class TestScrapePopularityErrorHandling(JuraganMaterialPopularitySortingTests):
    """Tests for error handling in scrape_popularity"""
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_popularity_invalid_page(self, mock_create_scraper):
        """Test scrape_popularity with invalid page parameter"""
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'page': 'invalid'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Page', data['error'])
    
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    def test_scrape_popularity_exception(self, mock_create_scraper):
        """Test scrape_popularity handles unexpected exceptions"""
        mock_scraper = Mock()
        mock_scraper.scrape_popularity_products.side_effect = Exception("Unexpected error")
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'top_n': '5'
        }, HTTP_X_API_TOKEN=TEST_API_TOKEN)
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Internal server error', data['error'])
