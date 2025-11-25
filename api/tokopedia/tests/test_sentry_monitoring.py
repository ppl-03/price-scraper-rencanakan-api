from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock, call
import json
import sentry_sdk
from api.tokopedia.sentry_monitoring import (
    TokopediaSentryMonitor,
    TokopediaTaskMonitor,
    track_tokopedia_transaction,
    monitor_tokopedia_function
)


class TokopediaSentryMonitorTests(TestCase):
    """Test TokopediaSentryMonitor class methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_keyword = "laptop"
        self.test_page = 0
    
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_context')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_tag')
    def test_set_scraping_context_basic(self, mock_set_tag, mock_set_context):
        """Test setting basic scraping context"""
        TokopediaSentryMonitor.set_scraping_context(
            keyword=self.test_keyword,
            page=self.test_page
        )
        
        # Verify set_context was called with scraping_context
        mock_set_context.assert_called_once()
        call_args = mock_set_context.call_args
        self.assertEqual(call_args[0][0], "scraping_context")
        context_data = call_args[0][1]
        self.assertEqual(context_data['keyword'], self.test_keyword)
        self.assertEqual(context_data['page'], self.test_page)
        self.assertEqual(context_data['vendor'], "tokopedia")
        
        # Verify tags were set
        self.assertEqual(mock_set_tag.call_count, 3)
        tag_calls = [c[0] for c in mock_set_tag.call_args_list]
        self.assertIn(('vendor', 'tokopedia'), tag_calls)
        self.assertIn(('search_keyword', self.test_keyword), tag_calls)
    
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_context')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_tag')
    def test_set_scraping_context_with_additional_data(self, mock_set_tag, mock_set_context):
        """Test setting scraping context with additional data"""
        additional_data = {
            'sort_by_price': True,
            'limit': 20,
            'source': 'api_endpoint'
        }
        
        TokopediaSentryMonitor.set_scraping_context(
            keyword=self.test_keyword,
            page=self.test_page,
            additional_data=additional_data
        )
        
        # Verify additional data was included in context
        call_args = mock_set_context.call_args
        context_data = call_args[0][1]
        self.assertEqual(context_data['sort_by_price'], True)
        self.assertEqual(context_data['limit'], 20)
        self.assertEqual(context_data['source'], 'api_endpoint')
    
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.add_breadcrumb')
    def test_add_breadcrumb(self, mock_add_breadcrumb):
        """Test adding breadcrumb"""
        message = "Test breadcrumb message"
        category = "test.category"
        level = "info"
        data = {"key": "value"}
        
        TokopediaSentryMonitor.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data
        )
        
        mock_add_breadcrumb.assert_called_once_with(
            category=category,
            message=message,
            level=level,
            data=data
        )
    
    @patch('api.tokopedia.sentry_monitoring.capture_message')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_context')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_measurement')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_tag')
    def test_track_scraping_result_success(self, mock_set_tag, mock_set_measurement, 
                                          mock_set_context, mock_capture_message):
        """Test tracking successful scraping result"""
        result = {
            'products_count': 10,
            'success': True,
            'errors_count': 0
        }
        
        TokopediaSentryMonitor.track_scraping_result(result)
        
        # Verify measurements were set
        self.assertEqual(mock_set_measurement.call_count, 2)
        measurement_calls = [c[0] for c in mock_set_measurement.call_args_list]
        self.assertIn(('products_scraped', 10), measurement_calls)
        self.assertIn(('scraping_errors', 0), measurement_calls)
        
        # Verify success tag and context
        mock_set_tag.assert_called()
        mock_set_context.assert_called_once()
        
        # Verify success message was captured
        mock_capture_message.assert_called_once()
        captured_message = mock_capture_message.call_args[0][0]
        self.assertIn("10 products found", captured_message)
    
    @patch('api.tokopedia.sentry_monitoring.capture_message')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_context')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_measurement')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_tag')
    def test_track_scraping_result_failure(self, mock_set_tag, mock_set_measurement,
                                          mock_set_context, mock_capture_message):
        """Test tracking failed scraping result"""
        result = {
            'products_count': 0,
            'success': False,
            'errors_count': 1
        }
        
        TokopediaSentryMonitor.track_scraping_result(result)
        
        # Verify failure message was captured with warning level
        mock_capture_message.assert_called_once()
        call_args = mock_capture_message.call_args
        self.assertIn("failed", call_args[0][0].lower())
        self.assertEqual(call_args[1]['level'], 'warning')
    
    @patch('api.tokopedia.sentry_monitoring.capture_message')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_context')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_measurement')
    def test_track_database_operation_success(self, mock_set_measurement, 
                                             mock_set_context, mock_capture_message):
        """Test tracking successful database operation"""
        result = {
            'success': True,
            'inserted': 5,
            'updated': 3,
            'anomalies': []
        }
        
        TokopediaSentryMonitor.track_database_operation("save", result)
        
        # Verify measurements
        self.assertEqual(mock_set_measurement.call_count, 3)
        measurement_calls = [c[0] for c in mock_set_measurement.call_args_list]
        self.assertIn(('db_inserted', 5), measurement_calls)
        self.assertIn(('db_updated', 3), measurement_calls)
        self.assertIn(('anomalies_detected', 0), measurement_calls)
        
        # Verify context
        mock_set_context.assert_called_once()
        call_args = mock_set_context.call_args
        context_data = call_args[0][1]
        self.assertEqual(context_data['operation'], 'save')
        self.assertEqual(context_data['inserted'], 5)
        self.assertEqual(context_data['updated'], 3)
        
        # Verify success message
        mock_capture_message.assert_called_once()
        captured_message = mock_capture_message.call_args[0][0]
        self.assertIn("5 inserted, 3 updated", captured_message)
    
    @patch('api.tokopedia.sentry_monitoring.capture_message')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_context')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_measurement')
    def test_track_database_operation_with_anomalies(self, mock_set_measurement,
                                                    mock_set_context, mock_capture_message):
        """Test tracking database operation with detected anomalies"""
        result = {
            'success': True,
            'inserted': 2,
            'updated': 1,
            'anomalies': [
                {'name': 'Product 1', 'change_percent': 50},
                {'name': 'Product 2', 'change_percent': -25}
            ]
        }
        
        TokopediaSentryMonitor.track_database_operation("save_with_update", result)
        
        # Verify anomaly count in measurement
        measurement_calls = [c[0] for c in mock_set_measurement.call_args_list]
        self.assertIn(('anomalies_detected', 2), measurement_calls)
        
        # Verify context contains anomaly count
        call_args = mock_set_context.call_args
        context_data = call_args[0][1]
        self.assertEqual(context_data['anomalies'], 2)


class TokopediaTaskMonitorTests(TestCase):
    """Test TokopediaTaskMonitor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.task_id = "test_task_123"
        self.task_type = "test_scraping"
    
    @patch('api.tokopedia.sentry_monitoring.TokopediaSentryMonitor.add_breadcrumb')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_context')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_tag')
    def test_task_monitor_initialization(self, mock_set_tag, mock_set_context, 
                                        mock_add_breadcrumb):
        """Test TokopediaTaskMonitor initialization"""
        TokopediaTaskMonitor(task_id=self.task_id, task_type=self.task_type)
        
        # Verify tags were set
        self.assertEqual(mock_set_tag.call_count, 2)
        tag_calls = [c[0] for c in mock_set_tag.call_args_list]
        self.assertIn(('task_id', self.task_id), tag_calls)
        self.assertIn(('task_type', self.task_type), tag_calls)
        
        # Verify context was set
        mock_set_context.assert_called_once()
        call_args = mock_set_context.call_args
        context_data = call_args[0][1]
        self.assertEqual(context_data['task_id'], self.task_id)
        self.assertEqual(context_data['task_type'], self.task_type)
        
        # Verify breadcrumb was added
        mock_add_breadcrumb.assert_called_once()
        breadcrumb_call = mock_add_breadcrumb.call_args
        self.assertIn(self.task_id, breadcrumb_call[0][0])
    
    @patch('api.tokopedia.sentry_monitoring.TokopediaSentryMonitor.add_breadcrumb')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_measurement')
    def test_record_progress(self, mock_set_measurement, mock_add_breadcrumb):
        """Test recording task progress"""
        monitor = TokopediaTaskMonitor(task_id=self.task_id, task_type=self.task_type)
        mock_add_breadcrumb.reset_mock()
        
        monitor.record_progress(items_processed=5, total_items=10, message="Processing items")
        
        # Verify measurement was set
        mock_set_measurement.assert_called()
        call_args = mock_set_measurement.call_args
        self.assertEqual(call_args[0][0], "task_progress")
        self.assertEqual(call_args[0][1], 50.0)
        
        # Verify breadcrumb was added
        mock_add_breadcrumb.assert_called_once()
        breadcrumb_call = mock_add_breadcrumb.call_args
        self.assertIn("Processing items", breadcrumb_call[0][0])
    
    @patch('api.tokopedia.sentry_monitoring.capture_message')
    @patch('api.tokopedia.sentry_monitoring.TokopediaSentryMonitor.add_breadcrumb')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_measurement')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_tag')
    def test_task_complete_success(self, mock_set_tag, mock_set_measurement,
                                  mock_add_breadcrumb, mock_capture_message):
        """Test completing task successfully"""
        monitor = TokopediaTaskMonitor(task_id=self.task_id, task_type=self.task_type)
        mock_set_tag.reset_mock()
        mock_set_measurement.reset_mock()
        mock_add_breadcrumb.reset_mock()
        
        result_data = {'products_count': 10, 'duration': 5.5}
        monitor.complete(success=True, result_data=result_data)
        
        # Verify success tag
        mock_set_tag.assert_called_with("task_status", "success")
        
        # Verify duration measurement
        mock_set_measurement.assert_called_once()
        call_args = mock_set_measurement.call_args
        self.assertEqual(call_args[0][0], "task_duration")
        
        # Verify success breadcrumb
        breadcrumb_call = mock_add_breadcrumb.call_args
        self.assertIn("success", breadcrumb_call[0][0])
        
        # Verify success message captured with info level
        mock_capture_message.assert_called_once()
        capture_call = mock_capture_message.call_args
        self.assertIn(self.task_id, capture_call[0][0])
        self.assertEqual(capture_call[1]['level'], 'info')
    
    @patch('api.tokopedia.sentry_monitoring.capture_message')
    @patch('api.tokopedia.sentry_monitoring.TokopediaSentryMonitor.add_breadcrumb')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_measurement')
    @patch('api.tokopedia.sentry_monitoring.sentry_sdk.set_tag')
    def test_task_complete_failure(self, mock_set_tag, mock_set_measurement,
                                  mock_add_breadcrumb, mock_capture_message):
        """Test completing task with failure"""
        monitor = TokopediaTaskMonitor(task_id=self.task_id, task_type=self.task_type)
        mock_set_tag.reset_mock()
        
        monitor.complete(success=False)
        
        # Verify failure tag
        mock_set_tag.assert_called_with("task_status", "failed")
        
        # Verify failure message captured with warning level
        mock_capture_message.assert_called_once()
        capture_call = mock_capture_message.call_args
        self.assertEqual(capture_call[1]['level'], 'warning')


