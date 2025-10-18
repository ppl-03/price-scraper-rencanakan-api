from django.test import TestCase
from django.urls import reverse, resolve
from api.depobangunan.views import depobangunan_locations_view


class TestDepoBangunanLocationUrls(TestCase):
    
    def test_depobangunan_locations_url_resolves(self):
        """Test that the locations URL resolves to the correct view"""
        url = reverse('depobangunan:depobangunan_locations')
        self.assertEqual(resolve(url).func, depobangunan_locations_view)
    
    def test_depobangunan_locations_url_pattern(self):
        """Test the URL pattern is correct"""
        url = reverse('depobangunan:depobangunan_locations')
        self.assertEqual(url, '/api/depobangunan/locations/')
    
    def test_depobangunan_locations_url_name(self):
        """Test the URL name is valid"""
        url = reverse('depobangunan:depobangunan_locations')
        self.assertIsInstance(url, str)
        self.assertTrue(url.endswith('/locations/'))
    
    def test_depobangunan_locations_url_with_trailing_slash(self):
        """Test URL works with trailing slash"""
        response = self.client.get('/api/depobangunan/locations/')
        self.assertNotEqual(response.status_code, 404)
    
    def test_depobangunan_locations_url_without_trailing_slash(self):
        """Test URL redirects or works without trailing slash"""
        response = self.client.get('/api/depobangunan/locations')
        self.assertIn(response.status_code, [301, 302, 200])
    
    def test_depobangunan_locations_url_case_sensitive(self):
        """Test URL is case sensitive"""
        response = self.client.get('/api/DEPOBANGUNAN/LOCATIONS/')
        self.assertEqual(response.status_code, 404)
    
    def test_depobangunan_locations_url_with_extra_path(self):
        """Test URL with extra path returns 404"""
        response = self.client.get('/api/depobangunan/locations/extra/')
        self.assertEqual(response.status_code, 404)
    
    def test_depobangunan_locations_url_method_options(self):
        """Test OPTIONS method on locations URL"""
        response = self.client.options('/api/depobangunan/locations/')
        self.assertIn(response.status_code, [200, 405])
    
    def test_depobangunan_locations_url_method_head(self):
        """Test HEAD method on locations URL"""
        response = self.client.head('/api/depobangunan/locations/')
        self.assertIn(response.status_code, [200, 405])
    
    def test_depobangunan_locations_url_with_query_params(self):
        """Test URL works with query parameters"""
        response = self.client.get('/api/depobangunan/locations/?timeout=60&test=value')
        self.assertNotEqual(response.status_code, 404)
