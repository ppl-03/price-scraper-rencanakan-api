import json
from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from api.mitra10 import views
from api.views import get_csrf_token
from api.interfaces import Product, ScrapingResult


TEST_DOC_IP = ".".join(["203", "0", "113", "1"])  


class TestMitra10Views(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        # API token for authenticated requests
        self.valid_token = "dev-token-12345"
        
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

    def test_scrape_products_missing_query(self):
        request = self.factory.get("/api/mitra10/products")
        response = views.scrape_products(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Query parameter is required", response.content.decode())

    def test_scrape_products_empty_query(self):
        request = self.factory.get("/api/mitra10/products?q=   ")
        response = views.scrape_products(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Query parameter cannot be empty", response.content.decode())

    def test_scrape_products_invalid_page(self):
        request = self.factory.get("/api/mitra10/products?q=cat&page=abc")
        response = views.scrape_products(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Page parameter must be a valid integer", response.content.decode())

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
    def test_scrape_locations_object_items(self, mock_factory):
        class Obj:
            def __init__(self, name, code):
                self.name = name
                self.code = code

        mock_scraper = MagicMock()
        mock_scraper.scrape_locations.return_value = {
            'success': True,
            'locations': [Obj('Obj Loc', 'OBJ_99')],
            'error_message': ''
        }
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["locations"][0]["name"], "Obj Loc")
        self.assertEqual(data["locations"][0]["code"], "OBJ_99")

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

    def test_scrape_and_save_missing_query(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/", **self.auth_headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["inserted"], 0)
        self.assertEqual(data["updated"], 0)
        self.assertEqual(data["anomalies"], [])
        self.assertIn("Query parameter is required", data["error_message"])

    def test_scrape_and_save_empty_query(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=   ", **self.auth_headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Query parameter cannot be empty", data["error_message"])

    def test_scrape_and_save_invalid_page_parameter(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer&page=invalid", **self.auth_headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Page parameter must be a valid integer", data["error_message"])

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_successful(self, mock_scraper_factory, mock_db_service):       
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[
                Product(name="Hammer A", price=50000, url="hammer-a.com", unit="pcs"),
                Product(name="Hammer B", price=60000, url="hammer-b.com", unit="pcs"),
            ]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 2,
            'updated': 0,
            'anomalies': []
        }
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
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=False,
            error_message="Product not found",
            url="https://www.mitra10.com",
            products=[]
        )
        mock_scraper.scrape_products.return_value = mock_result
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
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Test", price=1000, url="test.com", unit="pcs")]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        mock_service_instance = MagicMock()
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
        # Scraper returns a successful result with one product
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Item", price=1000, url="u", unit="pcs")]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        # DB service returns a malformed dict missing required keys to cause KeyError in logger/response
        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
            'success': True
            # 'inserted', 'updated', 'anomalies' intentionally missing
        }
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=item", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        # Should hit the outermost exception handler returning 500 with Internal server error
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Internal server error", data["error_message"])

    @patch("api.mitra10.views.logger")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_logger_info_raises_outer_except(self, mock_scraper_factory, mock_db_service, mock_logger):
        # Prepare scraper result
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="OK", price=123, url="u", unit="pcs")]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        # DB returns a valid save_result
        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 1,
            'updated': 0,
            'anomalies': []
        }
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
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[
                Product(name="Product X", price=100000, url="x.com", unit="box"),
            ]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
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
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Item", price=5000, url="item.com", unit="pcs")]
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
        self.assertFalse(data["success"])
        self.assertIn("API token required", data["error_message"])

    def test_scrape_and_save_unauthorized_invalid_token(self):
        """Invalid API token should be rejected."""
        headers = {"HTTP_X_API_TOKEN": "bad-token", "HTTP_X_CSRFTOKEN": self.csrf_token}
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer", **headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Invalid API token", data["error_message"])

    @patch("api.mitra10.views.logger")
    def test_scrape_and_save_invalid_token_logger_warning_raised(self, mock_logger):
        """Cover _validate_api_token path where logger.warning raises for invalid token."""
        mock_logger.warning.side_effect = Exception("warn boom")
        headers = {"HTTP_X_API_TOKEN": "bad-token", "HTTP_X_CSRFTOKEN": self.csrf_token}
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer", **headers)
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Invalid API token", data["error_message"])

    def test_scrape_and_save_ip_not_authorized(self):
        """Valid token but disallowed IP should be rejected."""
        # Patch allowed_ips for the dev token to a different IP
        original = views.API_TOKENS["dev-token-12345"]["allowed_ips"]
        try:
            views.API_TOKENS["dev-token-12345"]["allowed_ips"] = [TEST_DOC_IP]  # NOSONAR
            headers = {"HTTP_X_API_TOKEN": self.valid_token, "HTTP_X_CSRFTOKEN": self.csrf_token}
            # Simulate a request from 127.0.0.1 which is not allowed
            request = self.factory.post(
                "/api/mitra10/scrape-and-save/?q=hammer", **{**headers, "REMOTE_ADDR": "127.0.0.1"}
            )
            response = views.scrape_and_save_products(request)
            self.assertEqual(response.status_code, 401)
            data = json.loads(response.content)
            self.assertFalse(data["success"])
            self.assertIn("IP not authorized", data["error_message"])
        finally:
            # Restore
            views.API_TOKENS["dev-token-12345"]["allowed_ips"] = original

    @patch("api.mitra10.views.logger")
    def test_scrape_and_save_ip_not_authorized_logger_warning_raised(self, mock_logger):
        """Cover _validate_api_token path where logger.warning raises for disallowed IP."""
        original = views.API_TOKENS["dev-token-12345"]["allowed_ips"]
        try:
            views.API_TOKENS["dev-token-12345"]["allowed_ips"] = [TEST_DOC_IP]  # NOSONAR
            mock_logger.warning.side_effect = Exception("warn boom")
            headers = {"HTTP_X_API_TOKEN": self.valid_token, "HTTP_X_CSRFTOKEN": self.csrf_token}
            request = self.factory.post(
                "/api/mitra10/scrape-and-save/?q=hammer", **{**headers, "REMOTE_ADDR": "127.0.0.1"}
            )
            response = views.scrape_and_save_products(request)
            self.assertEqual(response.status_code, 401)
            data = json.loads(response.content)
            self.assertFalse(data["success"])
            self.assertIn("IP not authorized", data["error_message"])
        finally:
            views.API_TOKENS["dev-token-12345"]["allowed_ips"] = original

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_with_sort_type_cheapest(self, mock_scraper_factory, mock_db_service):
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Cheap Product", price=10000, url="cheap.com", unit="pcs")]
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

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer&sort_type=cheapest", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        
        # Verify scrape_products was called (not scrape_by_popularity)
        mock_scraper.scrape_products.assert_called_once_with(keyword='hammer', sort_by_price=True, page=0)
        mock_scraper.scrape_by_popularity.assert_not_called()

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_with_sort_type_popularity(self, mock_scraper_factory, mock_db_service):        
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[
                Product(name="Popular Product 1", price=50000, url="pop1.com", unit="pcs", sold_count=1000),
                Product(name="Popular Product 2", price=60000, url="pop2.com", unit="pcs", sold_count=800),
            ]
        )
        mock_scraper.scrape_by_popularity.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 2,
            'updated': 0,
            'anomalies': []
        }
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
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Default Product", price=20000, url="default.com", unit="pcs")]
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
        self.assertFalse(data['success'])
        self.assertIn("Query parameter is required", data['error_message'])

    def test_scrape_popularity_empty_query(self):
        """Test scrape_popularity with empty query parameter"""
        request = self.factory.get("/api/mitra10/scrape-popularity/?q=   ")
        response = views.scrape_popularity(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn("Query parameter cannot be empty", data['error_message'])

    def test_scrape_popularity_invalid_page(self):
        """Test scrape_popularity with invalid page parameter"""
        request = self.factory.get("/api/mitra10/scrape-popularity/?q=semen&page=invalid")
        response = views.scrape_popularity(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn("Page parameter must be a valid integer", data['error_message'])

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_popularity_success(self, mock_factory):        
        # Mock scraper
        mock_scraper = MagicMock()
        mock_factory.return_value = mock_scraper
        
        # Mock products
        mock_products = [
            Product(name="SCG Semen Instan 40 Kg", price=75000, url="https://mitra10.com/1", unit="sak"),
            Product(name="Sika Semen Instan 25 Kg", price=94907, url="https://mitra10.com/2", unit="sak"),
        ]
        
        mock_result = ScrapingResult(
            products=mock_products,
            success=True,
            url="https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22:%22relevance%22,%22value%22:%22DESC%22%7D&page=1"
        )
        mock_scraper.scrape_by_popularity.return_value = mock_result
        
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
        mock_scraper = MagicMock()
        mock_factory.return_value = mock_scraper
        
        mock_result = ScrapingResult(
            products=[],
            success=True,
            url="https://www.mitra10.com/catalogsearch/result?q=semen&sort=%7B%22key%22:%22relevance%22,%22value%22:%22DESC%22%7D&page=3"
        )
        mock_scraper.scrape_by_popularity.return_value = mock_result
        
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
        # Mock product scraper
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Test Product", price=10000, url="test.com", unit="pcs")]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        # Mock location scraper to raise exception
        mock_location_factory.side_effect = Exception("Location scraper failed")

        # Mock database service
        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 1,
            'updated': 0,
            'anomalies': []
        }
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
        # Mock product scraper
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Test Product 2", price=20000, url="test2.com", unit="pcs")]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        # Mock location scraper to return empty locations
        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {
            'success': True,
            'locations': [],
            'error_message': ''
        }
        mock_location_factory.return_value = mock_location_scraper

        # Mock database service
        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 1,
            'updated': 0,
            'anomalies': []
        }
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        # Verify products were saved with empty location
        call_args = mock_service_instance.save_with_price_update.call_args[0][0]
        self.assertEqual(call_args[0]['location'], '')

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_location_scraper_returns_failure(self, mock_scraper_factory, mock_db_service, mock_location_factory):
        """Test scrape_and_save when location scraper returns success=False (covers line 281-282)"""
        # Mock product scraper
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=True,
            error_message="",
            url="https://www.mitra10.com",
            products=[Product(name="Test Product 3", price=30000, url="test3.com", unit="pcs")]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        # Mock location scraper to return success=False
        mock_location_scraper = MagicMock()
        mock_location_scraper.scrape_locations.return_value = {
            'success': False,
            'locations': [],
            'error_message': 'Failed to scrape locations'
        }
        mock_location_factory.return_value = mock_location_scraper

        # Mock database service
        mock_service_instance = MagicMock()
        mock_service_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 1,
            'updated': 0,
            'anomalies': []
        }
        mock_db_service.return_value = mock_service_instance

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=test", **self.auth_headers)
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        # Verify products were saved with empty location
        call_args = mock_service_instance.save_with_price_update.call_args[0][0]
        self.assertEqual(call_args[0]['location'], '')