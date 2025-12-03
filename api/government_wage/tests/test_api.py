from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json


class GovernmentWageViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Mock the new file caching functions
        self.cache_patcher = patch('api.government_wage.views.get_cached_or_scrape')
        self.mock_get_cached = self.cache_patcher.start()
        # Default: return empty list (will be overridden in individual tests)
        self.mock_get_cached.return_value = []
    
    def tearDown(self):
        self.cache_patcher.stop()

    def test_get_available_regions_success(self):
        """Test successful retrieval of available regions"""
        # GovernmentWageScraper is imported inside the view function, so patch it there
        with patch('api.government_wage.scraper.GovernmentWageScraper') as MockScraper:
            mock_instance = MagicMock()
            mock_instance.get_available_regions.return_value = [
                'Kab. Cilacap', 'Kab. Banyumas', 'Kab. Purbalingga'
            ]
            MockScraper.return_value = mock_instance
            
            response = self.client.get('/api/government_wage/regions/')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(len(data['regions']), 3)
            self.assertEqual(data['count'], 3)
            self.assertIsNone(data['error_message'])

    def test_scrape_region_data_success(self):
        """Test successful region data scraping"""
        # Mock get_cached_or_scrape to return test data
        mock_item = MagicMock()
        mock_item.item_number = '1'
        mock_item.work_code = '6.1.1'
        mock_item.work_description = 'Mandor'
        mock_item.unit = 'OH'
        mock_item.unit_price_idr = 150000
        mock_item.region = 'Kab. Cilacap'
        mock_item.edition = 'Edisi Ke - 2'
        mock_item.year = '2025'
        mock_item.sector = 'Bidang Cipta Karya dan Perumahan'
        
        self.mock_get_cached.return_value = [mock_item]
        
        response = self.client.get('/api/government_wage/scrape/?region=Kab. Cilacap')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['region'], 'Kab. Cilacap')
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['data'][0]['work_code'], '6.1.1')
        
        # Verify get_cached_or_scrape was called
        self.mock_get_cached.assert_called_once()

    def test_scrape_region_data_cache_hit(self):
        """Test region data scraping with cached data"""
        # Mock cached data
        mock_item = MagicMock()
        mock_item.item_number = '1'
        mock_item.work_code = '6.1.1'
        mock_item.work_description = 'Mandor'
        mock_item.unit = 'OH'
        mock_item.unit_price_idr = 150000
        mock_item.region = 'Kab. Cilacap'
        mock_item.edition = 'Edisi Ke - 2'
        mock_item.year = '2025'
        mock_item.sector = 'Bidang Cipta Karya dan Perumahan'
        
        self.mock_get_cached.return_value = [mock_item]
        
        response = self.client.get('/api/government_wage/scrape/?region=Kab. Cilacap')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['region'], 'Kab. Cilacap')
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['data'][0]['work_code'], '6.1.1')

    def test_scrape_region_data_default_region(self):
        """Test region data scraping with default region"""
        # Mock empty data for default region
        self.mock_get_cached.return_value = []
        
        response = self.client.get('/api/government_wage/scrape/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['region'], 'Kab. Cilacap')  # Default region

    def test_search_by_work_code_success(self):
        """Test successful work code search"""
        # Mock cached data with work codes for filtering (as objects, not dicts)
        mock_item1 = MagicMock()
        mock_item1.item_number = '1'
        mock_item1.work_code = '6.1.1'
        mock_item1.work_description = 'Mandor'
        mock_item1.unit = 'OH'
        mock_item1.unit_price_idr = 150000
        mock_item1.region = 'Kab. Cilacap'
        mock_item1.edition = 'Edisi Ke - 2'
        mock_item1.year = '2025'
        mock_item1.sector = 'Bidang Cipta Karya dan Perumahan'
        
        mock_item2 = MagicMock()
        mock_item2.item_number = '2'
        mock_item2.work_code = '6.1.2'
        mock_item2.work_description = 'Kepala Tukang'
        mock_item2.unit = 'OH'
        mock_item2.unit_price_idr = 130000
        mock_item2.region = 'Kab. Cilacap'
        mock_item2.edition = 'Edisi Ke - 2'
        mock_item2.year = '2025'
        mock_item2.sector = 'Bidang Cipta Karya dan Perumahan'
        
        self.mock_get_cached.return_value = [mock_item1, mock_item2]
        
        response = self.client.get('/api/government_wage/search/?work_code=6.1.1')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['work_code'], '6.1.1')
        self.assertEqual(data['count'], 1)
        
        # Verify get_cached_or_scrape was called (year is passed as string from view)
        self.mock_get_cached.assert_called_once_with('Kab. Cilacap', '2025', force_refresh=False)

    def test_search_by_work_code_cache_hit(self):
        """Test work code search with cache hit"""
        # Mock cache hit (as object, not dict)
        mock_item = MagicMock()
        mock_item.item_number = '1'
        mock_item.work_code = '6.1.1'
        mock_item.work_description = 'Mandor'
        mock_item.unit = 'OH'
        mock_item.unit_price_idr = 150000
        mock_item.region = 'Kab. Cilacap'
        mock_item.edition = 'Edisi Ke - 2'
        mock_item.year = '2025'
        mock_item.sector = 'Bidang Cipta Karya dan Perumahan'
        
        self.mock_get_cached.return_value = [mock_item]
        
        response = self.client.get('/api/government_wage/search/?work_code=6.1.1')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['work_code'], '6.1.1')
        self.assertEqual(data['count'], 1)
        
        # Verify get_cached_or_scrape was called (year is passed as string from view)
        self.mock_get_cached.assert_called_once_with('Kab. Cilacap', '2025', force_refresh=False)

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
        with patch('api.government_wage.scraper.scrape_and_cache') as mock_scrape:
            mock_scrape.return_value = []
            
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

    def test_scraper_exception_handling(self):
        """Test exception handling in scraper operations"""
        # Mock get_cached_or_scrape to raise an exception
        self.mock_get_cached.side_effect = Exception('Scraping failed')
        
        response = self.client.get('/api/government_wage/scrape/?region=Kab.%20Cilacap')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)