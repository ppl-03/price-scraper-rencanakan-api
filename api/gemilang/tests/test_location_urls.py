from django.test import TestCase
from django.urls import reverse, resolve
from api.gemilang.views import gemilang_locations_view


class TestGemilangLocationUrls(TestCase):
    
    def test_gemilang_locations_url_resolves(self):
        url = reverse('gemilang_locations')
        self.assertEqual(resolve(url).func, gemilang_locations_view)
    
    def test_gemilang_locations_url_pattern(self):
        url = reverse('gemilang_locations')
        self.assertEqual(url, '/api/gemilang/locations/')
    
    def test_gemilang_locations_url_name(self):
        url = reverse('gemilang_locations')
        self.assertIsInstance(url, str)
        self.assertTrue(url.endswith('/locations/'))
    
    def test_gemilang_locations_url_with_trailing_slash(self):
        response = self.client.get('/api/gemilang/locations/')
        self.assertNotEqual(response.status_code, 404)
    
    def test_gemilang_locations_url_without_trailing_slash(self):
        response = self.client.get('/api/gemilang/locations')
        self.assertIn(response.status_code, [301, 302, 200])
    
    def test_gemilang_locations_url_case_sensitive(self):
        response = self.client.get('/api/GEMILANG/LOCATIONS/')
        self.assertEqual(response.status_code, 404)
    
    def test_gemilang_locations_url_with_extra_path(self):
        response = self.client.get('/api/gemilang/locations/extra/')
        self.assertEqual(response.status_code, 404)
    
    def test_gemilang_locations_url_method_options(self):
        response = self.client.options('/api/gemilang/locations/')
        self.assertIn(response.status_code, [200, 405])
    
    def test_gemilang_locations_url_method_head(self):
        response = self.client.head('/api/gemilang/locations/')
        self.assertIn(response.status_code, [200, 405])
    
    def test_gemilang_locations_url_with_query_params(self):
        response = self.client.get('/api/gemilang/locations/?timeout=60&test=value')
        self.assertNotEqual(response.status_code, 404)