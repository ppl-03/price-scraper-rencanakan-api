import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch, MagicMock

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

    # No categorizer for each vendor
    # def test_scheduler_no_categories(self):
    #     class S(BaseScheduler):
    #         def get_categories(self, vendor, server_time):
    #             return []

    #         def create_scraper(self, vendor):
    #             raise AssertionError('should not be called')

    #     s = S()
    #     summary = s.run(vendors=['depobangunan'])
    #     self.assertEqual(summary['vendors']['depobangunan']['products_found'], 0)
    #     self.assertEqual(summary['vendors']['depobangunan']['saved'], 0)
    #     self.assertEqual(summary['vendors']['depobangunan']['status'], 'skipped_no_categories')
    #     self.assertGreater(len(summary['vendors']['depobangunan']['errors']), 0)
    #     self.assertEqual(summary['failed_vendors'], 1)

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


class TestNowFunction(unittest.TestCase):
    def test_now_function_returns_datetime(self):
        from api.scheduler import _now
        result = _now()
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, datetime)
    
    def test_now_function_handles_timezone_exception(self):
        from api import scheduler
        from api.scheduler import _now
        
        # Use patch context manager to ensure cleanup
        with patch.object(scheduler.timezone, 'now', side_effect=Exception('timezone error')):
            result = _now()
            self.assertIsInstance(result, datetime)


