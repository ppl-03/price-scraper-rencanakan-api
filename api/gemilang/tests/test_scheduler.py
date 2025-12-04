import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from types import SimpleNamespace


class TestGemilangScheduler(unittest.TestCase):
    def test_scheduler_imports_base_scheduler(self):
        from api.gemilang.scheduler import GemilangScheduler
        from api.scheduler import BaseScheduler
        self.assertTrue(issubclass(GemilangScheduler, BaseScheduler))

    def test_scheduler_initialization(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        self.assertIsNotNone(scheduler)

    def test_get_categories_returns_list(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        server_time = datetime.now()
        categories = scheduler.get_categories('gemilang', server_time)
        self.assertIsInstance(categories, list)

    def test_run_without_arguments(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=['test']):
            with patch.object(scheduler, 'create_scraper') as mock_scraper:
                mock_result = SimpleNamespace(
                    success=True,
                    products=[SimpleNamespace(name='Product', price='100', url='https://test.com', unit='pcs')]
                )
                mock_scraper.return_value.scrape_products.return_value = mock_result
                
                with patch.object(scheduler, 'load_db_service') as mock_db:
                    mock_db.return_value.save.return_value = (True, None)
                    
                    result = scheduler.run()
                    self.assertIn('gemilang', result['vendors'])

    def test_run_with_custom_vendors(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=['test']):
            with patch.object(scheduler, 'create_scraper') as mock_scraper:
                mock_result = SimpleNamespace(success=True, products=[])
                mock_scraper.return_value.scrape_products.return_value = mock_result
                
                with patch.object(scheduler, 'load_db_service', return_value=None):
                    result = scheduler.run(vendors=['gemilang'])
                    self.assertEqual(result['total_vendors'], 1)
                    self.assertIn('gemilang', result['vendors'])

    def test_run_single_page(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=['category1']):
            with patch.object(scheduler, 'create_scraper') as mock_scraper:
                mock_result = SimpleNamespace(
                    success=True,
                    products=[SimpleNamespace(name='P1', price='50', url='https://url', unit='box')]
                )
                mock_scraper.return_value.scrape_products.return_value = mock_result
                
                with patch.object(scheduler, 'load_db_service') as mock_db:
                    mock_db.return_value.save.return_value = (True, None)
                    
                    result = scheduler.run(vendors=['gemilang'], search_keyword="semen")
                    vendor_data = result['vendors']['gemilang']
                    self.assertEqual(vendor_data['scrape_attempts'], 1)

    def test_run_products_saved(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=['test']):
            with patch.object(scheduler, 'create_scraper') as mock_scraper:
                products = [
                    SimpleNamespace(name='P1', price='10', url='https://1', unit='pcs'),
                    SimpleNamespace(name='P2', price='20', url='https://2', unit='box')
                ]
                mock_result = SimpleNamespace(success=True, products=products)
                mock_scraper.return_value.scrape_products.return_value = mock_result
                
                with patch.object(scheduler, 'load_db_service') as mock_db:
                    mock_db.return_value.save.return_value = (True, None)
                    
                    result = scheduler.run(vendors=['gemilang'])
                    self.assertEqual(result['vendors']['gemilang']['saved'], 2)
                    self.assertEqual(result['vendors']['gemilang']['products_found'], 2)

    # No categorizer for each vendor
    # def test_run_no_categories(self):
    #     from api.gemilang.scheduler import GemilangScheduler
    #     scheduler = GemilangScheduler()
        
    #     with patch.object(scheduler, 'get_categories', return_value=[]):
    #         result = scheduler.run(vendors=['gemilang'], search_keyword="semen")
    #         self.assertEqual(result['vendors']['gemilang']['status'], 'skipped_no_categories')
    #         self.assertEqual(result['failed_vendors'], 1)

    def test_run_scraper_creation_fails(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=['test']):
            with patch.object(scheduler, 'create_scraper', side_effect=Exception('Scraper error')):
                result = scheduler.run(vendors=['gemilang'])
                self.assertEqual(result['vendors']['gemilang']['status'], 'failed_scraper_creation')
                self.assertEqual(result['failed_vendors'], 1)

    def test_run_scrape_fails(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=['test']):
            with patch.object(scheduler, 'create_scraper') as mock_scraper:
                mock_result = SimpleNamespace(success=False, error_message='Scrape failed')
                mock_scraper.return_value.scrape_products.return_value = mock_result
                
                with patch.object(scheduler, 'load_db_service', return_value=None):
                    result = scheduler.run(vendors=['gemilang'])
                    self.assertEqual(result['vendors']['gemilang']['scrape_failures'], 1)

    def test_run_db_service_not_available(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=['test']):
            with patch.object(scheduler, 'create_scraper') as mock_scraper:
                mock_result = SimpleNamespace(
                    success=True,
                    products=[SimpleNamespace(name='P', price='1', url='https://u', unit='pc')]
                )
                mock_scraper.return_value.scrape_products.return_value = mock_result
                
                with patch.object(scheduler, 'load_db_service', return_value=None):
                    result = scheduler.run(vendors=['gemilang'])
                    self.assertEqual(result['vendors']['gemilang']['saved'], 0)

    def test_run_with_timing_metadata(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        expected_time = datetime(2024, 1, 1, 12, 0, 0)
        server_time = datetime(2024, 1, 1, 12, 0, 5)
        
        with patch.object(scheduler, 'get_categories', return_value=[]):
            result = scheduler.run(
                server_time=server_time,
                vendors=['gemilang'],
                expected_start_time=expected_time
            )
            self.assertIsNotNone(result.get('timing_delay_seconds'))

    def test_run_success_status(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=['test']):
            with patch.object(scheduler, 'create_scraper') as mock_scraper:
                mock_result = SimpleNamespace(
                    success=True,
                    products=[SimpleNamespace(name='P', price='10', url='https://test', unit='kg')]
                )
                mock_scraper.return_value.scrape_products.return_value = mock_result
                
                with patch.object(scheduler, 'load_db_service') as mock_db:
                    mock_db.return_value.save.return_value = (True, None)
                    
                    result = scheduler.run(vendors=['gemilang'])
                    self.assertEqual(result['vendors']['gemilang']['status'], 'success')
                    self.assertEqual(result['successful_vendors'], 1)

    def test_run_returns_summary(self):
        from api.gemilang.scheduler import GemilangScheduler
        scheduler = GemilangScheduler()
        
        with patch.object(scheduler, 'get_categories', return_value=[]):
            result = scheduler.run(vendors=['gemilang'])
            self.assertIn('server_time', result)
            self.assertIn('start_timestamp', result)
            self.assertIn('total_duration_seconds', result)
            self.assertIn('vendors', result)
            self.assertIn('total_vendors', result)
