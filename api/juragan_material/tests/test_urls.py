from django.test import TestCase
from django.urls import reverse, resolve
from django.http import Http404
from api.juragan_material import views


class TestJuraganMaterialUrls(TestCase):
    
    def test_scrape_products_url_resolves_correctly(self):
        url = reverse('juragan_material:scrape_products')
        self.assertEqual(url, '/api/juragan_material/scrape/')
        
        resolved = resolve('/api/juragan_material/scrape/')
        self.assertEqual(resolved.func, views.scrape_products)
        self.assertEqual(resolved.namespace, 'juragan_material')
        self.assertEqual(resolved.url_name, 'scrape_products')
        
    def test_app_name_is_set_correctly(self):
        url = reverse('juragan_material:scrape_products')
        self.assertIn('/api/juragan_material/', url)
        
    def test_url_pattern_exists_in_urlpatterns(self):
        url = reverse('juragan_material:scrape_products')
        resolved = resolve(url)
        self.assertIsNotNone(resolved)
        
    def test_view_function_import(self):
        from api.juragan_material.urls import urlpatterns
        self.assertTrue(len(urlpatterns) > 0)
        
        pattern = urlpatterns[0]
        self.assertEqual(pattern.callback, views.scrape_products)