class MonitorTokopediaFunctionDecoratorTests(TestCase):
    """Test monitor_tokopedia_function decorator"""
    
    @patch('api.tokopedia.sentry_monitoring.TokopediaSentryMonitor.add_breadcrumb')
    @patch('api.tokopedia.sentry_monitoring.start_span')
    def test_decorator_success(self, mock_start_span, mock_add_breadcrumb):
        """Test decorator with successful function execution"""
        # Create mock span context manager
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)
        mock_start_span.return_value = mock_span
        
        @monitor_tokopedia_function("test_operation", "test_component")
        def test_func(value):
            return value * 2
        
        result = test_func(5)
        
        # Verify function executed successfully
        self.assertEqual(result, 10)
        
        # Verify breadcrumbs were added
        self.assertEqual(mock_add_breadcrumb.call_count, 2)
        breadcrumb_calls = [c[0][0] for c in mock_add_breadcrumb.call_args_list]
        self.assertTrue(any('Starting' in msg for msg in breadcrumb_calls))
        self.assertTrue(any('Completed' in msg for msg in breadcrumb_calls))
        
        # Verify span was used
        mock_start_span.assert_called_once()
        span_call = mock_start_span.call_args
        self.assertEqual(span_call[1]['op'], 'tokopedia.test_component')
    
    @patch('api.tokopedia.sentry_monitoring.capture_exception')
    @patch('api.tokopedia.sentry_monitoring.TokopediaSentryMonitor.add_breadcrumb')
    @patch('api.tokopedia.sentry_monitoring.start_span')
    def test_decorator_exception(self, mock_start_span, mock_add_breadcrumb, 
                                 mock_capture_exception):
        """Test decorator with function raising exception"""
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)
        mock_start_span.return_value = mock_span
        
        @monitor_tokopedia_function("failing_operation", "test_component")
        def test_func():
            raise ValueError("Test error")
        
        # Verify exception is re-raised
        with self.assertRaises(ValueError) as context:
            test_func()
        
        self.assertEqual(str(context.exception), "Test error")
        
        # Verify exception was captured
        mock_capture_exception.assert_called_once()
        
        # Verify error breadcrumb was added
        breadcrumb_calls = [c[0][0] for c in mock_add_breadcrumb.call_args_list]
        self.assertTrue(any('Error' in msg for msg in breadcrumb_calls))


