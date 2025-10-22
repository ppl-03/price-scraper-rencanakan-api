import json
from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from api.mitra10 import views
from django.http import JsonResponse
import json


class TestMitra10Views(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        
    def test_create_error_response_returns_json(self):
        response = views._create_error_response("Something went wrong", 418)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 418)
        content = json.loads(response.content)
        self.assertFalse(content["success"])
        self.assertEqual(content["error_message"], "Something went wrong")
        self.assertEqual(content["locations"], [])
        self.assertEqual(content["count"], 0)

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
        from api.interfaces import Product, ScrapingResult
        
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

    def test_scrape_and_save_missing_query(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/")
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["inserted"], 0)
        self.assertEqual(data["updated"], 0)
        self.assertEqual(data["anomalies"], [])
        self.assertIn("Query parameter is required", data["error_message"])

    def test_scrape_and_save_empty_query(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=   ")
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Query parameter cannot be empty", data["error_message"])

    def test_scrape_and_save_invalid_page_parameter(self):
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer&page=invalid")
        response = views.scrape_and_save_products(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Page parameter must be a valid integer", data["error_message"])

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_successful(self, mock_scraper_factory, mock_db_service):
        from api.interfaces import Product, ScrapingResult
        
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

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=hammer")
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
        
        request = self.factory.post("/api/mitra10/scrape-and-save/?q=nail")
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["inserted"], 0)
        self.assertEqual(data["updated"], 0)
        self.assertIn("Scraping failed", data["error_message"])

    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_scraper_returns_failure(self, mock_scraper_factory):
        from api.interfaces import ScrapingResult
        
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            success=False,
            error_message="Product not found",
            url="https://www.mitra10.com",
            products=[]
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper_factory.return_value = mock_scraper

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=nonexistent")
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
        from api.interfaces import Product, ScrapingResult
        
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

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=test")
        response = views.scrape_and_save_products(request)

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Database error", data["error_message"])

    @patch("api.mitra10.views.Mitra10DatabaseService")
    @patch("api.mitra10.views.create_mitra10_scraper")
    def test_scrape_and_save_with_anomalies(self, mock_scraper_factory, mock_db_service):
        from api.interfaces import Product, ScrapingResult
        
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

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=product")
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
        from api.interfaces import Product, ScrapingResult
        
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

        request = self.factory.post("/api/mitra10/scrape-and-save/?q=item")
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


