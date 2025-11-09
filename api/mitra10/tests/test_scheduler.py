from unittest.mock import patch, MagicMock
from django.test import TestCase
from api.mitra10.scheduler import Mitra10Scheduler


class TestMitra10Scheduler(TestCase):
    def setUp(self):
        self.scheduler = Mitra10Scheduler()

    @patch('api.scheduler.BaseScheduler.run')
    def test_run_with_default_vendors(self, mock_base_run):
        """Test that run method defaults to mitra10 vendor"""
        mock_base_run.return_value = {'status': 'success'}
        
        result = self.scheduler.run()
        
        mock_base_run.assert_called_once_with(
            server_time=None,
            vendors=['mitra10'],
            pages_per_keyword=1,
            use_price_update=False,
            max_products_per_keyword=None,
            expected_start_time=None
        )
        self.assertEqual(result, {'status': 'success'})

    @patch('api.scheduler.BaseScheduler.run')
    def test_run_with_custom_vendors(self, mock_base_run):
        """Test that run method accepts custom vendors"""
        mock_base_run.return_value = {'status': 'success'}
        custom_vendors = ['mitra10', 'other_vendor']
        
        result = self.scheduler.run(vendors=custom_vendors)
        
        mock_base_run.assert_called_once_with(
            server_time=None,
            vendors=['mitra10', 'other_vendor'],
            pages_per_keyword=1,
            use_price_update=False,
            max_products_per_keyword=None,
            expected_start_time=None
        )

    @patch('api.scheduler.BaseScheduler.run')
    def test_run_with_all_parameters(self, mock_base_run):
        """Test that run method passes all parameters correctly"""
        mock_base_run.return_value = {'status': 'success'}
        
        result = self.scheduler.run(
            server_time='2024-01-01 10:00:00',
            vendors=['mitra10'],
            pages_per_keyword=3,
            use_price_update=True,
            max_products_per_keyword=50,
            expected_start_time='2024-01-01 09:00:00'
        )
        
        mock_base_run.assert_called_once_with(
            server_time='2024-01-01 10:00:00',
            vendors=['mitra10'],
            pages_per_keyword=3,
            use_price_update=True,
            max_products_per_keyword=50,
            expected_start_time='2024-01-01 09:00:00'
        )
        self.assertEqual(result, {'status': 'success'})

    @patch('api.scheduler.BaseScheduler.run')
    def test_run_converts_vendors_to_list(self, mock_base_run):
        """Test that vendors parameter is converted to list"""
        mock_base_run.return_value = {'status': 'success'}
        
        result = self.scheduler.run(vendors=('mitra10', 'vendor2'))
        
        # Verify vendors was converted to list
        call_args = mock_base_run.call_args
        self.assertIsInstance(call_args[1]['vendors'], list)
        self.assertEqual(call_args[1]['vendors'], ['mitra10', 'vendor2'])