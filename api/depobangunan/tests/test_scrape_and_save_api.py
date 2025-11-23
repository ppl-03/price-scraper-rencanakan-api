from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json

# ---------- Shared light helpers ----------
def create_mock_product(name="Test Product", price=5000, url="https://www.depobangunan.co.id/test", unit="PCS"):
    p = MagicMock()
    p.name, p.price, p.url, p.unit = name, price, url, unit
    return p

def mk_result(success=True, products=None, error_message=None, url="https://www.depobangunan.co.id/test"):
    r = MagicMock()
    r.success = success
    r.products = products or []
    r.error_message = error_message
    r.url = url
    return r

def assert_json_response(testcase, response, expected_status=200):
    testcase.assertEqual(response.status_code, expected_status)
    testcase.assertEqual(response['Content-Type'], 'application/json')
    return json.loads(response.content)

# ---------- Test Suite ----------
class TestDepoBangunanScrapeAndSaveAPI(TestCase):
    """Reduced-duplication tests for Depo Bangunan scrape-and-save endpoint."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('depobangunan:scrape_and_save_products')

        # common sample data
        self.sample_product_1 = create_mock_product("Test Product 1", 5000, "https://www.depobangunan.co.id/test-product-1", "PCS")
        self.sample_product_2 = create_mock_product("Test Product 2", 7500, "https://www.depobangunan.co.id/test-product-2", "KG")

        # start patches once per test, stop via addCleanup
        self.p_create_scraper = patch('api.depobangunan.views.create_depo_scraper')
        self.p_db_service_cls = patch('api.depobangunan.views.DepoBangunanDatabaseService')
        self.p_security_validate = patch('api.depobangunan.views.SecurityDesignPatterns.validate_business_logic')

        self.mock_create_scraper = self.p_create_scraper.start()
        self.mock_db_service_cls = self.p_db_service_cls.start()
        self.mock_security_validate = self.p_security_validate.start()
        
        # By default, security validation passes
        self.mock_security_validate.return_value = (True, "")

        self.addCleanup(self.p_create_scraper.stop)
        self.addCleanup(self.p_db_service_cls.stop)
        self.addCleanup(self.p_security_validate.stop)

        # by default, create_scraper returns a mock with a stubbed scrape_products attr
        self.mock_scraper = MagicMock()
        self.mock_create_scraper.return_value = self.mock_scraper

        # and DB service returns a mock with a 'save' method
        self.mock_db = MagicMock()
        self.mock_db_service_cls.return_value = self.mock_db

    # ---- small helpers to DRY arrange/act steps ----
    def given_scraper(self, *, success=True, products=None, error_message=None, url="https://www.depobangunan.co.id/test"):
        self.mock_scraper.scrape_products.return_value = mk_result(
            success=success, products=products, error_message=error_message, url=url
        )

    def given_db(self, *, save_return=True, side_effect=None):
        self.mock_db.save.return_value = save_return
        if side_effect:
            self.mock_db.save.side_effect = side_effect

    def post_json(self, data):
        resp = self.client.post(self.url, data)
        # Return both raw response and parsed JSON for flexible assertions
        try:
            parsed = json.loads(resp.content)
        except Exception:
            parsed = None
        return resp, parsed

    # ---------- Tests ----------
    def test_scrape_and_save_url_resolves_correctly(self):
        self.assertEqual(self.url, '/api/depobangunan/scrape-and-save/')

    def test_successful_scrape_and_save(self):
        products = [self.sample_product_1, self.sample_product_2]
        self.given_scraper(
            success=True,
            products=products,
            url="https://www.depobangunan.co.id/catalogsearch/result/?q=semen",
        )
        self.given_db(save_return=True)

        resp, data = self.post_json({'keyword': 'semen', 'sort_by_price': 'true', 'page': '0'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Successfully saved 2 products')
        self.assertEqual(data['saved'], 2)
        self.assertEqual(data['inserted'], 2)
        self.assertEqual(data['url'], "https://www.depobangunan.co.id/catalogsearch/result/?q=semen")

        self.mock_scraper.scrape_products.assert_called_once_with(keyword='semen', sort_by_price=True, page=0)
        self.mock_db.save.assert_called_once()
        saved_data = self.mock_db.save.call_args[0][0]
        self.assertEqual([x['name'] for x in saved_data], ['Test Product 1', 'Test Product 2'])

    def test_scrape_and_save_no_products_found(self):
        self.given_scraper(success=True, products=[], url="https://www.depobangunan.co.id/catalogsearch/result/?q=nonexistent")
        self.given_db(save_return=True)  # not used but harmless

        resp, data = self.post_json({'keyword': 'nonexistent', 'sort_by_price': 'true', 'page': '0'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'No products found to save')
        self.assertEqual(data['saved'], 0)

    def test_scrape_and_save_error_responses(self):
        cases = [
            ({'sort_by_price': 'true', 'page': '0'}, 400, 'Keyword parameter is required'),
            ({'keyword': '', 'sort_by_price': 'true', 'page': '0'}, 400, 'Keyword parameter is required'),
            ({'keyword': '   ', 'sort_by_price': 'true', 'page': '0'}, 400, 'Keyword parameter is required'),
            ({'keyword': 'semen', 'sort_by_price': 'true', 'page': 'invalid'}, 400, 'Page parameter must be a valid integer'),
        ]
        for payload, status, msg in cases:
            with self.subTest(payload=payload):
                resp, data = self.post_json(payload)
                self.assertEqual(resp.status_code, status)
                self.assertIn('error', data)
                self.assertEqual(data['error'], msg)

    def test_scrape_and_save_scraping_failure(self):
        self.given_scraper(success=False, products=[], error_message="Failed to connect to website")

        resp, data = self.post_json({'keyword': 'semen', 'sort_by_price': 'true', 'page': '0'})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(data['error'], 'Failed to connect to website')

    def test_scrape_and_save_database_save_failure(self):
        self.given_scraper(success=True, products=[self.sample_product_1], url="https://www.depobangunan.co.id/test")
        self.given_db(save_return=False)

        resp, data = self.post_json({'keyword': 'semen', 'sort_by_price': 'true', 'page': '0'})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(data['error'], 'Failed to save products to database')

    def test_scrape_and_save_unexpected_exception(self):
        # raise inside scraper
        self.mock_scraper.scrape_products.side_effect = Exception("Unexpected error")
        resp, data = self.post_json({'keyword': 'semen', 'sort_by_price': 'true', 'page': '0'})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(data['error'], 'Internal server error occurred')

    def test_scrape_and_save_method_not_allowed(self):
        cases = [
            ('get', self.url, {'keyword': 'semen', 'sort_by_price': 'true', 'page': '0'}),
            ('put', self.url, {}),
            ('delete', self.url, {}),
        ]
        for method, url, data in cases:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, data)
                self.assertEqual(response.status_code, 405)

    def test_scrape_and_save_default_parameters(self):
        self.given_scraper(success=True, products=[self.sample_product_1])
        self.given_db(save_return=True)

        resp, _ = self.post_json({'keyword': 'semen'})
        self.assertEqual(resp.status_code, 200)
        self.mock_scraper.scrape_products.assert_called_once_with(keyword='semen', sort_by_price=True, page=0)

    def test_scrape_and_save_sort_by_price_variations(self):
        self.given_scraper(success=True, products=[self.sample_product_1])
        self.given_db(save_return=True)

        truthy = ['true', '1', 'yes', 'TRUE', 'True', 'YES']
        falsy = ['false', '0', 'no', 'FALSE', 'random']

        for v in truthy:
            with self.subTest(sort_by_price=v):
                resp, _ = self.post_json({'keyword': 'semen', 'sort_by_price': v, 'page': '0'})
                self.assertEqual(resp.status_code, 200)

        for v in falsy:
            with self.subTest(sort_by_price=v):
                resp, _ = self.post_json({'keyword': 'semen', 'sort_by_price': v, 'page': '0'})
                self.assertEqual(resp.status_code, 200)

    def test_scrape_and_save_with_special_characters_in_keyword(self):
        self.given_scraper(success=True, products=[self.sample_product_1])
        self.given_db(save_return=True)

        resp, _ = self.post_json({'keyword': 'semen & cat', 'sort_by_price': 'true', 'page': '0'})
        self.assertEqual(resp.status_code, 200)
        self.mock_scraper.scrape_products.assert_called_with(keyword='semen & cat', sort_by_price=True, page=0)

    def test_scrape_and_save_large_page_number(self):
        self.given_scraper(success=True, products=[self.sample_product_1])
        self.given_db(save_return=True)

        resp, _ = self.post_json({'keyword': 'semen', 'sort_by_price': 'true', 'page': '999'})
        self.assertEqual(resp.status_code, 200)
        self.mock_scraper.scrape_products.assert_called_with(keyword='semen', sort_by_price=True, page=999)

    def test_scrape_and_save_response_structure(self):
        self.given_scraper(success=True, products=[self.sample_product_1])
        self.given_db(save_return=True)

        resp, data = self.post_json({'keyword': 'semen'})
        self.assertEqual(resp.status_code, 200)

        for key, typ in [
            ('success', bool),
            ('message', str),
            ('saved', int),
            ('inserted', int),
            ('updated', int),
            ('anomalies', list),
            ('url', str),
        ]:
            self.assertIn(key, data)
            self.assertIsInstance(data[key], typ)

    def test_scrape_and_save_database_service_exception(self):
        self.given_scraper(success=True, products=[self.sample_product_1])
        self.given_db(side_effect=Exception("Database connection error"))

        resp, data = self.post_json({'keyword': 'semen'})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(data['error'], 'Internal server error occurred')
