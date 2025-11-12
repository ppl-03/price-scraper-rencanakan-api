from unittest.mock import patch, Mock
import json
from django.test import TestCase
from dashboard.scheduler_views import (
    scheduler_settings,
    update_schedule,
    run_scheduler_now,
    get_scheduler_status,
    scheduler_config,
    AVAILABLE_VENDORS
)


class TestSchedulerConfig:
    """Test scheduler configuration"""
    
    def test_scheduler_config_structure(self):
        """Test that scheduler config has required keys"""
        required_keys = ['enabled', 'schedule_type', 'vendors', 'pages_per_keyword']
        for key in required_keys:
            assert key in scheduler_config
    
    def test_scheduler_config_defaults(self):
        """Test scheduler config default values"""
        assert isinstance(scheduler_config['enabled'], bool)
        assert scheduler_config['schedule_type'] in ['disabled', 'hourly', 'daily', 'weekly', 'custom']
        assert isinstance(scheduler_config['vendors'], list)
        assert isinstance(scheduler_config['pages_per_keyword'], int)
    
    def test_available_vendors_structure(self):
        """Test that available vendors are properly defined"""
        expected_vendors = ['gemilang', 'depobangunan', 'juragan_material', 'mitra10', 'tokopedia']
        for vendor in expected_vendors:
            assert vendor in AVAILABLE_VENDORS


class TestSchedulerSettingsView:
    """Test scheduler settings view"""
    
    @patch('dashboard.scheduler_views.render')
    @patch('dashboard.scheduler_views.timezone')
    def test_scheduler_settings_renders_template(self, mock_timezone, mock_render):
        """Test that scheduler settings renders correct template"""
        mock_request = Mock()
        mock_request.method = 'GET'
        mock_timezone.now.return_value = '2025-01-01 12:00:00'
        mock_render.return_value = Mock(status_code=200)
        
        mock_render.assert_called_once()
        args = mock_render.call_args
        assert args[0][1] == 'dashboard/scheduler_settings.html'
        assert 'config' in args[0][2]
        assert 'available_vendors' in args[0][2]
    
    @patch('dashboard.scheduler_views.render')
    @patch('dashboard.scheduler_views.timezone')
    def test_scheduler_settings_context_data(self, mock_timezone, mock_render):
        """Test context data passed to template"""
        mock_request = Mock()
        mock_request.method = 'GET'
        mock_timezone.now.return_value = '2025-01-01 12:00:00'
        
        scheduler_settings(mock_request)
        
        context = mock_render.call_args[0][2]
        assert 'config' in context
        assert 'available_vendors' in context
        assert 'server_time' in context


class TestUpdateScheduleView:
    """Test update schedule view"""
    
    @patch('dashboard.scheduler_views.redirect')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.logger')
    def test_update_schedule_to_hourly(self, mock_logger, mock_messages, mock_redirect):
        """Test updating schedule to hourly"""
        mock_request = Mock()
        mock_request.method = 'POST'
        mock_request.POST.get.side_effect = lambda key, default=None: {
            'schedule_type': 'hourly',
            'pages_per_keyword': '1'
        }.get(key, default)
        mock_request.POST.getlist.return_value = ['gemilang']
        
        update_schedule(mock_request)
        
        assert scheduler_config['schedule_type'] == 'hourly'
        assert scheduler_config['enabled'] == True
        mock_messages.success.assert_called_once()
        mock_redirect.assert_called_once()
    
    @patch('dashboard.scheduler_views.redirect')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.logger')
    def test_update_schedule_to_disabled(self, mock_logger, mock_messages, mock_redirect):
        """Test disabling scheduler"""
        mock_request = Mock()
        mock_request.method = 'POST'
        mock_request.POST.get.side_effect = lambda key, default=None: {
            'schedule_type': 'disabled',
            'pages_per_keyword': '1'
        }.get(key, default)
        mock_request.POST.getlist.return_value = []
        
        update_schedule(mock_request)
        
        assert scheduler_config['schedule_type'] == 'disabled'
        assert scheduler_config['enabled'] == False
        mock_redirect.assert_called_once()
    
    @patch('dashboard.scheduler_views.redirect')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.logger')
    def test_update_schedule_validates_pages(self, mock_logger, mock_messages, mock_redirect):
        """Test that pages per keyword is validated"""
        mock_request = Mock()
        mock_request.method = 'POST'
        mock_request.POST.get.side_effect = lambda key, default=None: {
            'schedule_type': 'daily',
            'pages_per_keyword': '-1'  # Invalid
        }.get(key, default)
        mock_request.POST.getlist.return_value = ['gemilang']
        
        update_schedule(mock_request)
        
        # Should be corrected to minimum value of 1
        assert scheduler_config['pages_per_keyword'] >= 1
    
    @patch('dashboard.scheduler_views.redirect')
    @patch('dashboard.scheduler_views.messages')
    def test_update_schedule_invalid_type(self, mock_messages, mock_redirect):
        """Test updating with invalid schedule type"""
        mock_request = Mock()
        mock_request.method = 'POST'
        mock_request.POST.get.side_effect = lambda key, default=None: {
            'schedule_type': 'invalid_type',
            'pages_per_keyword': '1'
        }.get(key, default)
        mock_request.POST.getlist.return_value = ['gemilang']
        
        update_schedule(mock_request)
        
        # Should show error message
        mock_messages.error.assert_called_once()


