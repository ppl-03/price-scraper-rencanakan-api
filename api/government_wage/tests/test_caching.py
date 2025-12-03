import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from api.government_wage.scraper import (
    save_to_local_file,
    load_from_local_file,
    get_cached_or_scrape,
    GovernmentWageItem
)


class TestFileCaching(unittest.TestCase):    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_region = "Kab. Test"
        self.test_year = "2025"
        
        self.test_items = [
            GovernmentWageItem(
                item_number="1",
                work_code="A.1.1.1",
                work_description="Test work",
                unit="m'",
                unit_price_idr=100000,
                region=self.test_region,
                edition="Edisi Ke - 2",
                year=self.test_year,
                sector="Test Sector"
            )
        ]
    
    @patch('api.government_wage.scraper.get_cache_directory')
    def test_save_to_local_file(self, mock_get_dir):
        mock_get_dir.return_value = self.test_dir
        
        filepath = save_to_local_file(self.test_items, self.test_region, self.test_year)
        
        self.assertTrue(os.path.exists(filepath))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['work_code'], "A.1.1.1")
        self.assertEqual(data[0]['region'], self.test_region)
    
    @patch('api.government_wage.scraper.get_cache_directory')
    def test_load_from_local_file_exists(self, mock_get_dir):
        mock_get_dir.return_value = self.test_dir
        
        save_to_local_file(self.test_items, self.test_region, self.test_year)
        
        loaded_items = load_from_local_file(self.test_region, self.test_year)
        
        self.assertIsNotNone(loaded_items)
        self.assertEqual(len(loaded_items), 1)
        self.assertEqual(loaded_items[0].work_code, "A.1.1.1")
    
    @patch('api.government_wage.scraper.get_cache_directory')
    def test_load_from_local_file_not_exists(self, mock_get_dir):
        mock_get_dir.return_value = self.test_dir
        
        loaded_items = load_from_local_file("NonExistent Region", self.test_year)
        
        self.assertIsNone(loaded_items)
    
    @patch('api.government_wage.scraper.scrape_and_cache')
    @patch('api.government_wage.scraper.load_from_local_file')
    def test_get_cached_or_scrape_cache_hit(self, mock_load, mock_scrape):
        mock_load.return_value = self.test_items
        
        result = get_cached_or_scrape(self.test_region, self.test_year)
        
        self.assertEqual(result, self.test_items)
        mock_load.assert_called_once()
        mock_scrape.assert_not_called()
    
    @patch('api.government_wage.scraper.scrape_and_cache')
    @patch('api.government_wage.scraper.load_from_local_file')
    def test_get_cached_or_scrape_cache_miss(self, mock_load, mock_scrape):
        mock_load.return_value = None  
        mock_scrape.return_value = self.test_items
        
        result = get_cached_or_scrape(self.test_region, self.test_year)
        
        self.assertEqual(result, self.test_items)
        mock_load.assert_called_once()
        mock_scrape.assert_called_once()
    
    @patch('api.government_wage.scraper.scrape_and_cache')
    @patch('api.government_wage.scraper.load_from_local_file')
    def test_get_cached_or_scrape_force_refresh(self, mock_load, mock_scrape):
        mock_scrape.return_value = self.test_items
        
        result = get_cached_or_scrape(self.test_region, self.test_year, force_refresh=True)
        
        self.assertEqual(result, self.test_items)
        mock_load.assert_not_called()  
        mock_scrape.assert_called_once()  
    
    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)


if __name__ == '__main__':
    unittest.main()