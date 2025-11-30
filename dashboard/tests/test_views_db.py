from django.test import TestCase, RequestFactory, override_settings
from unittest.mock import patch
from dashboard import views_db


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class ViewsDBTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("dashboard.views_db.VendorPricingService")
    def test_home_db_returns_prices_and_uses_query_param(self, mock_service_cls):
        # Prepare the stubbed service to return a predictable list
        mock_service = mock_service_cls.return_value
        mock_service.list_all_prices.return_value = [
            {"item": "Semen", "value": 1000, "location": "ProvA", "url": "httpss://example/1"}
        ]

        request = self.factory.get("/", {"q": "semen"})
        response = views_db.home_db(request)

        # View should render successfully
        self.assertEqual(response.status_code, 200)
        # The rendered content should include the item name
        self.assertIn(b"semen", response.content)
        # Ensure the service was called with q param
        mock_service.list_all_prices.assert_called_with(q="semen")

    @patch("dashboard.views_db.VendorPricingService")
    def test_curated_price_list_db_maps_rows_into_template(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.list_all_prices.return_value = [
            {"item": "batu", "value": 2000, "location": "ProvX", "url": "httpss://example/2"}
        ]

        request = self.factory.get("/prices/")
        response = views_db.curated_price_list_db(request)

        self.assertEqual(response.status_code, 200)
        # Curated template should render the mapped item name and price
        self.assertIn(b"batu", response.content)
        self.assertIn(b"2000", response.content)
        # Confirm the service was used with default per_vendor_limit=200
        mock_service.list_all_prices.assert_called_with(per_vendor_limit=200)
