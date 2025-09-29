from django.test import TestCase
from django.urls import reverse, resolve
from django.http import Http404
from api.gemilang import views


class TestGemilangUrls(TestCase):
    
    def test_scrape_products_url_resolves_correctly(self):
        url = reverse('gemilang:scrape_products')
        self.assertEqual(url, '/api/gemilang/scrape/')
        
        resolved = resolve('/api/gemilang/scrape/')
        self.assertEqual(resolved.func, views.scrape_products)
        self.assertEqual(resolved.namespace, 'gemilang')
        self.assertEqual(resolved.url_name, 'scrape_products')
        
    def test_app_name_is_set_correctly(self):
        url = reverse('gemilang:scrape_products')
        self.assertIn('/api/gemilang/', url)
        
    def test_url_pattern_exists_in_urlpatterns(self):
        url = reverse('gemilang:scrape_products')
        resolved = resolve(url)
        self.assertIsNotNone(resolved)
        
    def test_view_function_import(self):
        from api.gemilang.urls import urlpatterns
        self.assertTrue(len(urlpatterns) > 0)
        
        pattern = urlpatterns[0]
        self.assertEqual(pattern.callback, views.scrape_products)