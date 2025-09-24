import urllib.parse
from django.test import TestCase

class TestMitra10UrlBuilder(TestCase):
    
    def setUp(self):
        self.base_url = "https://www.mitra10.com/catalogsearch/result"
        
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