class TrackTokopediaTransactionTests(TestCase):
    """Test track_tokopedia_transaction context manager"""
    
    @patch('api.tokopedia.sentry_monitoring.start_transaction')
    def test_transaction_context_manager(self, mock_start_transaction):
        """Test transaction context manager"""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value = mock_transaction
        
        transaction_name = "test_scraping_transaction"
        with track_tokopedia_transaction(transaction_name):
            # Context manager should work correctly
            pass
        
        # Verify transaction was created with correct parameters
        mock_start_transaction.assert_called_once_with(
            op="scraping.tokopedia",
            name=transaction_name
        )
        
        # Verify tags were set on transaction
        mock_transaction.set_tag.assert_any_call("vendor", "tokopedia")
        mock_transaction.set_tag.assert_any_call("transaction_type", "scraping")


class TokopediaSentryIntegrationTests(TestCase):
    """Integration tests for Sentry monitoring with API endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.scrape_url = reverse('tokopedia:scrape_products')
    
    def _create_mock_product(self, name: str, price: int, url: str):
        """Create a mock product"""
        mock_product = MagicMock()
        mock_product.name = name
        mock_product.price = price
        mock_product.url = url
        mock_product.location = "Jakarta"
        mock_product.unit = "pcs"
        return mock_product
    
    def _create_mock_result(self, success: bool = True, products: list = None):
        """Create a mock scraper result"""
        mock_result = MagicMock()
        mock_result.success = success
        mock_result.products = products or []
        mock_result.error_message = None if success else "Test error"
        mock_result.url = "https://www.tokopedia.com/test"
        return mock_result
    
    @patch('api.tokopedia.views.TokopediaSentryMonitor')
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_products_sentry_monitoring(self, mock_create_scraper, mock_sentry_monitor):
        """Test that scrape_products endpoint triggers Sentry monitoring"""
        # Setup mock scraper
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        
        products = [
            self._create_mock_product("Laptop", 5000000, "https://tokopedia.com/laptop"),
            self._create_mock_product("Mouse", 50000, "https://tokopedia.com/mouse")
        ]
        mock_scraper.scrape_products.return_value = self._create_mock_result(
            success=True,
            products=products
        )
        
        # Make request
        response = self.client.get(
            self.scrape_url,
            {'q': 'laptop'},
            HTTP_X_API_TOKEN='dev-token-12345'
        )
        
        # Verify response is successful
        self.assertEqual(response.status_code, 200)
        
        # Verify Sentry monitoring was called
        mock_sentry_monitor.set_scraping_context.assert_called_once()
        mock_sentry_monitor.add_breadcrumb.assert_called()
        mock_sentry_monitor.track_scraping_result.assert_called_once()
    
    @patch('api.tokopedia.views.TokopediaSentryMonitor')
    @patch('api.tokopedia.views.TokopediaTaskMonitor')
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_products_task_monitor(self, mock_create_scraper, mock_task_monitor_class,
                                         mock_sentry_monitor):
        """Test that scrape_products creates and completes task monitor"""
        # Setup mock scraper
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        mock_scraper.scrape_products.return_value = self._create_mock_result(success=True)
        
        # Setup mock task monitor
        mock_task_monitor = MagicMock()
        mock_task_monitor_class.return_value = mock_task_monitor
        
        # Make request
        response = self.client.get(
            self.scrape_url,
            {'q': 'laptop'},
            HTTP_X_API_TOKEN='dev-token-12345'
        )
        
        # Verify response is successful
        self.assertEqual(response.status_code, 200)
        
        # Verify task monitor was created
        mock_task_monitor_class.assert_called_once()
        
        # Verify task monitor methods were called
        mock_task_monitor.record_progress.assert_called()
        mock_task_monitor.complete.assert_called_once()
        # Verify it was called with success=True
        complete_call = mock_task_monitor.complete.call_args
        self.assertEqual(complete_call[1]['success'], True)
    
    @patch('api.tokopedia.views.TokopediaSentryMonitor')
    @patch('api.tokopedia.views.create_tokopedia_scraper')
    def test_scrape_products_error_monitoring(self, mock_create_scraper, mock_sentry_monitor):
        """Test that errors are properly monitored"""
        # Setup mock scraper to raise an exception
        mock_scraper = MagicMock()
        mock_create_scraper.return_value = mock_scraper
        mock_scraper.scrape_products.side_effect = RuntimeError("Scraping failed")
        
        # Make request
        response = self.client.get(
            self.scrape_url,
            {'q': 'laptop'},
            HTTP_X_API_TOKEN='dev-token-12345'
        )
        
        # Verify error response
        self.assertEqual(response.status_code, 500)
        
        # Verify error was tracked in Sentry
        mock_sentry_monitor.add_breadcrumb.assert_called()
        breadcrumb_calls = [c[0][0] for c in mock_sentry_monitor.add_breadcrumb.call_args_list]
        self.assertTrue(any('Fatal error' in msg or 'Error' in msg for msg in breadcrumb_calls))
