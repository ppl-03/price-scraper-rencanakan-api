from django.test import TestCase
from django.urls import reverse, resolve, NoReverseMatch
from api.mitra10 import views


class TestMitra10URLs(TestCase):

    def test_scrape_products_url_resolves(self):
        url = reverse('mitra10:scrape_products')
        self.assertEqual(url, '/api/mitra10/scrape/')
        
    def test_scrape_products_url_uses_correct_view(self):
        resolver = resolve('/api/mitra10/scrape/')
        self.assertEqual(resolver.func, views.scrape_products)
        
    def test_scrape_products_url_name(self):
        resolver = resolve('/api/mitra10/scrape/')
        self.assertEqual(resolver.url_name, 'scrape_products')
        
    def test_scrape_products_namespace(self):
        resolver = resolve('/api/mitra10/scrape/')
        self.assertEqual(resolver.namespace, 'mitra10')
        
    def test_app_name_is_set(self):
        resolver = resolve('/api/mitra10/scrape/')
        self.assertEqual(resolver.app_name, 'mitra10')

    # Tests for scrape_locations URL pattern
    def test_scrape_locations_url_resolves(self):
        url = reverse('mitra10:scrape_locations')
        self.assertEqual(url, '/api/mitra10/locations/')
        
    def test_scrape_locations_url_uses_correct_view(self):
        resolver = resolve('/api/mitra10/locations/')
        self.assertEqual(resolver.func, views.scrape_locations)
        
    def test_scrape_locations_url_name(self):
        resolver = resolve('/api/mitra10/locations/')
        self.assertEqual(resolver.url_name, 'scrape_locations')
        
    def test_scrape_locations_namespace(self):
        resolver = resolve('/api/mitra10/locations/')
        self.assertEqual(resolver.namespace, 'mitra10')
        
    def test_scrape_locations_app_name_is_set(self):
        resolver = resolve('/api/mitra10/locations/')
        self.assertEqual(resolver.app_name, 'mitra10')

    # General URL tests
    def test_invalid_url_raises_404(self):
        with self.assertRaises(NoReverseMatch):
            reverse('mitra10:nonexistent_view')
        
    def test_scrape_url_pattern_without_trailing_slash_redirects(self):
        response = self.client.get('/api/mitra10/scrape')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/api/mitra10/scrape/')

    def test_locations_url_pattern_without_trailing_slash_redirects(self):
        response = self.client.get('/api/mitra10/locations')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/api/mitra10/locations/')

    def test_scrape_products_reverse_lookup_works(self):
        url = reverse('mitra10:scrape_products')
        self.assertTrue(url.startswith('/api/mitra10/'))
        self.assertTrue(url.endswith('/scrape/'))

    def test_scrape_locations_reverse_lookup_works(self):
        url = reverse('mitra10:scrape_locations')
        self.assertTrue(url.startswith('/api/mitra10/'))
        self.assertTrue(url.endswith('/locations/'))

    def test_all_url_patterns_are_covered(self):
        """Ensure we test both URL patterns defined in urls.py"""
        # Test that both URL patterns can be resolved
        scrape_products_url = reverse('mitra10:scrape_products')
        scrape_locations_url = reverse('mitra10:scrape_locations')
        
        self.assertEqual(scrape_products_url, '/api/mitra10/scrape/')
        self.assertEqual(scrape_locations_url, '/api/mitra10/locations/')
        
        # Test that both URLs resolve to correct views
        scrape_resolver = resolve('/api/mitra10/scrape/')
        locations_resolver = resolve('/api/mitra10/locations/')
        
        self.assertEqual(scrape_resolver.func, views.scrape_products)
        self.assertEqual(locations_resolver.func, views.scrape_locations)