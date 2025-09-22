from django.test import TestCase, RequestFactory
from .utils import sanitize_text
from .models import ScrapedData
from .views import show_scraped_data

class UtilsTest(TestCase):
    def test_sanitize_text_positive(self):
        raw = "<b>Harga</b>: 10000"
        clean = sanitize_text(raw)
        self.assertNotIn("<b>", clean)
        self.assertIn("Harga", clean)
        self.assertIn("10000", clean)

    def test_sanitize_text_negative(self):
        raw = "Harga: 20000"
        clean = sanitize_text(raw)
        self.assertEqual(clean, "Harga: 20000")

class ModelTest(TestCase):
    def test_scraped_data_sanitized_positive(self):
        obj = ScrapedData(content="<script>alert('xss')</script>Rp 5000")
        obj.save()
        self.assertNotIn("<script>", obj.content)
        self.assertIn("Rp 5000", obj.content)

    def test_scraped_data_sanitized_negative(self):
        obj = ScrapedData(content="Rp 7000")
        obj.save()
        self.assertEqual(obj.content, "Rp 7000")

class ViewsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_show_scraped_data_positive(self):
        request = self.factory.get('/dummy-url/')
        response = show_scraped_data(request)
        self.assertContains(response, "Harga: 10000")
        self.assertNotContains(response, "<script>")

    def test_show_scraped_data_negative(self):
        # Simulate clean input
        def clean_data_view(request):
            return show_scraped_data(request)
        request = self.factory.get('/dummy-url/')
        response = clean_data_view(request)
        self.assertContains(response, "Harga: 10000")
