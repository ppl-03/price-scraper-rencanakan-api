from django.test import TestCase, Client
from django.urls import reverse
from django.test.utils import override_settings
from unittest.mock import patch


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class TestDashboardPriceAnomaliesView(TestCase):
    """Simple tests for the dashboard price anomalies page"""

    def setUp(self):
        self.client = Client()
        # Patch staticfiles_storage.url to avoid ManifestStaticFilesStorage
        # looking up a manifest during template rendering in tests.
        self._patcher = patch(
            'django.contrib.staticfiles.storage.staticfiles_storage.url',
            return_value='/static/dashboard/images/rencanakan_logo.png'
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_price_anomalies_page_renders(self):
        """GET dashboard:price_anomalies should return 200 and render template"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Basic sanity: template contains page title defined in template
        content = response.content.decode('utf-8')
        self.assertIn('Price Anomalies - Rencanakan Dashboard', content)

    def test_price_anomalies_url_resolves(self):
        """Reverse lookup for the named URL should work"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_template_contains_statistics_and_filters(self):
        """Template should include statistic IDs and filter controls"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')

        # Statistics IDs
        for stat_id in ('total-anomalies', 'pending-anomalies', 'price-increases', 'price-decreases'):
            self.assertIn(f'id="{stat_id}"', content)

        # Filter controls
        for fid in ('filter-status', 'filter-vendor', 'filter-search'):
            self.assertIn(f'id="{fid}"', content)

    def test_template_contains_anomalies_list_and_pagination(self):
        """Anomalies list container and pagination container should exist"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')

        self.assertIn('id="anomalies-list"', content)
        self.assertIn('id="pagination-container"', content)

    def test_template_includes_api_endpoints_and_review_modal(self):
        """Template should include the JS endpoints used by the page and review modal elements"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')

        # API endpoints used by the page
        self.assertIn('/api/db-pricing/anomalies/statistics/', content)
        self.assertIn('/api/db-pricing/anomalies/', content)

        # Review modal and form
        for elem in ('review-modal', 'review-form', 'review-status', 'review-notes'):
            self.assertIn(f'id="{elem}"', content)
