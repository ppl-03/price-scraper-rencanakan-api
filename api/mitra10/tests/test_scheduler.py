import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from types import SimpleNamespace


class TestMitra10Scheduler(unittest.TestCase):
    
    def _setup_mock_scraper(self, scheduler, products, success=True, db_save_result=(True, None)):
        """Helper method to setup common mock objects for scraper tests"""
        mock_scraper = patch.object(scheduler, 'create_scraper').start()
        mock_result = SimpleNamespace(success=success, products=products)
        mock_scraper.return_value.scrape_products.return_value = mock_result
        
        if db_save_result is not None:
            mock_db = patch.object(scheduler, 'load_db_service').start()
            mock_db.return_value.save.return_value = db_save_result
        else:
            patch.object(scheduler, 'load_db_service', return_value=None).start()
        
        self.addCleanup(patch.stopall)
    
    def test_scheduler_imports_base_scheduler(self):
        """Test that Mitra10Scheduler inherits from BaseScheduler"""
        from api.mitra10.scheduler import Mitra10Scheduler
        from api.scheduler import BaseScheduler
        self.assertTrue(issubclass(Mitra10Scheduler, BaseScheduler))

    def test_scheduler_initialization(self):
        """Test that scheduler can be initialized"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        self.assertIsNotNone(scheduler)

    def test_get_categories_returns_list(self):
        """Test that get_categories returns a list"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        server_time = datetime.now()
        categories = scheduler.get_categories('mitra10', server_time)
        self.assertIsInstance(categories, list)

    def test_run_with_search_keyword(self):
        """Test running scheduler with search keyword"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        products = [SimpleNamespace(name='Product', price='100', url='https://test.com', unit='pcs')]
        self._setup_mock_scraper(scheduler, products)
        
        result = scheduler.run(vendors=['mitra10'], search_keyword='semen')
        self.assertIn('mitra10', result['vendors'])
        self.assertEqual(result['vendors']['mitra10']['scrape_attempts'], 1)

    def test_run_with_custom_vendors(self):
        """Test running scheduler with custom vendor list"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        self._setup_mock_scraper(scheduler, [], db_save_result=None)
        
        result = scheduler.run(vendors=['mitra10'], search_keyword='besi')
        self.assertEqual(result['total_vendors'], 1)
        self.assertIn('mitra10', result['vendors'])

    def test_run_single_scrape_attempt(self):
        """Test that scheduler makes only one scrape attempt per vendor with keyword"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        products = [SimpleNamespace(name='P1', price='50', url='https://url', unit='box')]
        self._setup_mock_scraper(scheduler, products)
        
        result = scheduler.run(vendors=['mitra10'], search_keyword='paku')
        vendor_data = result['vendors']['mitra10']
        self.assertEqual(vendor_data['scrape_attempts'], 1)

    def test_run_scraper_creation_fails(self):
        """Test handling when scraper creation fails"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        with patch.object(scheduler, 'create_scraper', side_effect=Exception('Scraper error')):
            result = scheduler.run(vendors=['mitra10'], search_keyword='test')
            self.assertEqual(result['vendors']['mitra10']['status'], 'failed_scraper_creation')
            self.assertEqual(result['failed_vendors'], 1)

    def test_run_products_saved(self):
        """Test that scraped products are saved correctly"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        products = [
            SimpleNamespace(name='P1', price='10', url='https://1', unit='pcs'),
            SimpleNamespace(name='P2', price='20', url='https://2', unit='box')
        ]
        self._setup_mock_scraper(scheduler, products)
        
        result = scheduler.run(vendors=['mitra10'], search_keyword='cat')
        self.assertEqual(result['vendors']['mitra10']['saved'], 2)
        self.assertEqual(result['vendors']['mitra10']['products_found'], 2)

    def test_run_with_scrape_failure(self):
        """Test handling of scrape failures (negative case)"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        self._setup_mock_scraper(scheduler, [], success=False, db_save_result=None)
        
        result = scheduler.run(vendors=['mitra10'], search_keyword='test')
        self.assertEqual(result['vendors']['mitra10']['scrape_failures'], 1)

    def test_run_with_empty_products(self):
        """Test handling when no products are found (edge case)"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        self._setup_mock_scraper(scheduler, [], db_save_result=None)
        
        result = scheduler.run(vendors=['mitra10'], search_keyword='test')
        self.assertEqual(result['vendors']['mitra10']['status'], 'no_products_found')

    def test_run_with_price_update_enabled(self):
        """Test running scheduler with price update enabled"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        products = [SimpleNamespace(name='P1', price='100', url='https://test', unit='pcs')]
        self._setup_mock_scraper(scheduler, products)
        
        result = scheduler.run(vendors=['mitra10'], search_keyword='test', use_price_update=True)
        self.assertIn('mitra10', result['vendors'])

    def test_run_with_max_products_limit(self):
        """Test running scheduler with max products limit (edge case)"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        products = [
            SimpleNamespace(name=f'P{i}', price=f'{i*10}', url=f'https://{i}', unit='pcs')
            for i in range(10)
        ]
        self._setup_mock_scraper(scheduler, products)
        
        result = scheduler.run(vendors=['mitra10'], search_keyword='test', max_products_per_keyword=5)
        self.assertEqual(result['vendors']['mitra10']['saved'], 5)

    def test_run_converts_vendors_to_list(self):
        """Test that vendors tuple is converted to list (edge case)"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        self._setup_mock_scraper(scheduler, ['test'], [], db_save_result=None)
        
        # Pass tuple instead of list
        result = scheduler.run(vendors=('mitra10',))
        self.assertIn('mitra10', result['vendors'])

    def test_run_with_db_save_failure(self):
        """Test handling of database save failures (negative case)"""
        from api.mitra10.scheduler import Mitra10Scheduler
        scheduler = Mitra10Scheduler()
        
        products = [SimpleNamespace(name='P1', price='100', url='https://test', unit='pcs')]
        self._setup_mock_scraper(scheduler, ['test'], products, db_save_result=(False, "Database error"))
        
        result = scheduler.run(vendors=['mitra10'])
        # Should still complete even with save failure
        self.assertIn('mitra10', result['vendors'])