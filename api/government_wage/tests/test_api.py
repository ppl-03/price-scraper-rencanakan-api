from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json


class GovernmentWageViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_available_regions_success(self):
        """Test successful retrieval of available regions"""
        with patch('api.government_wage.views.create_government_wage_scraper') as mock_create_scraper:
            mock_scraper = MagicMock()
            mock_scraper.get_available_regions.return_value = [
                'Kab. Cilacap', 'Kab. Banyumas', 'Kab. Purbalingga'
            ]
            mock_create_scraper.return_value = mock_scraper
            
            response = self.client.get('/api/government_wage/regions/')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(len(data['regions']), 3)
            self.assertEqual(data['count'], 3)
            self.assertIsNone(data['error_message'])

    def test_scrape_region_data_success(self):
        """Test successful region data scraping"""
        with patch('api.government_wage.views.create_government_wage_scraper') as mock_create_scraper:
            mock_scraper = MagicMock()
            mock_item = MagicMock()
            mock_item.item_number = '1'
            mock_item.work_code = '6.1.1'
            mock_item.work_description = 'Mandor'
            mock_item.unit = 'OH'
            mock_item.unit_price_idr = 150000
            mock_item.region = 'Kab. Cilacap'
            mock_item.edition = 'Edisi Ke - 2'
            mock_item.year = '2024'
            mock_item.sector = 'Bidang Cipta Karya dan Perumahan'
            
            mock_scraper.scrape_region_data.return_value = [mock_item]
            mock_scraper.__enter__.return_value = mock_scraper
            mock_scraper.__exit__.return_value = None
            mock_create_scraper.return_value = mock_scraper
            
            response = self.client.get('/api/government_wage/scrape/?region=Kab. Cilacap')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['region'], 'Kab. Cilacap')
            self.assertEqual(data['count'], 1)
            self.assertEqual(data['data'][0]['work_code'], '6.1.1')

    def test_scrape_region_data_default_region(self):
        """Test region data scraping with default region"""
        with patch('api.government_wage.views.create_government_wage_scraper') as mock_create_scraper:
            mock_scraper = MagicMock()
            mock_scraper.scrape_region_data.return_value = []
            mock_scraper.__enter__.return_value = mock_scraper
            mock_scraper.__exit__.return_value = None
            mock_create_scraper.return_value = mock_scraper
            
            response = self.client.get('/api/government_wage/scrape/')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['region'], 'Kab. Cilacap')  # Default region

    def test_search_by_work_code_success(self):
        """Test successful work code search"""
        with patch('api.government_wage.views.create_government_wage_scraper') as mock_create_scraper:
            mock_scraper = MagicMock()
            mock_item = MagicMock()
            mock_item.item_number = '1'
            mock_item.work_code = '6.1.1'
            mock_item.work_description = 'Mandor'
            mock_item.unit = 'OH'
            mock_item.unit_price_idr = 150000
            mock_item.region = 'Kab. Cilacap'
            mock_item.edition = 'Edisi Ke - 2'
            mock_item.year = '2024'
            mock_item.sector = 'Bidang Cipta Karya dan Perumahan'
            
            mock_scraper.search_by_work_code.return_value = [mock_item]
            mock_scraper.__enter__.return_value = mock_scraper
            mock_scraper.__exit__.return_value = None
            mock_create_scraper.return_value = mock_scraper
            
            response = self.client.get('/api/government_wage/search/?work_code=6.1.1')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['work_code'], '6.1.1')
            self.assertEqual(data['count'], 1)

    def test_search_by_work_code_missing_parameter(self):
        """Test work code search with missing work_code parameter"""
        response = self.client.get('/api/government_wage/search/')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Work code parameter is required')

    def test_search_by_work_code_empty_parameter(self):
        """Test work code search with empty work_code parameter"""
        response = self.client.get('/api/government_wage/search/?work_code=')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Work code parameter is required')

    def test_scrape_region_data_empty_region(self):
        """Test region data scraping with empty region parameter"""
        response = self.client.get('/api/government_wage/scrape/?region=')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Region parameter cannot be empty')

    def test_scrape_all_regions_with_max_limit(self):
        """Test scraping all regions with max limit"""
        with patch('api.government_wage.views.create_government_wage_scraper') as mock_create_scraper:
            mock_scraper = MagicMock()
            mock_scraper.scrape_all_regions.return_value = []
            mock_scraper.__enter__.return_value = mock_scraper
            mock_scraper.__exit__.return_value = None
            mock_create_scraper.return_value = mock_scraper
            
            response = self.client.get('/api/government_wage/scrape-all/?max_regions=5')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['max_regions_requested'], 5)

    def test_scrape_all_regions_invalid_max_limit(self):
        """Test scraping all regions with invalid max limit"""
        response = self.client.get('/api/government_wage/scrape-all/?max_regions=invalid')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Max regions parameter must be a valid integer')

    def test_scrape_all_regions_negative_max_limit(self):
        """Test scraping all regions with negative max limit"""
        response = self.client.get('/api/government_wage/scrape-all/?max_regions=-5')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Max regions parameter must be a positive integer')

    @patch('api.government_wage.views.create_government_wage_scraper')
    def test_scraper_exception_handling(self, mock_create_scraper):
        """Test exception handling in scraper operations"""
        mock_create_scraper.side_effect = Exception('Scraper creation failed')
        
        response = self.client.get('/api/government_wage/regions/')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Internal server error occurred')