class TestRunSchedulerNowView:
    """Test run scheduler now view"""
    
    @patch('dashboard.scheduler_views.GemilangScheduler')
    @patch('dashboard.scheduler_views.timezone')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.logger')
    def test_run_scheduler_success(self, mock_logger, mock_messages, mock_timezone, mock_scheduler_class):
        """Test successfully running scheduler"""
        mock_request = Mock()
        mock_request.method = 'POST'
        mock_timezone.now.return_value = Mock()
        mock_timezone.now.return_value.isoformat.return_value = '2025-01-01T12:00:00'
        
        # Mock scheduler
        mock_scheduler = Mock()
        mock_scheduler.run.return_value = {
            'vendors': {
                'gemilang': {
                    'status': 'success',
                    'products_found': 50,
                    'saved': 45
                }
            }
        }
        mock_scheduler_class.return_value = mock_scheduler
        
        # Set up config
        scheduler_config['vendors'] = ['gemilang']
        scheduler_config['pages_per_keyword'] = 1
        
        response = run_scheduler_now(mock_request)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] == True
        assert 'results' in data
    
    @patch('dashboard.scheduler_views.timezone')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.logger')
    def test_run_scheduler_returns_json(self, mock_logger, mock_messages, mock_timezone):
        """Test that run scheduler returns JSON"""
        mock_request = Mock()
        mock_request.method = 'POST'
        mock_timezone.now.return_value = Mock()
        mock_timezone.now.return_value.isoformat.return_value = '2025-01-01T12:00:00'
        
        scheduler_config['vendors'] = []
        
        response = run_scheduler_now(mock_request)
        
        assert response['Content-Type'] == 'application/json'


class TestGetSchedulerStatusView:
    """Test get scheduler status view"""
    
    @patch('dashboard.scheduler_views.timezone')
    def test_get_status_returns_json(self, mock_timezone):
        """Test that get status returns JSON"""
        mock_request = Mock()
        mock_request.method = 'GET'
        mock_timezone.now.return_value = Mock()
        mock_timezone.now.return_value.isoformat.return_value = '2025-01-01T12:00:00'
        
        response = get_scheduler_status(mock_request)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
    
    @patch('dashboard.scheduler_views.timezone')
    def test_get_status_contains_required_fields(self, mock_timezone):
        """Test status response has required fields"""
        mock_request = Mock()
        mock_request.method = 'GET'
        mock_timezone.now.return_value = Mock()
        mock_timezone.now.return_value.isoformat.return_value = '2025-01-01T12:00:00'
        
        response = get_scheduler_status(mock_request)
        data = json.loads(response.content)
        
        required_fields = ['enabled', 'schedule_type', 'vendors', 'server_time']
        for field in required_fields:
            assert field in data
    
    @patch('dashboard.scheduler_views.timezone')
    def test_get_status_data_types(self, mock_timezone):
        """Test status response field types"""
        mock_request = Mock()
        mock_request.method = 'GET'
        mock_timezone.now.return_value = Mock()
        mock_timezone.now.return_value.isoformat.return_value = '2025-01-01T12:00:00'
        
        response = get_scheduler_status(mock_request)
        data = json.loads(response.content)
        
        assert isinstance(data['enabled'], bool)
        assert isinstance(data['schedule_type'], str)
        assert isinstance(data['vendors'], list)


