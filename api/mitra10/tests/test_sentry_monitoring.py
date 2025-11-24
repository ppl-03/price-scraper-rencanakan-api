"""
Unit tests for Mitra10 Sentry monitoring functionality.

Tests cover:
- Mitra10SentryMonitor constants and structure
- Monitor function decorator
- Transaction tracking
- Task monitoring basics
"""

import unittest
from unittest.mock import MagicMock, patch, call
import time


class TestMitra10SentryMonitorConstants(unittest.TestCase):
    """Test Mitra10SentryMonitor class constants."""
    
    def test_vendor_constant(self):
        """Test that vendor constant is correctly set."""
        from api.mitra10.sentry_monitoring import Mitra10SentryMonitor
        self.assertEqual(Mitra10SentryMonitor.VENDOR, "mitra10")
    
    def test_component_constants(self):
        """Test that component constants are defined."""
        from api.mitra10.sentry_monitoring import Mitra10SentryMonitor
        self.assertEqual(Mitra10SentryMonitor.COMPONENT_SCRAPER, "scraper")
        self.assertEqual(Mitra10SentryMonitor.COMPONENT_PARSER, "parser")
        self.assertEqual(Mitra10SentryMonitor.COMPONENT_HTTP_CLIENT, "http_client")
        self.assertEqual(Mitra10SentryMonitor.COMPONENT_LOCATION, "location_scraper")


class TestMitra10SentryMonitorMethods(unittest.TestCase):
    """Test Mitra10SentryMonitor methods with mocked sentry_sdk."""
    
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_set_scraping_context_basic(self, mock_sentry):
        """Test setting basic scraping context."""
        from api.mitra10.sentry_monitoring import Mitra10SentryMonitor
        
        keyword = "test_product"
        page = 1
        
        Mitra10SentryMonitor.set_scraping_context(keyword, page)
        
        # Verify set_context was called
        self.assertTrue(mock_sentry.set_context.called)
        call_args = mock_sentry.set_context.call_args
        
        self.assertEqual(call_args[0][0], "scraping_context")
        context = call_args[0][1]
        self.assertEqual(context['keyword'], keyword)
        self.assertEqual(context['page'], page)
        self.assertEqual(context['vendor'], "mitra10")
        self.assertIn('timestamp', context)
    
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_set_scraping_context_with_additional_data(self, mock_sentry):
        """Test setting scraping context with additional data."""
        from api.mitra10.sentry_monitoring import Mitra10SentryMonitor
        
        keyword = "cement"
        page = 0
        additional_data = {
            'sort_by_price': True,
            'source': 'api_endpoint',
            'ip_address': '127.0.0.1'
        }
        
        Mitra10SentryMonitor.set_scraping_context(keyword, page, additional_data)
        
        call_args = mock_sentry.set_context.call_args
        context = call_args[0][1]
        
        self.assertEqual(context['keyword'], keyword)
        self.assertEqual(context['sort_by_price'], True)
        self.assertEqual(context['source'], 'api_endpoint')
        self.assertEqual(context['ip_address'], '127.0.0.1')
    
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_add_breadcrumb_default_params(self, mock_sentry):
        """Test adding breadcrumb with default parameters."""
        from api.mitra10.sentry_monitoring import Mitra10SentryMonitor
        
        message = "Test breadcrumb"
        
        Mitra10SentryMonitor.add_breadcrumb(message)
        
        mock_sentry.add_breadcrumb.assert_called_once_with(
            category="scraping",
            message=message,
            level="info",
            data={}
        )
    
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_add_breadcrumb_custom_params(self, mock_sentry):
        """Test adding breadcrumb with custom parameters."""
        from api.mitra10.sentry_monitoring import Mitra10SentryMonitor
        
        message = "Custom breadcrumb"
        category = "mitra10.scraper"
        level = "warning"
        data = {'products_count': 10}
        
        Mitra10SentryMonitor.add_breadcrumb(message, category, level, data)
        
        mock_sentry.add_breadcrumb.assert_called_once_with(
            category=category,
            message=message,
            level=level,
            data=data
        )
    
    @patch('api.mitra10.sentry_monitoring.capture_message')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_track_scraping_result_success(self, mock_sentry, mock_capture):
        """Test tracking successful scraping result."""
        from api.mitra10.sentry_monitoring import Mitra10SentryMonitor
        
        result = {
            'products_count': 15,
            'success': True,
            'errors_count': 0
        }
        
        Mitra10SentryMonitor.track_scraping_result(result)
        
        # Verify tags were set
        tag_calls = mock_sentry.set_tag.call_args_list
        self.assertIn(call("scraping_success", "True"), tag_calls)
        
        # Verify measurements were set
        measurement_calls = mock_sentry.set_measurement.call_args_list
        self.assertIn(call("products_scraped", 15), measurement_calls)
        self.assertIn(call("scraping_errors", 0), measurement_calls)
        
        # Verify context was set
        self.assertTrue(mock_sentry.set_context.called)
        
        # Verify message was captured
        self.assertTrue(mock_capture.called)
    
    @patch('api.mitra10.sentry_monitoring.capture_message')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_track_scraping_result_failure(self, mock_sentry, mock_capture):
        """Test tracking failed scraping result."""
        from api.mitra10.sentry_monitoring import Mitra10SentryMonitor
        
        result = {
            'products_count': 0,
            'success': False,
            'errors_count': 3
        }
        
        Mitra10SentryMonitor.track_scraping_result(result)
        
        # Verify failure message was captured
        self.assertTrue(mock_capture.called)
        message_call = mock_capture.call_args
        self.assertIn("Mitra10 scraping failed", message_call[0][0])
        self.assertEqual(message_call[1]['level'], "warning")