class TestGetCategories(unittest.TestCase):
    def test_get_categories_with_server_time_parameter(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module') as mock_import:
            mock_mod = Mock()
            mock_fn = Mock(return_value=['cat1', 'cat2'])
            mock_mod.get_categories = mock_fn
            mock_import.return_value = mock_mod
            
            server_time = datetime(2025, 1, 1, 12, 0, 0)
            result = scheduler.get_categories('test_vendor', server_time)
            
            self.assertEqual(result, ['cat1', 'cat2'])
            mock_fn.assert_called_once_with(server_time)
    
    def test_get_categories_fallback_without_server_time(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module') as mock_import:
            mock_mod = Mock()
            
            def mock_get_categories(*args):
                if len(args) > 0:
                    raise TypeError('takes 0 arguments')
                return ['cat1']
            
            mock_mod.get_categories = mock_get_categories
            mock_import.return_value = mock_mod
            
            result = scheduler.get_categories('test_vendor', None)
            
            self.assertEqual(result, ['cat1'])
    
    def test_get_categories_no_function(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module') as mock_import:
            mock_mod = Mock(spec=[])
            mock_import.return_value = mock_mod
            
            result = scheduler.get_categories('test_vendor', None)
            
            self.assertEqual(result, [])
    
    def test_get_categories_import_error(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module', side_effect=ImportError('Module not found')):
            result = scheduler.get_categories('nonexistent_vendor', None)
            
            self.assertEqual(result, [])
    
    def test_get_categories_exception(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module', side_effect=Exception('Unexpected error')):
            result = scheduler.get_categories('test_vendor', None)
            
            self.assertEqual(result, [])


class TestCreateScraper(unittest.TestCase):
    @patch('api.scheduler.get_scraper_factory')
    def test_create_scraper_success(self, mock_factory):
        mock_scraper = Mock()
        mock_factory.return_value = mock_scraper
        
        scheduler = BaseScheduler()
        result = scheduler.create_scraper('gemilang')
        
        self.assertEqual(result, mock_scraper)
        mock_factory.assert_called_once_with('gemilang')


class TestLoadDbService(unittest.TestCase):
    def test_load_db_service_success(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module') as mock_import:
            mock_service = Mock()
            mock_class = Mock(return_value=mock_service)
            mock_mod = Mock()
            mock_mod.__dir__ = Mock(return_value=['MyDatabaseService', 'other_attr'])
            mock_mod.MyDatabaseService = mock_class
            mock_import.return_value = mock_mod
            
            result = scheduler.load_db_service('test_vendor')
            
            self.assertEqual(result, mock_service)
            mock_class.assert_called_once()
    
    def test_load_db_service_import_error(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module', side_effect=ImportError('Module not found')):
            result = scheduler.load_db_service('nonexistent_vendor')
            
            self.assertIsNone(result)
    
    def test_load_db_service_no_database_service_class(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module') as mock_import:
            mock_mod = Mock()
            mock_mod.__dir__ = Mock(return_value=['other_class', 'helper_function'])
            mock_import.return_value = mock_mod
            
            result = scheduler.load_db_service('test_vendor')
            
            self.assertIsNone(result)
    
    def test_load_db_service_instantiation_error(self):
        scheduler = BaseScheduler()
        with patch('api.scheduler.import_module') as mock_import:
            mock_class = Mock(side_effect=Exception('Initialization failed'))
            mock_mod = Mock()
            mock_mod.__dir__ = Mock(return_value=['DatabaseService'])
            mock_mod.DatabaseService = mock_class
            mock_import.return_value = mock_mod
            
            result = scheduler.load_db_service('test_vendor')
            
            self.assertIsNone(result)


class TestNormalizeProducts(unittest.TestCase):
    def test_normalize_products_dict_list(self):
        scheduler = BaseScheduler()
        """Test normalize_products with list of dictionaries."""
        products = [
            {'name': 'Product A', 'price': 100, 'url': 'https://example.com/a', 'unit': 'pcs'},
            {'name': 'Product B', 'price': 200, 'url': 'https://example.com/b', 'unit': 'box'}
        ]
        
        result = scheduler.normalize_products(products)
        
        # Expected result includes location and category fields
        expected = [
            {
                'name': 'Product A',
                'price': 100,
                'url': 'https://example.com/a',
                'unit': 'pcs',
                'location': '',
                'category': ''
            },
            {
                'name': 'Product B',
                'price': 200,
                'url': 'https://example.com/b',
                'unit': 'box',
                'location': '',
                'category': ''
            }
        ]
        
        self.assertEqual(result, expected)
    
    def test_normalize_products_object_list(self):
        scheduler = BaseScheduler()
        product1 = SimpleNamespace(name='Product A', price=100, url='https://example.com/a', unit='pcs', location='Jawa Barat', category='category A')
        product2 = SimpleNamespace(name='Product B', price=200, url='https://example.com/b', unit='kg', location='Jawa Timur', category='category B')
        products = [product1, product2]
        
        result = scheduler.normalize_products(products)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Product A')
        self.assertEqual(result[0]['price'], 100)
        self.assertEqual(result[0]['url'], 'https://example.com/a')
        self.assertEqual(result[0]['unit'], 'pcs')
        self.assertEqual(result[0]['location'], 'Jawa Barat')
        self.assertEqual(result[0]['category'], 'category A')
        self.assertEqual(result[1]['name'], 'Product B')
        self.assertEqual(result[1]['price'], 200)
        self.assertEqual(result[1]['url'], 'https://example.com/b')
        self.assertEqual(result[1]['unit'], 'kg')
        self.assertEqual(result[1]['location'], 'Jawa Timur')
        self.assertEqual(result[1]['category'], 'category B')
        
    
    def test_normalize_products_object_without_unit(self):
        scheduler = BaseScheduler()
        product = SimpleNamespace(name='Product A', price=100, url='https://example.com/a')
        products = [product]
        
        result = scheduler.normalize_products(products)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['unit'], '')
    
    def test_normalize_products_mixed_list(self):
        scheduler = BaseScheduler()
        product1 = {'name': 'Product A', 'price': 100, 'url': 'https://example.com/a', 'unit': 'pcs', 'location': 'Jawa Barat', 'category': 'category A'}
        product2 = SimpleNamespace(name='Product B', price=200, url='https://example.com/b', unit='kg', location='Jawa Timur', category='category B')
        products = [product1, product2]
        
        result = scheduler.normalize_products(products)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], product1)
        self.assertEqual(result[0]['name'], 'Product A')
        self.assertEqual(result[1]['unit'], 'kg')
        self.assertEqual(result[1]['location'], 'Jawa Timur')
        self.assertEqual(result[1]['category'], 'category B')
        self.assertEqual(result[1]['name'], 'Product B')
    
    def test_normalize_products_invalid_object(self):
        scheduler = BaseScheduler()
        products = [SimpleNamespace(invalid='data')]
        
        with patch('api.scheduler.logger') as mock_logger:
            result = scheduler.normalize_products(products)
            
            self.assertEqual(result, [])
            mock_logger.warning.assert_called_once()


class TestEnrichUnit(unittest.TestCase):
    def test_enrich_unit_dict_product_success(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        detail = SimpleNamespace(unit='kg')
        scraper.scrape_product_details = Mock(return_value=detail)
        
        product = {'name': 'Product A', 'price': 100, 'url': 'https://example.com/a', 'unit': ''}
        
        scheduler.enrich_unit(scraper, product)
        
        self.assertEqual(product['unit'], 'kg')
        scraper.scrape_product_details.assert_called_once_with('https://example.com/a')
    
    def test_enrich_unit_object_product_success(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        detail = SimpleNamespace(unit='pcs')
        scraper.scrape_product_details = Mock(return_value=detail)
        
        product = SimpleNamespace(name='Product A', price=100, url='https://example.com/b', unit='')
        
        scheduler.enrich_unit(scraper, product)
        
        self.assertEqual(product.unit, 'pcs')
    
    def test_enrich_unit_no_scrape_product_details_method(self):
        scheduler = BaseScheduler()
        scraper = Mock(spec=[])
        product = {'name': 'Product A', 'price': 100, 'url': 'https://example.com/a', 'unit': ''}
        
        scheduler.enrich_unit(scraper, product)
        
        self.assertEqual(product['unit'], '')
    
    def test_enrich_unit_no_url(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        scraper.scrape_product_details = Mock()
        
        product = {'name': 'Product A', 'price': 100, 'unit': ''}
        
        scheduler.enrich_unit(scraper, product)
        
        scraper.scrape_product_details.assert_not_called()
    
    def test_enrich_unit_detail_no_unit(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        detail = SimpleNamespace()
        scraper.scrape_product_details = Mock(return_value=detail)
        
        product = {'name': 'Product A', 'price': 100, 'url': 'https://example.com/a', 'unit': ''}
        
        scheduler.enrich_unit(scraper, product)
        
        self.assertEqual(product['unit'], '')
    
    def test_enrich_unit_exception(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        scraper.scrape_product_details = Mock(side_effect=Exception('Network error'))
        
        product = {'name': 'Product A', 'price': 100, 'url': 'https://example.com/a', 'unit': ''}
        
        scheduler.enrich_unit(scraper, product)
        
        self.assertEqual(product['unit'], '')
    
    def test_enrich_unit_immutable_object(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        detail = SimpleNamespace(unit='kg')
        scraper.scrape_product_details = Mock(return_value=detail)
        
        product = Mock()
        product.url = 'https://example.com/a'
        type(product).unit = property(lambda self: '')
        
        scheduler.enrich_unit(scraper, product)
        
        scraper.scrape_product_details.assert_called_once()
    
    def test_enrich_unit_object_setattr_exception(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        detail = SimpleNamespace(unit='kg')
        scraper.scrape_product_details = Mock(return_value=detail)
        
        class ImmutableProduct:
            def __init__(self):
                self.url = 'https://example.com/a'
                self._unit = ''
            
            @property
            def unit(self):
                return self._unit
            
            @unit.setter
            def unit(self, value):
                raise AttributeError('cannot set attribute')
        
        product = ImmutableProduct()
        
        scheduler.enrich_unit(scraper, product)
        
        scraper.scrape_product_details.assert_called_once_with('https://example.com/a')
    
    def test_enrich_unit_outer_exception_coverage(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        scraper.scrape_product_details = Mock(side_effect=RuntimeError('Scraping failed'))
        
        product = SimpleNamespace(url='https://example.com/a', unit='')
        
        scheduler.enrich_unit(scraper, product)
        
        self.assertEqual(product.unit, '')
        scraper.scrape_product_details.assert_called_once()
    
    def test_enrich_unit_getattr_exception(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        
        class BrokenProduct:
            @property
            def url(self):
                raise RuntimeError('Cannot access url')
        
        product = BrokenProduct()
        
        scheduler.enrich_unit(scraper, product)
        
        scraper.scrape_product_details.assert_not_called()
    
    def test_enrich_unit_scraper_detail_exception(self):
        scheduler = BaseScheduler()
        scraper = Mock()
        scraper.scrape_product_details = Mock(side_effect=Exception('Network error'))
        
        product = {'name': 'Product', 'price': 100, 'url': 'https://example.com', 'unit': ''}
        
        scheduler.enrich_unit(scraper, product)
        
        self.assertEqual(product['unit'], '')
        scraper.scrape_product_details.assert_called_once()


class TestRunMethod(unittest.TestCase):
    def test_run_with_multiple_vendors(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        summary = s.run(vendors=['gemilang', 'mitra10'])
        
        self.assertEqual(summary['total_vendors'], 2)
        self.assertIn('gemilang', summary['vendors'])
        self.assertIn('mitra10', summary['vendors'])
        self.assertEqual(summary['successful_vendors'], 2)
    
    
    def test_run_with_use_price_update(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_with_update_result={'inserted': 1, 'updated': 0})

        s = S()
        summary = s.run(vendors=['gemilang'], use_price_update=True)
        
        self.assertEqual(summary['vendors']['gemilang']['saved'], 1)
        self.assertEqual(summary['vendors']['gemilang']['status'], 'success')
    
    def test_run_with_max_products_per_keyword(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                products = [
                    {'name': f'p{i}', 'price': i*10, 'url': f'u{i}', 'unit': 'kg'} 
                    for i in range(10)
                ]
                return FakeScraper([FakeResult(success=True, products=products)])

            def load_db_service(self, vendor):
                db = FakeDBService(save_result=True)
                return db

        s = S()
        summary = s.run(vendors=['gemilang'], max_products_per_keyword=3)
        
        self.assertEqual(summary['vendors']['gemilang']['saved'], 3)
    
    def test_run_with_default_vendors(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return []

            def create_scraper(self, vendor):
                return FakeScraper([])

        s = S()
        summary = s.run()
        
        self.assertEqual(summary['total_vendors'], 4)
        self.assertIn('depobangunan', summary['vendors'])
        self.assertIn('gemilang', summary['vendors'])
        self.assertIn('juragan_material', summary['vendors'])
        self.assertIn('mitra10', summary['vendors'])
    
    def test_run_with_timing_delay(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['k']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        expected_time = datetime(2025, 1, 1, 10, 0, 0)
        server_time = datetime(2025, 1, 1, 10, 0, 5)
        summary = s.run(server_time=server_time, expected_start_time=expected_time, vendors=['gemilang'])
        
        self.assertIn('timing_delay_seconds', summary)
        self.assertIsNotNone(summary['timing_delay_seconds'])
    
    def test_run_timing_delay_exception(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['k']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        
        class BadTime:
            def timestamp(self):
                raise RuntimeError('timestamp error')
        
        expected_time = BadTime()
        server_time = datetime(2025, 1, 1, 10, 0, 5)
        summary = s.run(server_time=server_time, expected_start_time=expected_time, vendors=['gemilang'])
        
        self.assertIn('timing_delay_seconds', summary)
        self.assertIsNone(summary['timing_delay_seconds'])
    
    # because the scrape is based on 1 keyword searched, this unit test case is not relevant
    # def test_run_partial_success(self):
    #     class S(BaseScheduler):
    #         def get_categories(self, vendor, server_time):
    #             return ['keyword1', 'keyword2']

    #         def create_scraper(self, vendor):
    #             results = [
    #                 FakeResult(success=True, products=[{'name': 'p1', 'price': 10, 'url': 'u1', 'unit': 'kg'}]),
    #                 FakeResult(success=False, error_message='timeout')
    #             ]
    #             return FakeScraper(results)

    #         def load_db_service(self, vendor):
    #             return FakeDBService(save_result=True)

    #     s = S()
    #     summary = s.run(vendors=['gemilang'])
        
    #      # Debug: Print the actual values
    #     print(f"scrape_attempts: {summary['vendors']['gemilang']['scrape_attempts']}")
    #     print(f"scrape_failures: {summary['vendors']['gemilang']['scrape_failures']}")
    #     print(f"status: {summary['vendors']['gemilang']['status']}")
        
    #     self.assertEqual(summary['vendors']['gemilang']['status'], 'partial_success')
    #     self.assertEqual(summary['vendors']['gemilang']['scrape_failures'], 1)
    #     self.assertEqual(summary['successful_vendors'], 1)
        
    def test_run_no_products_found(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertEqual(summary['vendors']['gemilang']['status'], 'no_products_found')
        self.assertEqual(summary['vendors']['gemilang']['products_found'], 0)
        self.assertEqual(summary['successful_vendors'], 1)
    
    def test_run_critical_exception(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                # Return scraper that raises exception
                class FailingScraper:
                    def scrape_products(self, keyword=None, sort_by_price=False, page=0):
                        raise RuntimeError("Critical scraper error")
                
                return FailingScraper()

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertEqual(summary['vendors']['gemilang']['status'], 'failed_all_scrapes')
        self.assertEqual(summary['failed_vendors'], 1)
        self.assertEqual(summary['successful_vendors'], 0)
        self.assertGreater(len(summary['vendors']['gemilang']['errors']), 0)
    
    def test_run_no_db_service(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return None

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertEqual(summary['vendors']['gemilang']['products_found'], 1)
        self.assertEqual(summary['vendors']['gemilang']['saved'], 0)
    
    def test_run_db_save_returns_tuple(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=(True, 'saved'))

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertEqual(summary['vendors']['gemilang']['saved'], 1)
    
    def test_run_db_save_returns_dict_new_count(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result={'new_count': 1})

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertEqual(summary['vendors']['gemilang']['saved'], 1)
    
    def test_run_db_save_returns_dict_saved(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result={'saved': 1})

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertEqual(summary['vendors']['gemilang']['saved'], 1)
    
    def test_run_db_save_unknown_return(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result='unknown')

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertEqual(summary['vendors']['gemilang']['saved'], 0)
    
    def test_run_scrape_exception_during_loop(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['keyword1']

            def create_scraper(self, vendor):
                scraper = FakeScraper([])
                scraper.scrape_products = Mock(side_effect=Exception('Network error'))
                return scraper

            def load_db_service(self, vendor):
                return FakeDBService()

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertEqual(summary['vendors']['gemilang']['scrape_failures'], 1)
        self.assertGreater(len(summary['vendors']['gemilang']['errors']), 0)
    
    def test_run_summary_structure(self):
        class S(BaseScheduler):
            def get_categories(self, vendor, server_time):
                return ['k']

            def create_scraper(self, vendor):
                return FakeScraper([FakeResult(success=True, products=[{'name': 'p', 'price': 10, 'url': 'u', 'unit': 'kg'}])])

            def load_db_service(self, vendor):
                return FakeDBService(save_result=True)

        s = S()
        summary = s.run(vendors=['gemilang'])
        
        self.assertIn('server_time', summary)
        self.assertIn('start_timestamp', summary)
        self.assertIn('end_timestamp', summary)
        self.assertIn('timing_delay_seconds', summary)
        self.assertIn('vendors', summary)
        self.assertIn('errors', summary)
        self.assertIn('total_vendors', summary)
        self.assertIn('successful_vendors', summary)
        self.assertIn('failed_vendors', summary)
        self.assertIn('total_duration_seconds', summary)


if __name__ == '__main__':
    unittest.main()
