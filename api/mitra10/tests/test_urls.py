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

    def test_invalid_url_raises_404(self):
        with self.assertRaises(NoReverseMatch):
            reverse('mitra10:nonexistent_view')
            
    def test_url_pattern_accepts_trailing_slash(self):
        resolver = resolve('/api/mitra10/scrape/')
        self.assertEqual(resolver.func, views.scrape_products)
        
    def test_url_pattern_without_trailing_slash_redirects(self):
        response = self.client.get('/api/mitra10/scrape')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/api/mitra10/scrape/')

    def test_reverse_lookup_works(self):
        url = reverse('mitra10:scrape_products')
        self.assertTrue(url.startswith('/api/mitra10/'))
        self.assertTrue(url.endswith('/scrape/'))