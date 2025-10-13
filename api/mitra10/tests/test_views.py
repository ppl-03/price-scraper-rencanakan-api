import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, Mock, MagicMock
from api.interfaces import ScrapingResult, Product
from api.mitra10.location_scraper import Mitra10ScrapingResult


class TestMitra10Views(TestCase):
    def setUp(self):
        self.client = Client()

    def test_scrape_products_success(self):
        """Test successful product scraping"""
        mock_products = [
            Product(name="Test Product 1", price=100000, url="http://example.com/1"),
            Product(name="Test Product 2", price=200000, url="http://example.com/2")
        ]
        
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            error_message=None,
            url="http://mitra10.com/search"
        )

        with patch('api.mitra10.views.create_mitra10_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_products.return_value = mock_result
            mock_factory.return_value = mock_scraper

            response = self.client.get('/api/mitra10/scrape-products/?q=cement')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            self.assertTrue(data['success'])
            self.assertEqual(len(data['products']), 2)
            self.assertEqual(data['products'][0]['name'], "Test Product 1")
            self.assertEqual(data['products'][0]['price'], 100000)
            self.assertEqual(data['products'][1]['name'], "Test Product 2")
            self.assertIsNone(data['error_message'])
            self.assertEqual(data['url'], "http://mitra10.com/search")

    def test_scrape_products_missing_query_parameter(self):
        """Test error when query parameter is missing"""
        response = self.client.get('/api/mitra10/scrape-products/')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['products'], [])
        self.assertEqual(data['error_message'], 'Query parameter is required')
        self.assertEqual(data['url'], '')

    def test_scrape_products_empty_query_parameter(self):
        """Test error when query parameter is empty"""
        response = self.client.get('/api/mitra10/scrape-products/?q=')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['products'], [])
        self.assertEqual(data['error_message'], 'Query parameter cannot be empty')
        self.assertEqual(data['url'], '')

    def test_scrape_products_whitespace_only_query(self):
        """Test error when query parameter contains only whitespace"""
        response = self.client.get('/api/mitra10/scrape-products/?q=   ')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['products'], [])
        self.assertEqual(data['error_message'], 'Query parameter cannot be empty')

    def test_scrape_products_with_sort_by_price_true(self):
        """Test product scraping with sort_by_price=true"""
        mock_result = ScrapingResult(
            products=[],
            success=True,
            error_message=None,
            url="http://test.com"
        )

        with patch('api.mitra10.views.create_mitra10_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_products.return_value = mock_result
            mock_factory.return_value = mock_scraper

            mock_scraper.scrape_products.assert_called_once_with(
                keyword='test',
                sort_by_price=True,
                page=0
            )

    def test_scrape_products_with_sort_by_price_false(self):
        """Test product scraping with sort_by_price=false"""
        mock_result = ScrapingResult(
            products=[],
            success=True,
            error_message=None,
            url="http://test.com"
        )

        with patch('api.mitra10.views.create_mitra10_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_products.return_value = mock_result
            mock_factory.return_value = mock_scraper

            mock_scraper.scrape_products.assert_called_once_with(
                keyword='test',
                sort_by_price=False,
                page=0
            )

    def test_scrape_products_with_sort_by_price_variants(self):
        """Test different sort_by_price parameter values"""
        mock_result = ScrapingResult(
            products=[],
            success=True,
            error_message=None,
            url="http://test.com"
        )

        with patch('api.mitra10.views.create_mitra10_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_products.return_value = mock_result
            mock_factory.return_value = mock_scraper

            # Test '1' (should be True)
            self.client.get('/api/mitra10/scrape-products/?q=test&sort_by_price=1')
            _, kwargs = mock_scraper.scrape_products.call_args
            self.assertTrue(kwargs['sort_by_price'])

            # Test 'yes' (should be True)
            self.client.get('/api/mitra10/scrape-products/?q=test&sort_by_price=yes')
            _, kwargs = mock_scraper.scrape_products.call_args
            self.assertTrue(kwargs['sort_by_price'])

            # Test 'no' (should be False)
            self.client.get('/api/mitra10/scrape-products/?q=test&sort_by_price=no')
            _, kwargs = mock_scraper.scrape_products.call_args
            self.assertFalse(kwargs['sort_by_price'])

    def test_scrape_products_with_valid_page_parameter(self):
        """Test product scraping with valid page parameter"""
        mock_result = ScrapingResult(
            products=[],
            success=True,
            error_message=None,
            url="http://test.com"
        )

        with patch('api.mitra10.views.create_mitra10_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_products.return_value = mock_result
            mock_factory.return_value = mock_scraper

            mock_scraper.scrape_products.assert_called_once_with(
                keyword='test',
                sort_by_price=True,
                page=5
            )

    def test_scrape_products_with_invalid_page_parameter(self):
        """Test error when page parameter is not a valid integer"""
        response = self.client.get('/api/mitra10/scrape-products/?q=test&page=invalid')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['products'], [])
        self.assertEqual(data['error_message'], 'Page parameter must be a valid integer')
        self.assertEqual(data['url'], '')

    def test_scrape_products_with_failure_result(self):
        """Test handling of failed scraping result"""
        mock_result = ScrapingResult(
            products=[],
            success=False,
            error_message="Network timeout",
            url="http://test.com"
        )

        with patch('api.mitra10.views.create_mitra10_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_products.return_value = mock_result
            mock_factory.return_value = mock_scraper

            response = self.client.get('/api/mitra10/scrape-products/?q=test')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            self.assertFalse(data['success'])
            self.assertEqual(data['products'], [])
            self.assertEqual(data['error_message'], "Network timeout")
            self.assertEqual(data['url'], "http://test.com")

    def test_scrape_products_exception_handling(self):
        """Test exception handling in scrape_products view"""
        with patch('api.mitra10.views.create_mitra10_scraper') as mock_factory:
            mock_factory.side_effect = Exception("Unexpected error")

            with patch('api.mitra10.views.logger') as mock_logger:
                response = self.client.get('/api/mitra10/scrape-products/?q=test')

                self.assertEqual(response.status_code, 500)
                data = json.loads(response.content)
                
                self.assertEqual(data['error'], 'Internal server error occurred')
                mock_logger.error.assert_called_once()

    def test_scrape_products_post_method_not_allowed(self):
        """Test that POST method is not allowed for scrape_products"""
        response = self.client.post('/api/mitra10/scrape-products/')
        self.assertEqual(response.status_code, 405)

    def test_scrape_products_query_stripping(self):
        """Test that query parameter is properly stripped of whitespace"""
        mock_result = ScrapingResult(
            products=[],
            success=True,
            error_message=None,
            url="http://test.com"
        )

        with patch('api.mitra10.views.create_mitra10_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_products.return_value = mock_result
            mock_factory.return_value = mock_scraper

            mock_scraper.scrape_products.assert_called_once_with(
                keyword='test query',
                sort_by_price=True,
                page=0
            )

    # Location scraper tests
    def test_scrape_locations_success(self):
        """Test successful location scraping"""
        mock_result = Mitra10ScrapingResult(
            locations=["Jakarta", "Surabaya", "Bandung"],
            success=True,
            error_message=None,
            attempts_made=1
        )

        with patch('api.mitra10.views.create_mitra10_location_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_locations_batch.return_value = mock_result
            mock_factory.return_value = mock_scraper

            response = self.client.get('/api/mitra10/scrape-locations/')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            self.assertTrue(data['success'])
            self.assertEqual(len(data['locations']), 3)
            self.assertEqual(data['locations'][0]['location'], "Jakarta")
            self.assertEqual(data['locations'][1]['location'], "Surabaya")
            self.assertEqual(data['locations'][2]['location'], "Bandung")
            self.assertEqual(data['count'], 3)
            self.assertIsNone(data['error_message'])
            self.assertEqual(data['attempts_made'], 1)
            self.assertEqual(data['source'], 'mitra10_website')

    def test_scrape_locations_with_timeout_parameter(self):
        """Test location scraping with custom timeout"""
        mock_result = Mitra10ScrapingResult(
            locations=[],
            success=True,
            error_message=None,
            attempts_made=1
        )

        with patch('api.mitra10.views.create_mitra10_location_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_locations_batch.return_value = mock_result
            mock_factory.return_value = mock_scraper

            mock_scraper.scrape_locations_batch.assert_called_once_with(timeout=120)

    def test_scrape_locations_with_invalid_timeout_parameter(self):
        """Test error when timeout parameter is not a valid integer"""
        response = self.client.get('/api/mitra10/scrape-locations/?timeout=invalid')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['locations'], [])
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['error_message'], 'Timeout parameter must be a valid integer')

    def test_scrape_locations_with_failure_result(self):
        """Test handling of failed location scraping result"""
        mock_result = Mitra10ScrapingResult(
            locations=[],
            success=False,
            error_message="Failed to load locations",
            attempts_made=3
        )

        with patch('api.mitra10.views.create_mitra10_location_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_locations_batch.return_value = mock_result
            mock_factory.return_value = mock_scraper

            response = self.client.get('/api/mitra10/scrape-locations/')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            self.assertFalse(data['success'])
            self.assertEqual(data['locations'], [])
            self.assertEqual(data['count'], 0)
            self.assertEqual(data['error_message'], "Failed to load locations")
            self.assertEqual(data['attempts_made'], 3)
            self.assertEqual(data['source'], 'mitra10_website')

    def test_scrape_locations_exception_handling(self):
        """Test exception handling in scrape_locations view"""
        with patch('api.mitra10.views.create_mitra10_location_scraper') as mock_factory:
            mock_factory.side_effect = Exception("Unexpected error")

            with patch('api.mitra10.views.logger') as mock_logger:
                response = self.client.get('/api/mitra10/scrape-locations/')

                self.assertEqual(response.status_code, 500)
                data = json.loads(response.content)
                
                self.assertFalse(data['success'])
                self.assertEqual(data['locations'], [])
                self.assertEqual(data['count'], 0)
                self.assertEqual(data['error_message'], 'Internal server error occurred')
                mock_logger.error.assert_called_once()

    def test_scrape_locations_post_method_not_allowed(self):
        """Test that POST method is not allowed for scrape_locations"""
        response = self.client.post('/api/mitra10/scrape-locations/')
        self.assertEqual(response.status_code, 405)

    def test_scrape_locations_default_timeout(self):
        """Test location scraping with default timeout (60)"""
        mock_result = Mitra10ScrapingResult(
            locations=[],
            success=True,
            error_message=None,
            attempts_made=1
        )

        with patch('api.mitra10.views.create_mitra10_location_scraper') as mock_factory:
            mock_scraper = Mock()
            mock_scraper.scrape_locations_batch.return_value = mock_result
            mock_factory.return_value = mock_scraper

            # Should call with timeout=60 (the default from the view)
            mock_scraper.scrape_locations_batch.assert_called_once_with(timeout=60)

    def test_create_error_response_helper(self):
        """Test the _create_error_response helper function"""
        # This is tested indirectly through the error cases above,
        # but we can test it more explicitly by checking the structure
        response = self.client.get('/api/mitra10/scrape-locations/?timeout=invalid')
        
        data = json.loads(response.content)
        
        # Verify the structure matches what _create_error_response should return
        self.assertIn('success', data)
        self.assertIn('locations', data)
        self.assertIn('count', data)
        self.assertIn('error_message', data)
        self.assertFalse(data['success'])
        self.assertEqual(data['locations'], [])
        self.assertEqual(data['count'], 0)