class TestMonitorMitra10FunctionDecorator(unittest.TestCase):
    """Test monitor_mitra10_function decorator."""
    
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    @patch('api.mitra10.sentry_monitoring.start_span')
    def test_decorator_successful_execution(self, mock_start_span, mock_sentry):
        """Test decorator tracks successful function execution."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        # Mock span context manager
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = MagicMock(return_value=False)
        
        @monitor_mitra10_function("test_operation", "scraper")
        def test_function(x, y):
            return x + y
        
        result = test_function(2, 3)
        
        self.assertEqual(result, 5)
        
        # Verify span was started
        self.assertTrue(mock_start_span.called)
        
        # Verify breadcrumbs were added
        self.assertTrue(mock_sentry.add_breadcrumb.called)
    
    @patch('api.mitra10.sentry_monitoring.capture_exception')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    @patch('api.mitra10.sentry_monitoring.start_span')
    def test_decorator_handles_exception(self, mock_start_span, mock_sentry, mock_capture_exc):
        """Test decorator properly handles and re-raises exceptions."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        # Mock span context manager
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = MagicMock(return_value=False)
        
        @monitor_mitra10_function("failing_operation", "parser")
        def failing_function():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            failing_function()
        
        # Verify error context was set
        self.assertTrue(mock_sentry.set_context.called)
        
        # Verify exception was captured
        self.assertTrue(mock_capture_exc.called)
    
    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves original function metadata."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        @monitor_mitra10_function("operation", "scraper")
        def documented_function():
            """This is a docstring."""
            pass
        
        self.assertEqual(documented_function.__name__, "documented_function")
        self.assertEqual(documented_function.__doc__, "This is a docstring.")
    
    @patch('api.mitra10.sentry_monitoring.start_span')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    @patch('api.mitra10.sentry_monitoring.time')
    def test_decorator_span_tags(self, mock_time, mock_sentry, mock_start_span):
        """Test decorator sets correct span tags."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        
        @monitor_mitra10_function("test_operation", "test_component")
        def sample_function():
            return "success"
        
        sample_function()
        
        # Verify span.set_tag was called with correct values
        span_tag_calls = mock_span.set_tag.call_args_list
        self.assertIn(call("vendor", "mitra10"), span_tag_calls)
        self.assertIn(call("component", "test_component"), span_tag_calls)
        self.assertIn(call("operation", "test_operation"), span_tag_calls)
    
    @patch('api.mitra10.sentry_monitoring.start_span')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    @patch('api.mitra10.sentry_monitoring.time')
    def test_decorator_execution_time_tracking(self, mock_time, mock_sentry, mock_start_span):
        """Test decorator tracks execution time correctly."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        # Mock time to control execution duration
        mock_time.time.side_effect = [100.0, 105.5]  # 5.5 second execution
        
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        
        @monitor_mitra10_function("timed_op", "timer")
        def timed_function():
            return "done"
        
        timed_function()
        
        # Verify execution time was recorded
        span_data_calls = mock_span.set_data.call_args_list
        self.assertIn(call("execution_time", 5.5), span_data_calls)
        self.assertIn(call("status", "success"), span_data_calls)
    
    @patch('api.mitra10.sentry_monitoring.start_span')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_decorator_success_breadcrumbs(self, mock_sentry, mock_start_span):
        """Test decorator adds breadcrumbs on successful execution."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        
        @monitor_mitra10_function("breadcrumb_op", "breadcrumb_comp")
        def breadcrumb_function():
            return "result"
        
        result = breadcrumb_function()
        
        # Verify breadcrumb was added
        self.assertTrue(mock_sentry.add_breadcrumb.called)
        breadcrumb_calls = mock_sentry.add_breadcrumb.call_args_list
        
        # Check that at least one breadcrumb contains the function info
        found_start_breadcrumb = False
        for breadcrumb_call in breadcrumb_calls:
            if 'message' in breadcrumb_call[1]:
                message = breadcrumb_call[1]['message']
                if 'Starting' in message and 'breadcrumb_function' in message:
                    found_start_breadcrumb = True
                    break
        
        self.assertTrue(found_start_breadcrumb)
    
    @patch('api.mitra10.sentry_monitoring.capture_exception')
    @patch('api.mitra10.sentry_monitoring.start_span')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    @patch('api.mitra10.sentry_monitoring.time')
    def test_decorator_error_handling_details(self, mock_time, mock_sentry, mock_start_span, mock_capture):
        """Test decorator sets error details correctly."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        mock_time.time.side_effect = [100.0, 102.0]  # 2 second execution
        
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        
        test_error = ValueError("Test error message")
        
        @monitor_mitra10_function("error_op", "error_comp")
        def error_function():
            raise test_error
        
        with self.assertRaises(ValueError):
            error_function()
        
        # Verify span error data
        span_data_calls = mock_span.set_data.call_args_list
        self.assertIn(call("status", "error"), span_data_calls)
        self.assertIn(call("error_type", "ValueError"), span_data_calls)
        self.assertIn(call("execution_time", 2.0), span_data_calls)
        
        # Verify error context was set
        self.assertTrue(mock_sentry.set_context.called)
        context_calls = mock_sentry.set_context.call_args_list
        
        # Find the error_context call
        found_error_context = False
        for context_call in context_calls:
            if context_call[0][0] == "error_context":
                error_context = context_call[0][1]
                self.assertEqual(error_context["function"], "error_function")
                self.assertEqual(error_context["operation"], "error_op")
                self.assertEqual(error_context["component"], "error_comp")
                self.assertEqual(error_context["error_message"], "Test error message")
                self.assertEqual(error_context["error_type"], "ValueError")
                found_error_context = True
                break
        
        self.assertTrue(found_error_context)
        
        # Verify exception was captured
        mock_capture.assert_called_once_with(test_error)
    
    @patch('api.mitra10.sentry_monitoring.start_span')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_decorator_with_function_args(self, mock_sentry, mock_start_span):
        """Test decorator works with functions that have arguments."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        
        @monitor_mitra10_function("args_op", "args_comp")
        def function_with_args(a, b, c=None):
            return a + b + (c or 0)
        
        result = function_with_args(1, 2, c=3)
        
        self.assertEqual(result, 6)
        
        # Verify monitoring was performed
        self.assertTrue(mock_start_span.called)
        self.assertTrue(mock_span.set_tag.called)
    
    @patch('api.mitra10.sentry_monitoring.start_span')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    @patch('api.mitra10.sentry_monitoring.time')
    def test_decorator_span_description(self, mock_time, mock_sentry, mock_start_span):
        """Test decorator creates span with correct description."""
        from api.mitra10.sentry_monitoring import monitor_mitra10_function
        
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__.return_value = mock_span
        
        @monitor_mitra10_function("desc_op", "desc_comp")
        def described_function():
            return True
        
        described_function()
        
        # Verify start_span was called with correct op and description
        mock_start_span.assert_called_once_with(
            op="mitra10.desc_op",
            description="described_function"
        )


class TestTrackMitra10Transaction(unittest.TestCase):
    """Test track_mitra10_transaction context manager."""
    
    @patch('api.mitra10.sentry_monitoring.start_transaction')
    def test_transaction_creation(self, mock_start_transaction):
        """Test transaction is created with correct parameters."""
        from api.mitra10.sentry_monitoring import track_mitra10_transaction
        
        # Mock transaction
        mock_transaction = MagicMock()
        mock_start_transaction.return_value = mock_transaction
        
        transaction = track_mitra10_transaction("test_transaction")
        
        mock_start_transaction.assert_called_once_with(
            op="scraping.mitra10",
            name="test_transaction"
        )
        
        # Verify transaction returned
        self.assertEqual(transaction, mock_transaction)


class TestMitra10TaskMonitor(unittest.TestCase):
    """Test Mitra10TaskMonitor class."""
    
    @patch('api.mitra10.sentry_monitoring.time')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_task_initialization(self, mock_sentry, mock_time):
        """Test task monitor initialization."""
        from api.mitra10.sentry_monitoring import Mitra10TaskMonitor
        
        mock_time.time.return_value = 100.0
        
        task_id = "test_task_123"
        task_type = "scraping"
        
        monitor = Mitra10TaskMonitor(task_id, task_type)
        
        self.assertEqual(monitor.task_id, task_id)
        self.assertEqual(monitor.task_type, task_type)
        self.assertEqual(monitor.start_time, 100.0)
        
        # Verify tags were set
        self.assertTrue(mock_sentry.set_tag.called)
        
        # Verify context was set
        self.assertTrue(mock_sentry.set_context.called)
        
        # Verify breadcrumb was added
        self.assertTrue(mock_sentry.add_breadcrumb.called)
    
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_record_progress(self, mock_sentry):
        """Test recording task progress."""
        from api.mitra10.sentry_monitoring import Mitra10TaskMonitor
        
        with patch('api.mitra10.sentry_monitoring.time') as mock_time:
            mock_time.time.return_value = 100.0
            monitor = Mitra10TaskMonitor("task_1", "test")
        
        monitor.record_progress(5, 10, "Half complete")
        
        # Verify measurement was set
        self.assertTrue(mock_sentry.set_measurement.called)
        
        # Verify breadcrumb was added
        self.assertTrue(mock_sentry.add_breadcrumb.called)
    
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_record_progress_zero_total(self, mock_sentry):
        """Test recording progress with zero total items."""
        from api.mitra10.sentry_monitoring import Mitra10TaskMonitor
        
        with patch('api.mitra10.sentry_monitoring.time') as mock_time:
            mock_time.time.return_value = 100.0
            monitor = Mitra10TaskMonitor("task_2", "test")
        
        monitor.record_progress(0, 0)
        
        # Should set 0% progress
        self.assertTrue(mock_sentry.set_measurement.called)
    
    @patch('api.mitra10.sentry_monitoring.capture_message')
    @patch('api.mitra10.sentry_monitoring.time')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_complete_success(self, mock_sentry, mock_time, mock_capture):
        """Test completing task successfully."""
        from api.mitra10.sentry_monitoring import Mitra10TaskMonitor
        
        mock_time.time.side_effect = [100.0, 200.0]
        
        monitor = Mitra10TaskMonitor("task_3", "test")
        
        result_data = {'items_processed': 100}
        monitor.complete(success=True, result_data=result_data)
        
        # Verify duration measurement
        self.assertTrue(mock_sentry.set_measurement.called)
        
        # Verify completion message
        self.assertTrue(mock_capture.called)
    
    @patch('api.mitra10.sentry_monitoring.capture_message')
    @patch('api.mitra10.sentry_monitoring.time')
    @patch('api.mitra10.sentry_monitoring.sentry_sdk')
    def test_complete_failure(self, mock_sentry, mock_time, mock_capture):
        """Test completing task with failure."""
        from api.mitra10.sentry_monitoring import Mitra10TaskMonitor
        
        mock_time.time.side_effect = [100.0, 200.0]
        
        monitor = Mitra10TaskMonitor("task_4", "test")
        
        monitor.complete(success=False)
        
        # Verify completion message
        self.assertTrue(mock_capture.called)


if __name__ == '__main__':
    unittest.main()
