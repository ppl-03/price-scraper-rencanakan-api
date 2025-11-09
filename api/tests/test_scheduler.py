import unittest
from types import SimpleNamespace

from api.scheduler import BaseScheduler


class FakeResult:
    def __init__(self, success=True, products=None, error_message=None):
        self.success = success
        self.products = products or []
        self.error_message = error_message


class FakeScraper:
    def __init__(self, results):
        self._results = results
        self.detail_map = {}

    def scrape_products(self, keyword, sort_by_price=True, page=0):
        return self._results.pop(0) if self._results else FakeResult(success=False, error_message='no result')

    def scrape_product_details(self, url):
        return self.detail_map.get(url)


class FakeDBService:
    def __init__(self, save_result=True, save_with_update_result=None, should_raise=False):
        self._save_result = save_result
        self._save_with_update_result = save_with_update_result
        self.saved_data = []
        self._should_raise = should_raise

    def save(self, data):
        if self._should_raise:
            raise RuntimeError('Database connection failed')
        self.saved_data.append(data)
        return self._save_result

    def save_with_price_update(self, data):
        if self._should_raise:
            raise RuntimeError('Database connection failed')
        self.saved_data.append(data)
        return self._save_with_update_result or {"inserted": len(data)}


class TestScheduler(unittest.TestCase):
    def test_scheduler_successful_save(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['k1']

            def create_scraper(self, vendor):
                r = FakeResult(success=True, products=[{'name': 'a', 'price': 100, 'url': 'u', 'unit': 'pcs'}])
                return FakeScraper([r])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        summary = s.run(vendors=['gemilang'])
        self.assertIn('gemilang', summary['vendors'])
        self.assertEqual(summary['vendors']['gemilang']['products_found'], 1)
        self.assertEqual(summary['vendors']['gemilang']['saved'], 1)
        self.assertEqual(summary['vendors']['gemilang']['status'], 'success')
        self.assertEqual(summary['successful_vendors'], 1)
        self.assertEqual(summary['failed_vendors'], 0)

    def test_scheduler_no_categories(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return []

            def create_scraper(self, vendor):
                raise AssertionError('should not be called')

        s = S()
        summary = s.run(vendors=['depobangunan'])
        self.assertEqual(summary['vendors']['depobangunan']['products_found'], 0)
        self.assertEqual(summary['vendors']['depobangunan']['saved'], 0)
        self.assertEqual(summary['vendors']['depobangunan']['status'], 'skipped_no_categories')
        self.assertGreater(len(summary['vendors']['depobangunan']['errors']), 0)
        self.assertEqual(summary['failed_vendors'], 1)

    def test_scheduler_scraper_failure(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['kw']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=False, error_message='timeout')])

            def load_db_service(self, vendor):
                return FakeDBService()

        s = S()
        summary = s.run(vendors=['mitra10'])
        self.assertGreater(len(summary['vendors']['mitra10']['errors']), 0)
        self.assertEqual(summary['vendors']['mitra10']['products_found'], 0)
        self.assertEqual(summary['vendors']['mitra10']['status'], 'failed_all_scrapes')
        self.assertEqual(summary['failed_vendors'], 1)

    def test_scheduler_db_save_failure(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['k']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'x', 'price': 10, 'url': 'u', 'unit': 'box'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=False)

        s = S()
        summary = s.run(vendors=['juragan_material'])
        self.assertEqual(summary['vendors']['juragan_material']['products_found'], 1)
        self.assertEqual(summary['vendors']['juragan_material']['saved'], 0)
        self.assertEqual(summary['vendors']['juragan_material']['status'], 'success')

    def test_enrichment_called(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['kw']

            def create_scraper(self, vendor):
                r = FakeResult(success=True, products=[{'name': 'p', 'price': 5, 'url': 'detail-1', 'unit': ''}])
                s = FakeScraper([r])
                s.detail_map['detail-1'] = SimpleNamespace(unit='kg')
                return s

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        summary = s.run(vendors=['gemilang'])
        self.assertEqual(summary['vendors']['gemilang']['products_found'], 1)
        self.assertEqual(summary['vendors']['gemilang']['saved'], 1)
        self.assertEqual(summary['vendors']['gemilang']['status'], 'success')
    
    def test_scheduler_scraper_creation_failure(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword']

            def create_scraper(self, vendor):
                raise ValueError('Invalid vendor configuration')

            def load_db_service(self, vendor):
                return FakeDBService()

        s = S()
        summary = s.run(vendors=['test_vendor'])
        self.assertEqual(summary['vendors']['test_vendor']['status'], 'failed_scraper_creation')
        self.assertGreater(len(summary['vendors']['test_vendor']['errors']), 0)
        self.assertEqual(summary['failed_vendors'], 1)
        self.assertGreater(len(summary['errors']), 0)
    
    def test_scheduler_database_exception(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 100, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(should_raise=True)

        s = S()
        summary = s.run(vendors=['test_vendor'])
        self.assertEqual(summary['vendors']['test_vendor']['products_found'], 1)
        self.assertEqual(summary['vendors']['test_vendor']['saved'], 0)
        self.assertGreater(len(summary['vendors']['test_vendor']['errors']), 0)
    
    def test_scheduler_timing_metadata(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['k']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'x', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        summary = s.run(vendors=['gemilang'])
        self.assertIn('start_timestamp', summary)
        self.assertIn('end_timestamp', summary)
        self.assertIn('total_duration_seconds', summary)
        self.assertIn('duration_seconds', summary['vendors']['gemilang'])
        self.assertGreaterEqual(summary['total_duration_seconds'], 0)


if __name__ == '__main__':
    unittest.main()
