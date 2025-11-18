import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from api.interfaces import ScrapingResult, Product


class TestMitra10API(TestCase):
    """Test cases for Mitra10 API endpoints to achieve near 100% views.py coverage."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = Client()
        self.url = reverse('mitra10:scrape_products')
        
        # Sample product data
        self.sample_products = [
            Product(name='Semen Portland', price=55000, url='/product1'),
            Product(name='Cat Tembok', price=85000, url='/product2')
        ]

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_successful_scraping_basic(self, mock_create_scraper):
        """Test successful product scraping with basic parameters."""
        # Arrange
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=self.sample_products,
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test keyword'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
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
    def test_successful_scraping_with_failed_result(self, mock_create_scraper):
        """Test handling when scraper returns failed result."""
        # Arrange
        mock_scraper = MagicMock()
        failed_result = ScrapingResult(
            success=False,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message='Scraping failed for some reason'
        )
        mock_scraper.scrape_products.return_value = failed_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)  # Still 200, but success=False
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertEqual(response_data['error_message'], 'Scraping failed for some reason')

    def test_missing_query_parameter(self):
        """Test handling when query parameter is missing."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertEqual(response_data['error_message'], 'Query parameter is required')
        self.assertEqual(response_data['url'], '')

    def test_empty_query_parameter(self):
        """Test handling when query parameter is empty."""
        response = self.client.get(self.url, {'q': ''})
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertEqual(response_data['error_message'], 'Query parameter cannot be empty')
        self.assertEqual(response_data['url'], '')

    def test_whitespace_only_query_parameter(self):
        """Test handling when query parameter contains only whitespace."""
        response = self.client.get(self.url, {'q': '   '})
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertEqual(response_data['error_message'], 'Query parameter cannot be empty')
        self.assertEqual(response_data['url'], '')

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_query_whitespace_stripping(self, mock_create_scraper):
        """Test that query parameter whitespace is properly stripped."""
        # Arrange
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': '  test keyword  '})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test keyword',
            sort_by_price=True,
            page=0
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_sort_by_price_true_variations(self, mock_create_scraper):
        """Test different variations of sort_by_price parameter that should be True."""
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper

        # Test different truthy values
        truthy_values = ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES']

        for param_value in truthy_values:
            with self.subTest(param_value=param_value):
                mock_scraper.reset_mock()
                response = self.client.get(self.url, {
                    'q': 'test',
                    'sort_by_price': param_value
                })
                
                self.assertEqual(response.status_code, 200)
                mock_scraper.scrape_products.assert_called_once_with(
                    keyword='test',
                    sort_by_price=True,
                    page=0
                )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_sort_by_price_false_variations(self, mock_create_scraper):
        """Test different variations of sort_by_price parameter that should be False."""
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper

        # Test different falsy values
        falsy_values = ['false', 'False', 'FALSE', '0', 'no', 'No', 'NO', 'invalid', 'random']

        for param_value in falsy_values:
            with self.subTest(param_value=param_value):
                mock_scraper.reset_mock()
                response = self.client.get(self.url, {
                    'q': 'test',
                    'sort_by_price': param_value
                })
                
                self.assertEqual(response.status_code, 200)
                mock_scraper.scrape_products.assert_called_once_with(
                    keyword='test',
                    sort_by_price=False,
                    page=0
                )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_sort_by_price_default_behavior(self, mock_create_scraper):
        """Test default sort_by_price behavior when parameter is not provided."""
        # Arrange
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act - Don't provide sort_by_price parameter
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test',
            sort_by_price=True,  # Default should be True
            page=0
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_page_parameter_valid(self, mock_create_scraper):
        """Test page parameter with valid integer values."""
        # Arrange
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Test different valid page values
        valid_pages = ['0', '1', '5', '10', '100']
        
        for page_str in valid_pages:
            with self.subTest(page=page_str):
                mock_scraper.reset_mock()
                response = self.client.get(self.url, {
                    'q': 'test',
                    'page': page_str
                })
                
                self.assertEqual(response.status_code, 200)
                mock_scraper.scrape_products.assert_called_once_with(
                    keyword='test',
                    sort_by_price=True,
                    page=int(page_str)
                )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_page_parameter_default_behavior(self, mock_create_scraper):
        """Test default page behavior when parameter is not provided."""
        # Arrange
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act - Don't provide page parameter
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='test',
            sort_by_price=True,
            page=0  # Default should be 0
        )

    def test_invalid_page_parameter_various_types(self):
        """Test handling of various invalid page parameter types."""
        invalid_pages = ['invalid', 'abc', '1.5', 'true', '', ' ', 'null', 'undefined']
        
        for invalid_page in invalid_pages:
            with self.subTest(page=invalid_page):
                response = self.client.get(self.url, {'q': 'test', 'page': invalid_page})
                
                self.assertEqual(response.status_code, 400)
                response_data = json.loads(response.content)
                
                self.assertFalse(response_data['success'])
                self.assertEqual(len(response_data['products']), 0)
                self.assertEqual(response_data['error_message'], 'Page parameter must be a valid integer')
                self.assertEqual(response_data['url'], '')

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_product_data_formatting(self, mock_create_scraper):
        """Test that product data is properly formatted in response."""
        # Arrange
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=self.sample_products,
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertEqual(len(response_data['products']), 2)
        
        # Check first product format
        product = response_data['products'][0]
        self.assertIn('name', product)
        self.assertIn('price', product)
        self.assertIn('url', product)
        self.assertEqual(product['name'], 'Semen Portland')
        self.assertEqual(product['price'], 55000)
        self.assertEqual(product['url'], '/product1')

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_empty_products_result(self, mock_create_scraper):
        """Test handling when scraper returns empty product list."""
        # Arrange
        mock_scraper = MagicMock()
        empty_result = ScrapingResult(
            success=True,
            products=[],  # Empty product list
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = empty_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'nonexistent'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['products']), 0)
        self.assertIsNone(response_data['error_message'])

    @patch('api.mitra10.views.create_mitra10_scraper')
    @patch('api.mitra10.views.logger')
    def test_successful_logging(self, mock_logger, mock_create_scraper):
        """Test that successful scraping is logged."""
        # Arrange
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=self.sample_products,
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        mock_logger.info.assert_called_once_with(
            "Mitra10 scraping successful for query 'test': 2 products found"
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    @patch('api.mitra10.views.logger')
    def test_successful_logging_empty_results(self, mock_logger, mock_create_scraper):
        """Test logging when scraping is successful but returns no products."""
        # Arrange
        mock_scraper = MagicMock()
        empty_result = ScrapingResult(
            success=True,
            products=[],
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = empty_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        mock_logger.info.assert_called_once_with(
            "Mitra10 scraping successful for query 'test': 0 products found"
        )

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_scraper_creation_exception(self, mock_create_scraper):
        """Test handling when scraper creation raises an exception."""
        # Arrange
        mock_create_scraper.side_effect = Exception("Failed to create scraper")
        
        # Act
        response = self.client.get(self.url, {'q': 'test keyword'})
        
        # Assert
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error_message', response_data)
        self.assertIn('Internal server error', response_data['error_message'])
        self.assertIn('Failed to create scraper', response_data['error_message'])

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_scraping_execution_exception(self, mock_create_scraper):
        """Test handling when scraping execution raises an exception."""
        # Arrange
        mock_scraper = MagicMock()
        mock_scraper.scrape_products.side_effect = Exception("Scraping execution failed")
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test keyword'})
        
        # Assert
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error_message', response_data)
        self.assertIn('Internal server error', response_data['error_message'])
        self.assertIn('Scraping execution failed', response_data['error_message'])

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

        # Test PATCH method
        response = self.client.patch(self.url, {'q': 'test'})
        self.assertEqual(response.status_code, 405)

    @patch('api.mitra10.views.create_mitra10_scraper')
    def test_response_structure_consistency(self, mock_create_scraper):
        """Test that all responses have consistent structure."""
        # Arrange
        mock_scraper = MagicMock()
        sample_result = ScrapingResult(
            success=True,
            products=self.sample_products,
            url='https://www.mitra10.com/catalogsearch/result/?q=test',
            error_message=None
        )
        mock_scraper.scrape_products.return_value = sample_result
        mock_create_scraper.return_value = mock_scraper
        
        # Act
        response = self.client.get(self.url, {'q': 'test'})
        
        # Assert
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Check all required fields are present
        required_fields = {'success', 'products', 'error_message', 'url'}
        actual_fields = set(response_data.keys())
        self.assertEqual(required_fields, actual_fields)
        
        # Check field types
        self.assertIsInstance(response_data['success'], bool)
        self.assertIsInstance(response_data['products'], list)
        self.assertIsInstance(response_data['url'], str)
        self.assertTrue(
            response_data['error_message'] is None or 
            isinstance(response_data['error_message'], str)
        )