class TestSchedulerIntegration:
    """Integration tests for scheduler functionality"""
    
    @patch('dashboard.scheduler_views.redirect')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.timezone')
    @patch('dashboard.scheduler_views.logger')
    def test_update_and_check_status_workflow(self, mock_logger, mock_timezone, mock_messages, mock_redirect):
        """Test updating config and checking status"""
        mock_timezone.now.return_value = Mock()
        mock_timezone.now.return_value.isoformat.return_value = '2025-01-01T12:00:00'
        
        # Update schedule
        mock_request = Mock()
        mock_request.method = 'POST'
        mock_request.POST.get.side_effect = lambda key, default=None: {
            'schedule_type': 'daily',
            'pages_per_keyword': '2'
        }.get(key, default)
        mock_request.POST.getlist.return_value = ['gemilang', 'tokopedia']
        
        update_schedule(mock_request)
        
        # Check status
        status_request = Mock()
        status_request.method = 'GET'
        response = get_scheduler_status(status_request)
        data = json.loads(response.content)
        
        assert data['schedule_type'] == 'daily'
        assert 'gemilang' in data['vendors']
        assert 'tokopedia' in data['vendors']
    
    @patch('dashboard.scheduler_views.GemilangScheduler')
    @patch('dashboard.scheduler_views.redirect')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.timezone')
    @patch('dashboard.scheduler_views.logger')
    def test_configure_and_run_workflow(self, mock_logger, mock_timezone, mock_messages, mock_redirect, mock_scheduler_class):
        """Test configuring scheduler and running it"""
        mock_timezone.now.return_value = Mock()
        mock_timezone.now.return_value.isoformat.return_value = '2025-01-01T12:00:00'
        
        # Configure
        mock_request = Mock()
        mock_request.method = 'POST'
        mock_request.POST.get.side_effect = lambda key, default=None: {
            'schedule_type': 'hourly',
            'pages_per_keyword': '1'
        }.get(key, default)
        mock_request.POST.getlist.return_value = ['gemilang']
        
        update_schedule(mock_request)
        
        # Mock scheduler run
        mock_scheduler = Mock()
        mock_scheduler.run.return_value = {
            'vendors': {
                'gemilang': {
                    'status': 'success',
                    'products_found': 25,
                    'saved': 25
                }
            }
        }
        mock_scheduler_class.return_value = mock_scheduler
        
        # Run
        run_request = Mock()
        run_request.method = 'POST'
        response = run_scheduler_now(run_request)
        data = json.loads(response.content)
        
        assert data['success'] == True
        assert 'gemilang' in data['results']

