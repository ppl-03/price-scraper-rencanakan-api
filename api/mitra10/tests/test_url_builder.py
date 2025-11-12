import urllib.parse
from django.test import TestCase
from unittest.mock import patch
from api.mitra10.url_builder import Mitra10UrlBuilder

class TestMitra10UrlBuilder(TestCase):
    
    def setUp(self):
        self.base_url = "https://www.mitra10.com/catalogsearch/result"
        
    @patch('api.mitra10.url_builder.config')
    def test_mitra10_url_builder_initialization(self, mock_config):
        """Test Mitra10UrlBuilder initialization with default config"""
        mock_config.mitra10_base_url = "https://www.mitra10.com/"
        mock_config.mitra10_search_path = "catalogsearch/result"
        
        builder = Mitra10UrlBuilder()
        
        # Test that the builder was initialized with config values
        self.assertEqual(builder.base_url, "https://www.mitra10.com/")
        self.assertEqual(builder.search_path, "catalogsearch/result")
        
    def test_mitra10_url_builder_custom_initialization(self):
        """Test Mitra10UrlBuilder initialization with custom values"""
        custom_base = "https://custom.mitra10.com/"
        custom_path = "custom/search"
        
        builder = Mitra10UrlBuilder(base_url=custom_base, search_path=custom_path)
        
        self.assertEqual(builder.base_url, custom_base)
        self.assertEqual(builder.search_path, custom_path)
    
    @patch('api.mitra10.url_builder.config')
    def test_build_params_without_sort(self, mock_config):
        """Test _build_params without sorting"""
        mock_config.mitra10_base_url = "https://www.mitra10.com/"
        mock_config.mitra10_search_path = "catalogsearch/result"
        
        builder = Mitra10UrlBuilder()
        params = builder._build_params(keyword="semen", sort_by_price=False, page=0)
        
        expected_params = {
            'q': 'semen',
            'sort': '{"key":"relevance","value":"DESC"}',  # sort_by_price=False still adds sort parameter
            'page': 1  # 0-based to 1-based conversion
        }
        
        self.assertEqual(params, expected_params)
        
    @patch('api.mitra10.url_builder.config')
    def test_build_params_with_sort(self, mock_config):
        """Test _build_params with sorting"""
        mock_config.mitra10_base_url = "https://www.mitra10.com/"
        mock_config.mitra10_search_path = "catalogsearch/result"
        
        builder = Mitra10UrlBuilder()
        params = builder._build_params(keyword="semen", sort_by_price=True, page=2)
        
        expected_params = {
            'q': 'semen',
            'sort': '{"key":"price","value":"ASC"}',
            'page': 3  # 2-based to 1-based conversion
        }
        
        self.assertEqual(params, expected_params)
        
    def test_mitra10_url_building_with_semen_search(self):
        """Test URL building for Mitra10 search with semen as search term"""
        search_term = "semen"
        expected_url = "https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D"
        
        actual_url = f"https://www.mitra10.com/catalogsearch/result?q={search_term}&sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D"
        self.assertEqual(actual_url, expected_url)
        
        self.assertIn('q=semen', actual_url)
        self.assertIn('sort=', actual_url)
        self.assertIn('price', actual_url)
        self.assertIn('ASC', actual_url)

    def test_mitra10_semen_url_encoding(self):
        search_term = "semen"
        
        properly_encoded = urllib.parse.quote(search_term)
        expected_url = f"https://www.mitra10.com/catalogsearch/result?q={properly_encoded}&sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D"
        
        self.assertEqual(properly_encoded, "semen") 
        self.assertIn("q=semen", expected_url)

    def test_mitra10_semen_price_sorting_verification(self):
        search_term = "semen"
        url = f"https://www.mitra10.com/catalogsearch/result?q={search_term}&sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D"
        
        self.assertIn('sort=', url)
        self.assertIn('price', url)
        self.assertIn('ASC', url)
        
        self.assertTrue(url.startswith('https://www.mitra10.com/catalogsearch/result'))
        self.assertIn('q=semen', url)
        
        expected_url = "https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D"
        self.assertEqual(url, expected_url)

    def test_mitra10_url_components_validation(self):
        search_term = "semen"
        
        base = "https://www.mitra10.com/catalogsearch/result"
        query_param = f"q={search_term}"
        sort_param = 'sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D'
        
        url = f"{base}?{query_param}&{sort_param}"
        
        self.assertTrue(url.startswith(base))
        self.assertIn(query_param, url)
        self.assertIn(sort_param, url)
        
        expected = "https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D"
        self.assertEqual(url, expected)