import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from api.mitra10.scraper import Mitra10PriceScraper
from api.interfaces import ScrapingResult, Product


class TestMitra10API(TestCase):
    """Test cases for Mitra10 API endpoints."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = Client()
        self.url = reverse('mitra10:scrape_products')
        
        # Sample product data matching expected format
        self.sample_products = [
            Product(name='Semen Portland', price=55000, url='https://mitra10.com/product1'),
            Product(name='Cat Tembok', price=85000, url='https://mitra10.com/product2')
        ]
        
        # Sample successful scraping result
        self.sample_result = ScrapingResult(
            success=True,
            products=self.sample_products,
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_successful_scraping(self, mock_create_scraper):
        """Test successful product scraping returns proper format."""
        # Arrange
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.return_value = self.sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test keyword'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertIn('success', response_data)
        self.assertIn('products', response_data)
        self.assertIn('error_message', response_data)
        self.assertIn('url', response_data)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 2)
        self.assertIsNone(response_data['error_message'])
        self.assertIn('mitra10.com', response_data['url'])
        
        # Verify scraper was called correctly
        mock_create_scraper.assert_called_once()
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test keyword',
            sort_by_price=True,
            page=0
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_successful_scraping_with_additional_params(self, mock_create_scraper):
        """Test successful scraping with sorting and pagination parameters."""
        # Arrange
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.return_value = self.sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {
            'q': 'test keyword',
            'sort_by_price': 'false',
            'page': '2'
        })
        
        # Assert
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 2)
        self.assertIsNone(response_data['error_message'])
        
        # Verify scraper was called with correct parameters
        mock_create_scraper.assert_called_once()
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test keyword',
            sort_by_price=False,
            page=2
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_empty_results(self, mock_create_scraper):
        """Test handling when no products are found."""
        # Arrange
        empty_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=nonexistent',
            error_message=None
        )
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.return_value = empty_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'nonexistent product'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertIsNone(response_data['error_message'])

    def test_missing_query_parameter(self):
        """Test handling when query parameter is missing."""
        # Act
        response = self.client.get(self.url)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertEqual(response_data['error_message'], 'Query parameter is required')
        self.assertEqual(response_data['url'], '')

    def test_empty_query_parameter(self):
        """Test handling when query parameter is empty."""
        # Act
        response = self.client.get(self.url, {'q': ''})
        
        # Assert
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertEqual(response_data['error_message'], 'Query parameter cannot be empty')
        self.assertEqual(response_data['url'], '')

    def test_whitespace_only_query_parameter(self):
        """Test handling when query parameter contains only whitespace."""
        # Act
        response = self.client.get(self.url, {'q': '   '})
        
        # Assert
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertEqual(response_data['error_message'], 'Query parameter cannot be empty')
        self.assertEqual(response_data['url'], '')

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_scraper_creation_failure(self, mock_create_scraper):
        """Test handling when scraper creation fails."""
        # Arrange
        mock_create_scraper.side_effect = Exception("Failed to create scraper")
        
        # Act
        response = self.client.get(self.url, {'q': 'test keyword'})
        
        # Assert
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Internal server error occurred')

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_scraping_failure(self, mock_create_scraper):
        """Test handling when scraping process fails."""
        # Arrange
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.side_effect = Exception("Scraping failed")
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test keyword'})
        
        # Assert
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Internal server error occurred')

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_response_format_consistency(self, mock_create_scraper):
        """Test that response format is consistent with Gemilang API."""
        # Arrange
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.return_value = self.sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        
        # Check that response has exactly the expected fields
        expected_fields = {'success', 'products', 'error_message', 'url'}
        actual_fields = set(response_data.keys())
        self.assertEqual(expected_fields, actual_fields)
        
        # Check field types
        self.assertIsInstance(response_data['success'], bool)
        self.assertIsInstance(response_data['products'], list)
        self.assertIsInstance(response_data['url'], str)
        # error_message can be None or string
        self.assertTrue(
            response_data['error_message'] is None or 
            isinstance(response_data['error_message'], str)
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_product_format_consistency(self, mock_create_scraper):
        """Test that product format is consistent."""
        # Arrange
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.return_value = self.sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        products = response_data['products']
        
        for product in products:
            self.assertIn('name', product)
            self.assertIn('price', product)
            self.assertIn('url', product)
            
            self.assertIsInstance(product['name'], str)
            self.assertIsInstance(product['price'], (int, float))
            self.assertIsInstance(product['url'], str)

    def test_method_not_allowed(self):
        """Test that only GET method is allowed."""
        # Test POST method
        response = self.client.post(self.url, {'q': 'test'})
        self.assertEqual(response.status_code, 405)
        
        # Test PUT method  
        response = self.client.put(self.url, {'q': 'test'})
        self.assertEqual(response.status_code, 405)
        
        # Test DELETE method
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 405)

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_url_generation(self, mock_create_scraper):
        """Test that URL is properly generated in response."""
        # Arrange
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.return_value = self.sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'cement'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        generated_url = response_data['url']
        
        # URL should be from the scraping result
        self.assertIn('mitra10.com', generated_url)

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_special_characters_in_query(self, mock_create_scraper):
        """Test handling of special characters in search query."""
        # Arrange
        empty_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test%20%26%20product',
            error_message=None
        )
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.return_value = empty_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test & product'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        
        # Verify scraper was called with the special characters
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test & product',
            sort_by_price=True,
            page=0
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_unicode_characters_in_query(self, mock_create_scraper):
        """Test handling of unicode characters in search query."""
        # Arrange
        empty_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=s%C3%A9m%C3%A9n',
            error_message=None
        )
        mock_scraper = MagicMock(spec=Mitra10PriceScraper)
        mock_scraper.scrape_products.return_value = empty_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'sémén'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify scraper was called with unicode characters
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='sémén',
            sort_by_price=True,
            page=0
        )

    def test_invalid_page_parameter(self):
        """Test handling of invalid page parameter."""
        # Act - Test with non-numeric page parameter
        response = self.client.get(self.url, {'q': 'test', 'page': 'invalid'})
        
        # Assert
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertEqual(response_data['error_message'], 'Page parameter must be a valid integer')
        self.assertEqual(response_data['url'], '')