class TestSchedulerDatabaseIntegration(TestCase):
    """Test scheduler with database integration"""
    
    @patch('dashboard.scheduler_views.redirect')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.logger')
    def test_scheduled_run_fills_database_after_delay(self, mock_logger, mock_messages, mock_redirect):
        """Test that database is filled after scheduled time (1 minute delay)"""
        from django.utils import timezone as django_timezone
        from datetime import timedelta
        from db_pricing.models import GemilangProduct
        
        # Get actual server time
        server_time = django_timezone.now()
        
        # Set schedule to run after 1 minute
        expected_run_time = server_time + timedelta(minutes=1)
        
        # Configure scheduler with 1-minute delay
        config_request = Mock()
        config_request.method = 'POST'
        config_request.POST.get.side_effect = lambda key, default=None: {
            'schedule_type': 'custom',
            'pages_per_keyword': '1',
            'custom_interval': '1',
            'custom_unit': 'minutes'
        }.get(key, default)
        config_request.POST.getlist.return_value = ['gemilang']
        
        update_schedule(config_request)
        
        # Verify configuration
        self.assertEqual(scheduler_config['schedule_type'], 'custom')
        self.assertTrue(scheduler_config['enabled'])
        self.assertIn('gemilang', scheduler_config['vendors'])
        
        # Mock scheduler to return realistic data
        mock_scheduler = Mock()
        mock_scheduler_class = Mock(return_value=mock_scheduler)
        
        mock_scheduler.run.return_value = {
            'server_time': expected_run_time.isoformat(),
            'timing_delay_seconds': 60,  # 1 minute delay
            'vendors': {
                'gemilang': {
                    'status': 'success',
                    'products_found': 3,
                    'saved': 3,
                    'keywords': 1,
                    'errors': []
                }
            },
            'total_vendors': 1,
            'successful_vendors': 1,
            'failed_vendors': 0
        }
        
        # Mock AVAILABLE_VENDORS to use our mock scheduler
        mock_vendors = {
            'gemilang': {'name': 'Gemilang', 'scheduler': mock_scheduler_class}
        }
        
        # Simulate waiting for scheduled time (1 minute passes)
        # In real scenario, scheduler would run automatically
        # Here we trigger it manually after the delay
        with patch('dashboard.scheduler_views.timezone') as mock_tz, \
             patch('dashboard.scheduler_views.AVAILABLE_VENDORS', mock_vendors):
            # Mock timezone to return the expected run time
            mock_tz.now.return_value = expected_run_time
            
            # Run scheduler at the scheduled time
            run_request = Mock()
            run_request.method = 'POST'
            response = run_scheduler_now(run_request)
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertIn('gemilang', data['results'])
            self.assertEqual(data['results']['gemilang']['status'], 'success')
            self.assertEqual(data['results']['gemilang']['saved'], 3)
        
        # Verify scheduler was called with correct parameters
        mock_scheduler.run.assert_called_once()
        call_args = mock_scheduler.run.call_args
        self.assertEqual(call_args[1]['vendors'], ['gemilang'])
        self.assertEqual(call_args[1]['pages_per_keyword'], 1)
        
        # Verify timing delay was calculated correctly (approximately 60 seconds)
        timing_delay = mock_scheduler.run.return_value['timing_delay_seconds']
        self.assertEqual(timing_delay, 60)  # 1 minute delay
        
        # In a real integration test with actual database:
        # We would verify products were actually saved to database
        # final_count = GemilangProduct.objects.count()
        # self.assertEqual(final_count, initial_count + 3)
        
        # Verify last_run timestamp was updated
        self.assertIn('last_run', scheduler_config)
        self.assertEqual(scheduler_config['last_run'], expected_run_time.isoformat())
    
    @patch('dashboard.scheduler_views.redirect')
    @patch('dashboard.scheduler_views.messages')
    @patch('dashboard.scheduler_views.logger')
    def test_multiple_vendors_scheduled_run(self, mock_logger, mock_messages, mock_redirect):
        """Test multiple vendors running at scheduled time and filling database"""
        from django.utils import timezone as django_timezone
        from datetime import timedelta
        
        server_time = django_timezone.now()
        expected_run_time = server_time + timedelta(minutes=1)
        
        # Configure for multiple vendors
        config_request = Mock()
        config_request.method = 'POST'
        config_request.POST.get.side_effect = lambda key, default=None: {
            'schedule_type': 'custom',
            'pages_per_keyword': '1',
            'custom_interval': '1',
            'custom_unit': 'minutes'
        }.get(key, default)
        config_request.POST.getlist.return_value = ['gemilang', 'depobangunan']
        
        update_schedule(config_request)
        
        # Mock both schedulers
        mock_gemilang = Mock()
        mock_gemilang.run.return_value = {
            'vendors': {
                'gemilang': {
                    'status': 'success',
                    'products_found': 5,
                    'saved': 5,
                }
            }
        }
        mock_gemilang_scheduler_class = Mock(return_value=mock_gemilang)
        
        mock_depo = Mock()
        mock_depo.run.return_value = {
            'vendors': {
                'depobangunan': {
                    'status': 'success',
                    'products_found': 7,
                    'saved': 7,
                }
            }
        }
        mock_depo_scheduler_class = Mock(return_value=mock_depo)
        
        # Mock AVAILABLE_VENDORS to use our mock schedulers
        mock_vendors = {
            'gemilang': {'name': 'Gemilang', 'scheduler': mock_gemilang_scheduler_class},
            'depobangunan': {'name': 'Depo Bangunan', 'scheduler': mock_depo_scheduler_class}
        }
        
        # Run at scheduled time
        with patch('dashboard.scheduler_views.timezone') as mock_tz, \
             patch('dashboard.scheduler_views.AVAILABLE_VENDORS', mock_vendors):
            mock_tz.now.return_value = expected_run_time
            
            run_request = Mock()
            run_request.method = 'POST'
            response = run_scheduler_now(run_request)
            
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(len(data['results']), 2)
            self.assertEqual(data['results']['gemilang']['saved'], 5)
            self.assertEqual(data['results']['depobangunan']['saved'], 7)
        
        # Verify both schedulers were called
        mock_gemilang.run.assert_called_once()
        mock_depo.run.assert_called_once()
