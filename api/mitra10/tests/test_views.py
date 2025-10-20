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
        self.assertIn("Internal server error occurred", response.content.decode())

    @patch("api.mitra10.views.create_mitra10_location_scraper")
    def test_scrape_locations_success(self, mock_factory):
        from api.interfaces import Location, LocationScrapingResult
        
        mock_scraper = MagicMock()
        mock_result = LocationScrapingResult(
            locations=[
                Location(name="MITRA10 A", code="code_a"),
                Location(name="MITRA10 B", code="code_b")
            ],
            success=True,
            error_message="",
            attempts_made=1
        )
        mock_scraper.scrape_locations.return_value = mock_result
        mock_factory.return_value = mock_scraper

        request = self.factory.get("/api/mitra10/locations")
        response = views.scrape_locations(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["locations"]), 2)
        self.assertEqual(data["locations"][1]["name"], "MITRA10 B")

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
        self.assertEqual(data["error_message"], "Internal server error occurred")


