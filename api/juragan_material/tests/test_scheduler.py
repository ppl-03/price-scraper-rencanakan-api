import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from types import SimpleNamespace


class TestJuraganMaterialScheduler(unittest.TestCase):
    
    def _setup_mock_scraper(self, scheduler, categories, products, success=True, db_save_result=(True, None)):
        """Helper method to setup common mock objects for scraper tests"""
        patch.object(scheduler, 'get_categories', return_value=categories).start()
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
        """Test that JuraganMaterialScheduler inherits from BaseScheduler"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        from api.scheduler import BaseScheduler
        self.assertTrue(issubclass(JuraganMaterialScheduler, BaseScheduler))

    def test_scheduler_initialization(self):
        """Test that scheduler can be initialized"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        self.assertIsNotNone(scheduler)

    def test_get_categories_returns_list(self):
        """Test that get_categories returns a list"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        server_time = datetime.now()
        categories = scheduler.get_categories('juragan_material', server_time)
        self.assertIsInstance(categories, list)

    def test_run_without_arguments(self):
        """Test running scheduler without arguments defaults to juragan_material"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        products = [SimpleNamespace(name='Product', price='100', url='https://test.com', unit='pcs')]
        self._setup_mock_scraper(scheduler, ['test'], products)
        
        result = scheduler.run()
        self.assertIn('juragan_material', result['vendors'])

    def test_run_with_custom_vendors(self):
        """Test running scheduler with custom vendor list"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        self._setup_mock_scraper(scheduler, ['test'], [], db_save_result=None)
        
        result = scheduler.run(vendors=['juragan_material'])
        self.assertEqual(result['total_vendors'], 1)
        self.assertIn('juragan_material', result['vendors'])

    def test_run_single_page(self):
        """Test scraping single page per keyword"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        products = [SimpleNamespace(name='P1', price='50', url='https://url', unit='box')]
        self._setup_mock_scraper(scheduler, ['category1'], products)
        
        result = scheduler.run(vendors=['juragan_material'], pages_per_keyword=1)
        vendor_data = result['vendors']['juragan_material']
        self.assertEqual(vendor_data['scrape_attempts'], 1)

    def test_run_multiple_pages(self):
        """Test scraping multiple pages per keyword"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        self._setup_mock_scraper(scheduler, ['cat1'], [], db_save_result=None)
        
        result = scheduler.run(vendors=['juragan_material'], pages_per_keyword=3)
        self.assertEqual(result['vendors']['juragan_material']['scrape_attempts'], 3)

    def test_run_products_saved(self):
        """Test that scraped products are saved correctly"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        products = [
            SimpleNamespace(name='P1', price='10', url='https://1', unit='pcs'),
            SimpleNamespace(name='P2', price='20', url='https://2', unit='box')
        ]
        self._setup_mock_scraper(scheduler, ['test'], products)
        
        result = scheduler.run(vendors=['juragan_material'], pages_per_keyword=1)
        self.assertEqual(result['vendors']['juragan_material']['saved'], 2)

    def test_run_with_scrape_failure(self):
        """Test handling of scrape failures (negative case)"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        self._setup_mock_scraper(scheduler, ['test'], [], success=False, db_save_result=None)
        
        result = scheduler.run(vendors=['juragan_material'])
        self.assertEqual(result['vendors']['juragan_material']['saved'], 0)

    def test_run_with_empty_products(self):
        """Test handling when no products are found (edge case)"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        self._setup_mock_scraper(scheduler, ['test'], [], db_save_result=None)
        
        result = scheduler.run(vendors=['juragan_material'])
        self.assertEqual(result['vendors']['juragan_material']['saved'], 0)

    def test_run_with_price_update_enabled(self):
        """Test running scheduler with price update enabled"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        products = [SimpleNamespace(name='P1', price='100', url='https://test', unit='pcs')]
        self._setup_mock_scraper(scheduler, ['test'], products)
        
        result = scheduler.run(vendors=['juragan_material'], use_price_update=True)
        self.assertIn('juragan_material', result['vendors'])

    def test_run_with_max_products_limit(self):
        """Test running scheduler with max products limit (edge case)"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        products = [
            SimpleNamespace(name=f'P{i}', price=f'{i*10}', url=f'https://{i}', unit='pcs')
            for i in range(10)
        ]
        self._setup_mock_scraper(scheduler, ['test'], products)
        
        result = scheduler.run(vendors=['juragan_material'], max_products_per_keyword=5)
        self.assertIn('juragan_material', result['vendors'])

    def test_run_converts_vendors_to_list(self):
        """Test that vendors tuple is converted to list (edge case)"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        self._setup_mock_scraper(scheduler, ['test'], [], db_save_result=None)
        
        # Pass tuple instead of list
        result = scheduler.run(vendors=('juragan_material',))
        self.assertIn('juragan_material', result['vendors'])

    def test_run_with_db_save_failure(self):
        """Test handling of database save failures (negative case)"""
        from api.juragan_material.scheduler import JuraganMaterialScheduler
        scheduler = JuraganMaterialScheduler()
        
        products = [SimpleNamespace(name='P1', price='100', url='https://test', unit='pcs')]
        self._setup_mock_scraper(scheduler, ['test'], products, db_save_result=(False, "Database error"))
        
        result = scheduler.run(vendors=['juragan_material'])
        # Should still complete even with save failure
        self.assertIn('juragan_material', result['vendors'])