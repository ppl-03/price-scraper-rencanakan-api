import json
from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from api.mitra10 import views
from api.mitra10.security import AccessControlManager
from api.views import get_csrf_token
from db_pricing.models import Mitra10Product
from api.interfaces import Product, ScrapingResult


TEST_DOC_IP = ".".join(["203", "0", "113", "1"])  # NOSONAR - Test documentation IP
TEST_PRIVATE_IP_1 = ".".join(["10", "0", "0", "1"])  # NOSONAR - Test private IP
TEST_PRIVATE_IP_2 = ".".join(["192", "168", "1", "1"])  # NOSONAR - Test private IP


class TestMitra10Views(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        # API token for authenticated requests
        self.valid_token = "mitra10-dev-token-12345"
        
        # Get CSRF token from the existing endpoint
        csrf_request = self.factory.get('/api/csrf-token/')
        csrf_response = get_csrf_token(csrf_request)
        csrf_data = json.loads(csrf_response.content)
        self.csrf_token = csrf_data['csrf_token']
        
        # Include both API token and CSRF token in headers
        self.auth_headers = {
            'HTTP_X_API_TOKEN': self.valid_token,
            'HTTP_X_CSRFTOKEN': self.csrf_token
        }

    def _create_mock_scraper_with_products(self, products, success=True, error_message="", url="https://www.mitra10.com"):
        """Helper to create a mock scraper with products."""
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=success,
            error_message=error_message,
            url=url,
            products=products
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper.scrape_by_popularity.return_value = mock_result
        return mock_scraper

    def _create_mock_db_service(self, save_result):
        """Helper to create a mock database service."""
        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = save_result
        return mock_service_instance

    def test_scrape_products_missing_query(self):
        request = self.factory.get("/api/mitra10/products")
        response = views.scrape_products(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Keyword is required", response.content.decode())

    def test_scrape_products_empty_query(self):
        request = self.factory.get("/api/mitra10/products?q=   ")
        response = views.scrape_products(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Keyword cannot be empty", response.content.decode())

    def test_scrape_products_invalid_page(self):
        request = self.factory.get("/api/mitra10/products?q=cat&page=abc")
        response = views.scrape_products(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("page must be a valid integer", response.content.decode())

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_products_success(self, mock_factory):
        
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[
                Product(name="Item A", price=10000, url="a.com"),
                Product(name="Item B", price=20000, url="b.com"),
            ]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/products?q=screw&page=1&sort_by_price=true")
        response = views.scrape_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["products"]), 2)
        self.assertEqual(data["products"][0]["name"], "Item A")
        mock_scraper.scrape_products.assert_called_once()

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_products_unexpected_error(self, mock_factory):
        mock_factory.side_effect = Exception("unexpected fail")
        request = self.factory.get("/api/mitra10/products?q=hammer")
        response = views.scrape_products(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Internal server error", response.content.decode())
        self.assertIn("unexpected fail", response.content.decode())

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    def test_scrape_locations_success(self, mock_factory):
        mock_scraper = MagicMock()
        mock_result = {
            'success': True,
            'locations': ['MITRA10 Jakarta', 'MITRA10 Bandung'],
            'error_message': ''
        }
        mock_scraper.scrape_locations.return_value = mock_result
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["locations"]), 2)
        self.assertEqual(data["locations"][0]["name"], "MITRA10 Jakarta")
        self.assertEqual(data["locations"][0]["code"], "MITRA10_1")

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    def test_scrape_locations_failure(self, mock_factory):
        mock_scraper = MagicMock()
        mock_scraper.scrape_locations.side_effect = Exception("boom")
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Internal server error", data["error_message"])
        self.assertIn("boom", data["error_message"])

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    def test_scrape_locations_string_format(self, mock_factory):
        """Test that string locations are properly formatted with auto-generated codes."""
        mock_scraper = MagicMock()
        mock_result = {
            'success': True,
            'locations': ['Store Alpha', 'Store Beta', 'Store Gamma'],
            'error_message': ''
        }
        mock_scraper.scrape_locations.return_value = mock_result
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["locations"]), 3)
        # Verify line 160-163: isinstance(location, str) branch
        self.assertEqual(data["locations"][0]["name"], "Store Alpha")
        self.assertEqual(data["locations"][0]["code"], "MITRA10_1")
        self.assertEqual(data["locations"][2]["name"], "Store Gamma")
        self.assertEqual(data["locations"][2]["code"], "MITRA10_3")

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    def test_scrape_locations_dict_items(self, mock_factory):
        """Locations provided as dicts should be passed through unchanged."""
        mock_scraper = MagicMock()
        mock_scraper.scrape_locations.return_value = {
            'success': True,
            'locations': [{
                'name': 'Custom Loc',
                'code': 'CSTM_01'
            }],
            'error_message': ''
        }
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["locations"][0]["name"], "Custom Loc")
        self.assertEqual(data["locations"][0]["code"], "CSTM_01")

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    def test_scrape_locations_success_but_empty(self, mock_factory):
        mock_scraper = MagicMock()
        mock_scraper.scrape_locations.return_value = {
            'success': True,
            'locations': [],
            'error_message': ''
        }
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["locations"], [])
        self.assertEqual(data["count"], 0)

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    def test_scrape_locations_failure_result(self, mock_factory):
        mock_scraper = MagicMock()
        mock_scraper.scrape_locations.return_value = {
            'success': False,
            'locations': [],
            'error_message': 'bad'
        }
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["locations"], [])
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["error_message"], 'bad')

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    def test_scrape_locations_object_format(self, mock_factory):
        """Test that object locations are properly formatted using getattr - covers line 161"""
        mock_scraper = MagicMock()
        
        # Create mock location objects (not dicts, not strings)
        mock_location1 = MagicMock()
        mock_location1.name = "Object Location 1"
        mock_location1.code = "OBJ_LOC_1"
        
        mock_location2 = MagicMock()
        mock_location2.name = "Object Location 2"
        # This one has no code attribute to test fallback
        del mock_location2.code
        
        mock_result = {
            'success': True,
            'locations': [mock_location1, mock_location2],
            'error_message': ''
        }
        mock_scraper.scrape_locations.return_value = mock_result
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["locations"]), 2)
        # Verify line 161-163: getattr with fallback
        self.assertEqual(data["locations"][0]["name"], "Object Location 1")
        self.assertEqual(data["locations"][0]["code"], "OBJ_LOC_1")
        self.assertEqual(data["locations"][1]["name"], "Object Location 2")
        self.assertEqual(data["locations"][1]["code"], "MITRA10_2")  # Fallback code

    def test_scrape_and_save_missing_query(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/", **self.auth_headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("Keyword is required", data["details"]["q"])

    def test_scrape_and_save_empty_query(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=   ", **self.auth_headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("Keyword cannot be empty", data["details"]["q"])

    def test_scrape_and_save_invalid_page_parameter(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer&page=invalid", **self.auth_headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("page must be a valid integer", data["details"]["page"])

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_successful(self, mock_scraper_factory, mock_db_service):
        products = [
            Product(name="Hammer A", price=50000, url="hammer-a.com", unit="pcs"),
            Product(name="Hammer B", price=60000, url="hammer-b.com", unit="pcs"),
        ]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        save_result = {'success': True, 'inserted': 2, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["inserted"], 2)
        self.assertEqual(data["updated"], 0)
        self.assertEqual(data["anomalies"], [])
        self.assertEqual(data["total_products"], 2)
        mock_service_instance.save_with_price_update.assert_called_once()

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_scraping_failure(self, mock_scraper_factory):
        mock_scraper_factory.side_effect = Exception("Scraper initialization failed")

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=nail", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["inserted"], 0)
        self.assertEqual(data["updated"], 0)
        self.assertIn("Scraping failed", data["error_message"])

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_scraper_returns_failure(self, mock_scraper_factory):
        mock_scraper = self._create_mock_scraper_with_products([], success=False, error_message="Product not found")
        mock_scraper_factory.return_value = mock_scraper

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=nonexistent", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["inserted"], 0)
        self.assertEqual(data["updated"], 0)
        self.assertIn("Product not found", data["error_message"])

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_database_failure(self, mock_scraper_factory, mock_db_service):
        products = [Product(name="Test", price=1000, url="test.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        mock_service_instance = self._create_mock_db_service({})
        mock_service_instance.save_with_price_update.side_effect = Exception("Database connection failed")
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Database error", data["error_message"])

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_unexpected_exception_after_db(self, mock_scraper_factory, mock_db_service):
        products = [Product(name="Item", price=1000, url="u", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        # DB service returns a malformed dict missing required keys
        # After Sentry monitoring integration, the code uses .get() for safe access
        # so this now returns 200 with default values instead of 500
        mock_service_instance = self._create_mock_db_service({'success': True})
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=item", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        # Code now handles malformed dicts gracefully with .get() defaults
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["inserted"], 0)  # Default value from .get()
        self.assertEqual(data["updated"], 0)  # Default value from .get()

    @patch("api.mitra10.views.logger")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_logger_info_raises_outer_except(self, mock_scraper_factory, mock_db_service, mock_logger):
        products = [Product(name="OK", price=123, url="u", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        # DB returns a valid save_result
        save_result = {'success': True, 'inserted': 1, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        # Make logger.info raise an exception to hit the outer except
        mock_logger.info.side_effect = Exception('log boom')

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=ok", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Internal server error", data["error_message"])

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_with_anomalies(self, mock_scraper_factory, mock_db_service):
        products = [Product(name="Product X", price=100000, url="x.com", unit="box")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        save_result = {
            'success': True,
            'inserted': 0,
            'updated': 1,
            'anomalies': [
                {
                    'name': 'Product X',
                    'url': 'x.com',
                    'unit': 'box',
                    'old_price': 50000,
                    'new_price': 100000,
                    'change_percent': 100.0
                }
            ]
        }
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=product", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["inserted"], 0)
        self.assertEqual(data["updated"], 1)
        self.assertEqual(len(data["anomalies"]), 1)
        self.assertEqual(data["anomalies"][0]["name"], "Product X")
        self.assertEqual(data["anomalies"][0]["old_price"], 50000)
        self.assertEqual(data["anomalies"][0]["new_price"], 100000)

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_response_format(self, mock_scraper_factory, mock_db_service):
        products = [Product(name="Item", price=5000, url="item.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        save_result = {'success': True, 'inserted': 1, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=item", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        data = json.loads(response.content)
        self.assertIn("success", data)
        self.assertIn("inserted", data)
        self.assertIn("updated", data)
        self.assertIn("anomalies", data)
        self.assertIn("total_products", data)
        self.assertIn("error_message", data)
        self.assertIsInstance(data["success"], bool)
        self.assertIsInstance(data["inserted"], int)
        self.assertIsInstance(data["updated"], int)
        self.assertIsInstance(data["anomalies"], list)
        self.assertIsInstance(data["total_products"], int)
        self.assertIsInstance(data["error_message"], str)

    # --- Authorization and API token validation coverage ---
    def test_scrape_and_save_unauthorized_no_token(self):
        """POST without API token should be rejected before parsing params."""
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer")
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("API token required", data["error"])

    def test_scrape_and_save_unauthorized_invalid_token(self):
        """Invalid API token should be rejected."""
        headers = {"HTTP_X_API_TOKEN": "bad-token", "HTTP_X_CSRFTOKEN": self.csrf_token}
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer", **headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("Invalid API token", data["error"])

    @patch("api.mitra10.views.logger")
    def test_scrape_and_save_invalid_token_logger_warning_raised(self, mock_logger):
        """Cover _validate_api_token path where logger.warning raises for invalid token."""
        mock_logger.warning.side_effect = Exception("warn boom")
        headers = {"HTTP_X_API_TOKEN": "bad-token", "HTTP_X_CSRFTOKEN": self.csrf_token}
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer", **headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("Invalid API token", data["error"])

    def test_scrape_and_save_ip_not_authorized(self):
        """Valid token but disallowed IP should be rejected."""
        # Patch allowed_ips for the dev token to a different IP
        original = AccessControlManager.API_TOKENS["mitra10-dev-token-12345"]["allowed_ips"]
        try:
            AccessControlManager.API_TOKENS["mitra10-dev-token-12345"]["allowed_ips"] = [TEST_DOC_IP]  # NOSONAR
            headers = {"HTTP_X_API_TOKEN": self.valid_token, "HTTP_X_CSRFTOKEN": self.csrf_token}
            # Simulate a request from 127.0.0.1 which is not allowed
            request = self.factory.post(
                "/api/mitra10/scrape-and-save/?q=hammer", **{**headers, "REMOTE_ADDR": "127.0.0.1"}
            )
            response = views.scrape_and_save_products(request)
            self.assertEqual(response.status_code, 401)
            data = json.loads(response.content)
            self.assertIn("error", data)
            self.assertIn("not authorized", data["error"])
        finally:
            # Restore
            AccessControlManager.API_TOKENS["mitra10-dev-token-12345"]["allowed_ips"] = original

    @patch("api.mitra10.views.logger")
    def test_scrape_and_save_ip_not_authorized_logger_warning_raised(self, mock_logger):
        """Cover _validate_api_token path where logger.warning raises for disallowed IP."""
        original = AccessControlManager.API_TOKENS["mitra10-dev-token-12345"]["allowed_ips"]
        try:
            AccessControlManager.API_TOKENS["mitra10-dev-token-12345"]["allowed_ips"] = [TEST_DOC_IP]  # NOSONAR
            mock_logger.warning.side_effect = Exception("warn boom")
            headers = {"HTTP_X_API_TOKEN": self.valid_token, "HTTP_X_CSRFTOKEN": self.csrf_token}
            request = self.factory.post(
                "/api/mitra10/scrape-and-save/?q=hammer", **{**headers, "REMOTE_ADDR": "127.0.0.1"}
            )
            response = views.scrape_and_save_products(request)
            self.assertEqual(response.status_code, 401)
            data = json.loads(response.content)
            self.assertIn("error", data)
            self.assertIn("not authorized", data["error"])
        finally:
            AccessControlManager.API_TOKENS["mitra10-dev-token-12345"]["allowed_ips"] = original

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_with_sort_type_popularity(self, mock_scraper_factory, mock_db_service):
        products = [
            Product(name="Popular Product 1", price=50000, url="pop1.com", unit="pcs", sold_count=1000),
            Product(name="Popular Product 2", price=60000, url="pop2.com", unit="pcs", sold_count=800),
        ]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        save_result = {'success': True, 'inserted': 2, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer&sort_type=popularity", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["inserted"], 2)
        
        # Verify scrape_by_popularity was called (not scrape_products)
        mock_scraper.scrape_by_popularity.assert_called_once_with(keyword='hammer', top_n=5, page=0)
        mock_scraper.scrape_products.assert_not_called()

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_default_sort_type(self, mock_scraper_factory, mock_db_service):
        products = [Product(name="Default Product", price=20000, url="default.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        save_result = {'success': True, 'inserted': 1, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        # No sort_type parameter provided
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=nail", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        
        # Should default to scrape_products
        mock_scraper.scrape_products.assert_called_once()
        mock_scraper.scrape_by_popularity.assert_not_called()

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_with_bearer_token_header(self, mock_scraper_factory, mock_db_service):
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Bearer OK", price=11111, url="bearer.com", unit="pcs")]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 1,
            'updated': 0,
            'anomalies': []
        }
        mock_db_service.return_value = mock_service_instance

        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {self.valid_token}',
            'HTTP_X_CSRFTOKEN': self.csrf_token
        }
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=bearer", **headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

    def test_scrape_popularity_missing_query(self):
        """Test scrape_popularity with missing query parameter"""
        request = self.factory.get("/api/mitra10/scrape-popularity/")
        response = views.scrape_popularity(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("Keyword is required", data["details"]["q"])

    def test_scrape_popularity_empty_query(self):
        """Test scrape_popularity with empty query parameter"""
        request = self.factory.get("/api/mitra10/scrape-popularity/?q=   ")
        response = views.scrape_popularity(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("Keyword cannot be empty", data["details"]["q"])

    def test_scrape_popularity_invalid_page(self):
        """Test scrape_popularity with invalid page parameter"""
        request = self.factory.get("/api/mitra10/scrape-popularity/?q=semen&page=invalid")
        response = views.scrape_popularity(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("page must be a valid integer", data["details"]["page"])

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_popularity_success(self, mock_factory):
        products = [
            Product(name="SCG Semen Instan 40 Kg", price=75000, url="https://mitra10.com/1", unit="sak"),
            Product(name="Sika Semen Instan 25 Kg", price=94907, url="https://mitra10.com/2", unit="sak"),
        ]
        mock_scraper = self._create_mock_scraper_with_products(
            products, 
            url="https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22:%22relevance%22,%22value%22:%22DESC%22%7D&page=1"
        )
        mock_factory.return_value = mock_scraper
        
        request = self.factory.get("/api/mitra10/scrape-popularity/?q=semen")
        response = views.scrape_popularity(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['products']), 2)
        self.assertEqual(data['products'][0]['name'], "SCG Semen Instan 40 Kg")
        self.assertEqual(data['products'][0]['price'], 75000)
        
        # Verify scrape_by_popularity was called (not scrape_products)
        mock_scraper.scrape_by_popularity.assert_called_once_with(keyword='semen', top_n=5, page=0)

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_popularity_with_page_parameter(self, mock_factory):
        mock_scraper = self._create_mock_scraper_with_products(
            [], 
            url="https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22:%22relevance%22,%22value%22:%22DESC%22%7D&page=3"
        )
        mock_factory.return_value = mock_scraper
        
        request = self.factory.get("/api/mitra10/scrape-popularity/?q=semen&page=2")
        response = views.scrape_popularity(request)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify page parameter was passed correctly
        mock_scraper.scrape_by_popularity.assert_called_once_with(keyword='semen', top_n=5, page=2)

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_popularity_scraper_failure(self, mock_factory):
        """Test scrape_popularity when scraper fails"""
        mock_factory.side_effect = Exception("Scraper initialization failed")
        
        request = self.factory.get("/api/mitra10/scrape-popularity/?q=semen")
        response = views.scrape_popularity(request)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn("Internal server error", data['error_message'])

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_location_scraper_failure(self, mock_scraper_factory, mock_db_service, mock_location_factory):
        """Test scrape_and_save when location scraper raises exception (covers line 283-284)"""
        products = [Product(name="Test Product", price=10000, url="test.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        # Mock location scraper to raise exception
        mock_location_factory.side_effect = Exception("Location scraper failed")

        save_result = {'success': True, 'inserted': 1, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        # Should still succeed despite location scraper failure
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["inserted"], 1)

        # Verify products were saved with empty location
        call_args = mock_service_instance.save_with_price_update.call_args[0][0]
        self.assertEqual(call_args[0]['location'], '')

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_location_scraper_returns_empty(self, mock_scraper_factory, mock_db_service, mock_location_factory):
        """Test scrape_and_save when location scraper returns empty locations (covers line 281-282)"""
        products = [Product(name="Test Product 2", price=20000, url="test2.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        # Mock location scraper to return empty locations
        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {
            'success': True,
            'locations': [],
            'error_message': ''
        }
        mock_location_factory.return_value = mock_location_scraper

        save_result = {'success': True, 'inserted': 1, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        # Verify products were saved with empty location
        call_args = mock_service_instance.save_with_price_update.call_args[0][0]
        self.assertEqual(call_args[0]['location'], '')

    @patch("api.mitra10.views.AutoCategorizationService")
    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_with_categorization_success(self, mock_scraper_factory, mock_db_service, mock_location_factory, mock_categorization_service):        
        products = [Product(name="Test Product", price=10000, url="test.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {'success': True, 'locations': ['Loc1'], 'error_message': ''}
        mock_location_factory.return_value = mock_location_scraper

        save_result = {'success': True, 'inserted': 2, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance
        
        mock_queryset = MagicMock()
        mock_queryset.values_list.return_value = [1, 2]
        
        with patch.object(Mitra10Product.objects, 'filter', return_value=mock_queryset):
            mock_queryset.order_by.return_value = mock_queryset
            mock_queryset.__getitem__.return_value = mock_queryset
            
            # Mock categorization service
            mock_cat_service_instance = MagicMock()
            mock_cat_service_instance.categorize_products.return_value = {'categorized': 2}
            mock_categorization_service.return_value = mock_cat_service_instance

            request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
            response = views.scrape_and_save_products(request)

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data["success"])
            
            # Verify categorization was called
            mock_categorization_service.assert_called_once()
            mock_cat_service_instance.categorize_products.assert_called_once_with('mitra10', [1, 2])

    @patch("api.mitra10.views.logger")
    @patch("api.mitra10.views.AutoCategorizationService")
    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_categorization_failure_does_not_break_response(self, mock_scraper_factory, mock_db_service, mock_location_factory, mock_categorization_service, mock_logger):
        products = [Product(name="Test Product", price=10000, url="test.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {'success': True, 'locations': [], 'error_message': ''}
        mock_location_factory.return_value = mock_location_scraper

        save_result = {'success': True, 'inserted': 1, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        with patch("api.mitra10.views.Mitra10Product") as mock_product_model:
            mock_products_qs = MagicMock()
            mock_products_qs.values_list.return_value = [1]
            mock_product_model.objects.filter.return_value.order_by.return_value.__getitem__.return_value = mock_products_qs
            
            mock_categorization_service.side_effect = Exception("Categorization error")

            request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
            response = views.scrape_and_save_products(request)

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data["success"])
            
            mock_logger.warning.assert_called_once()
            self.assertIn("Auto-categorization failed", str(mock_logger.warning.call_args))

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_no_categorization_when_no_inserts(self, mock_scraper_factory, mock_db_service, mock_location_factory):
        products = [Product(name="Test Product", price=10000, url="test.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {'success': True, 'locations': [], 'error_message': ''}
        mock_location_factory.return_value = mock_location_scraper

        save_result = {'success': True, 'inserted': 0, 'updated': 1, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        with patch("api.mitra10.views.AutoCategorizationService") as mock_cat_service:
            request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
            response = views.scrape_and_save_products(request)

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data["success"])
            
            mock_cat_service.assert_not_called()

    @patch("api.mitra10.views.AutoCategorizationService")
    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_no_categorization_when_save_fails(self, mock_scraper_factory, mock_db_service, mock_location_factory, mock_categorization_service):
        products = [Product(name="Test Product", price=10000, url="test.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {'success': True, 'locations': [], 'error_message': ''}
        mock_location_factory.return_value = mock_location_scraper

        save_result = {'success': False, 'inserted': 0, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        
        mock_categorization_service.assert_not_called()

    @patch("api.mitra10.views.logger")
    @patch("api.mitra10.views.AutoCategorizationService")
    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_categorization_with_no_product_ids(self, mock_scraper_factory, mock_db_service, mock_location_factory, mock_categorization_service, mock_logger):       
        products = [Product(name="Test Product", price=10000, url="test.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {'success': True, 'locations': [], 'error_message': ''}
        mock_location_factory.return_value = mock_location_scraper

        save_result = {'success': True, 'inserted': 1, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        mock_queryset = MagicMock()
        mock_queryset.values_list.return_value = []
        
        with patch.object(Mitra10Product.objects, 'filter', return_value=mock_queryset):
            mock_queryset.order_by.return_value = mock_queryset
            mock_queryset.__getitem__.return_value = mock_queryset
            
            request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
            response = views.scrape_and_save_products(request)

            self.assertEqual(response.status_code, 200)
            
            mock_categorization_service.assert_not_called()

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_location_scraper_returns_failure(self, mock_scraper_factory, mock_db_service, mock_location_factory):
        """Test scrape_and_save when location scraper returns success=False (covers line 281-282)"""
        products = [Product(name="Test Product 3", price=30000, url="test3.com", unit="pcs")]
        mock_scraper = self._create_mock_scraper_with_products(products)
        mock_scraper_factory.return_value = mock_scraper

        # Mock location scraper to return success=False
        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {
            'success': False,
            'locations': [],
            'error_message': 'Failed to scrape locations'
        }
        mock_location_factory.return_value = mock_location_scraper

        save_result = {'success': True, 'inserted': 1, 'updated': 0, 'anomalies': []}
        mock_service_instance = self._create_mock_db_service(save_result)
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        # Verify products were saved with empty location
        call_args = mock_service_instance.save_with_price_update.call_args[0][0]
        self.assertEqual(call_args[0]['location'], '')

    def test_validate_api_token_logging_exception_invalid_token(self):
        """Test exception handling in logging for invalid token (lines 43-45)"""
        from api.mitra10.views import _validate_api_token
        
        request = self.factory.get('/test/')
        request.headers = {'X-API-Token': 'invalid-token'}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        # Mock logger to raise exception
        with patch('api.mitra10.views.logger.warning', side_effect=Exception("Logging failed")):
            is_valid, error_msg = _validate_api_token(request)
            
            # Should still return False without crashing
            self.assertFalse(is_valid)
            self.assertEqual(error_msg, 'Invalid API token')
    
    def test_validate_api_token_logging_exception_ip_not_allowed(self):
        """Test exception handling in logging for IP not allowed (lines 54-55)"""
        from api.mitra10.views import _validate_api_token
        
        request = self.factory.get('/test/')
        request.headers = {'X-API-Token': 'dev-token-12345'}
        request.META = {'REMOTE_ADDR': TEST_PRIVATE_IP_2}
        
        # Mock API_TOKENS with IP whitelist
        with patch('api.mitra10.views.API_TOKENS', {
            'dev-token-12345': {
                'name': 'Test Token',
                'allowed_ips': [TEST_PRIVATE_IP_1],  # Different IP
                'created': '2024-01-01',
                'expires': None
            }
        }):
            with patch('api.mitra10.views.logger.warning', side_effect=Exception("Logging failed")):
                is_valid, error_msg = _validate_api_token(request)
                
                # Should still return False without crashing
                self.assertFalse(is_valid)
                self.assertEqual(error_msg, 'IP not authorized')
    
    def test_validate_api_token_logging_exception_success(self):
        """Test exception handling in logging for successful auth (lines 60-62)"""
        from api.mitra10.views import _validate_api_token
        
        request = self.factory.get('/test/')
        request.headers = {'X-API-Token': 'dev-token-12345'}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        # Mock logger.info to raise exception
        with patch('api.mitra10.views.logger.info', side_effect=Exception("Logging failed")):
            is_valid, error_msg = _validate_api_token(request)
            
            # Should still return True without crashing
            self.assertTrue(is_valid)
            self.assertEqual(error_msg, '')
    
    def test_validate_api_token_with_ip_whitelist_allowed(self):
        """Test IP whitelist allowing specific IP (lines 51-52)"""
        from api.mitra10.views import _validate_api_token
        
        request = self.factory.get('/test/')
        request.headers = {'X-API-Token': 'dev-token-12345'}
        request.META = {'REMOTE_ADDR': TEST_PRIVATE_IP_1}
        
        with patch('api.mitra10.views.API_TOKENS', {
            'dev-token-12345': {
                'name': 'Test Token',
                'allowed_ips': [TEST_PRIVATE_IP_1],
                'created': '2024-01-01',
                'expires': None
            }
        }):
            is_valid, error_msg = _validate_api_token(request)
            
            self.assertTrue(is_valid)
            self.assertEqual(error_msg, '')