import unittest
from unittest.mock import Mock, patch, MagicMock, call
import time
from django.test import TestCase

from ..sentry_monitoring import (
    DepoBangunanSentryMonitor,
    monitor_depobangunan_function,
    track_depobangunan_transaction,
    DepoBangunanTaskMonitor
)


class TestDepoBangunanSentryMonitor(TestCase):
    """Test cases for DepoBangunanSentryMonitor class"""
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    def test_set_scraping_context_basic(self, mock_sentry):
        """Test setting basic scraping context"""
        keyword = "test_product"
        page = 1
        
        DepoBangunanSentryMonitor.set_scraping_context(keyword, page)
        
        # Verify context was set
        mock_sentry.set_context.assert_called_once()
        context_name, context_data = mock_sentry.set_context.call_args[0]
        
        self.assertEqual(context_name, "scraping_context")
        self.assertEqual(context_data["keyword"], keyword)
        self.assertEqual(context_data["page"], page)
        self.assertEqual(context_data["vendor"], "depobangunan")
        self.assertIn("timestamp", context_data)
        
        # Verify tags were set
        tag_calls = mock_sentry.set_tag.call_args_list
        self.assertEqual(len(tag_calls), 3)
        
        # Check vendor tag
        self.assertEqual(tag_calls[0][0], ("vendor", "depobangunan"))
        # Check keyword tag
        self.assertEqual(tag_calls[1][0], ("search_keyword", keyword))
        # Check page tag
        self.assertEqual(tag_calls[2][0], ("page_number", str(page)))
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    def test_set_scraping_context_with_additional_data(self, mock_sentry):
        """Test setting scraping context with additional data"""
        keyword = "test_product"
        page = 2
        additional_data = {
            'sort_by_price': True,
            'source': 'api_endpoint',
            'ip_address': '127.0.0.1'
        }
        
        DepoBangunanSentryMonitor.set_scraping_context(keyword, page, additional_data)
        
        # Verify context includes additional data
        context_name, context_data = mock_sentry.set_context.call_args[0]
        
        self.assertEqual(context_data["keyword"], keyword)
        self.assertEqual(context_data["page"], page)
        self.assertEqual(context_data["sort_by_price"], True)
        self.assertEqual(context_data["source"], "api_endpoint")
        self.assertEqual(context_data["ip_address"], "127.0.0.1")
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    def test_add_breadcrumb_basic(self, mock_sentry):
        """Test adding a basic breadcrumb"""
        message = "Test breadcrumb"
        
        DepoBangunanSentryMonitor.add_breadcrumb(message)
        
        mock_sentry.add_breadcrumb.assert_called_once()
        call_kwargs = mock_sentry.add_breadcrumb.call_args[1]
        
        self.assertEqual(call_kwargs["message"], message)
        self.assertEqual(call_kwargs["category"], "scraping")
        self.assertEqual(call_kwargs["level"], "info")
        self.assertEqual(call_kwargs["data"], {})
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    def test_add_breadcrumb_with_data(self, mock_sentry):
        """Test adding breadcrumb with custom data"""
        message = "Product scraping started"
        category = "depobangunan.scraper"
        level = "info"
        data = {"keyword": "cement", "page": 0}
        
        DepoBangunanSentryMonitor.add_breadcrumb(message, category, level, data)
        
        call_kwargs = mock_sentry.add_breadcrumb.call_args[1]
        
        self.assertEqual(call_kwargs["message"], message)
        self.assertEqual(call_kwargs["category"], category)
        self.assertEqual(call_kwargs["level"], level)
        self.assertEqual(call_kwargs["data"], data)
    
    @patch('api.depobangunan.sentry_monitoring.capture_message')
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    def test_track_scraping_result_success(self, mock_sentry, mock_capture_message):
        """Test tracking successful scraping result"""
        result = {
            'products_count': 10,
            'success': True,
            'errors_count': 0
        }
        
        DepoBangunanSentryMonitor.track_scraping_result(result)
        
        # Verify tags
        tag_calls = mock_sentry.set_tag.call_args_list
        self.assertIn(call("scraping_success", "True"), tag_calls)
        
        # Verify measurements
        measurement_calls = mock_sentry.set_measurement.call_args_list
        self.assertIn(call("products_scraped", 10), measurement_calls)
        self.assertIn(call("scraping_errors", 0), measurement_calls)
        
        # Verify context
        context_name, context_data = mock_sentry.set_context.call_args[0]
        self.assertEqual(context_name, "scraping_result")
        self.assertEqual(context_data["products_found"], 10)
        self.assertEqual(context_data["success"], True)
        self.assertEqual(context_data["errors"], 0)
        
        # Verify capture_message was called for success
        mock_capture_message.assert_called_once()
        message, level = mock_capture_message.call_args[0][0], mock_capture_message.call_args[1]['level']
        self.assertIn("DepoBangunan scraping completed", message)
        self.assertIn("10 products found", message)
        self.assertEqual(level, "info")
    
    @patch('api.depobangunan.sentry_monitoring.capture_message')
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    def test_track_scraping_result_failure(self, mock_sentry, mock_capture_message):
        """Test tracking failed scraping result"""
        result = {
            'products_count': 0,
            'success': False,
            'errors_count': 3
        }
        
        DepoBangunanSentryMonitor.track_scraping_result(result)
        
        # Verify tags
        tag_calls = mock_sentry.set_tag.call_args_list
        self.assertIn(call("scraping_success", "False"), tag_calls)
        
        # Verify measurements
        measurement_calls = mock_sentry.set_measurement.call_args_list
        self.assertIn(call("products_scraped", 0), measurement_calls)
        self.assertIn(call("scraping_errors", 3), measurement_calls)
        
        # Verify capture_message was called for failure
        mock_capture_message.assert_called_once()
        message, level = mock_capture_message.call_args[0][0], mock_capture_message.call_args[1]['level']
        self.assertIn("DepoBangunan scraping failed", message)
        self.assertIn("3 errors", message)
        self.assertEqual(level, "warning")


class TestMonitorDepoBangunanFunction(TestCase):
    """Test cases for monitor_depobangunan_function decorator"""
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    @patch('api.depobangunan.sentry_monitoring.start_span')
    def test_decorator_success(self, mock_start_span, mock_sentry):
        """Test decorator on successful function execution"""
        # Setup mock span
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = Mock(return_value=False)
        
        # Create decorated function
        @monitor_depobangunan_function("test_operation", "scraper")
        def test_function(x, y):
            return x + y
        
        # Execute function
        result = test_function(2, 3)
        
        # Verify result
        self.assertEqual(result, 5)
        
        # Verify span was started
        mock_start_span.assert_called_once_with(
            op="depobangunan.scraper",
            description="test_operation"
        )
        
        # Verify span tags
        span_tag_calls = mock_span.set_tag.call_args_list
        self.assertIn(call("vendor", "depobangunan"), span_tag_calls)
        self.assertIn(call("component", "scraper"), span_tag_calls)
        self.assertIn(call("operation", "test_operation"), span_tag_calls)
        
        # Verify span data
        span_data_calls = mock_span.set_data.call_args_list
        # Check that execution_time was set
        execution_time_call = [c for c in span_data_calls if c[0][0] == "execution_time"]
        self.assertTrue(len(execution_time_call) > 0)
        # Check that status was set to success
        status_call = [c for c in span_data_calls if c[0][0] == "status"]
        self.assertTrue(len(status_call) > 0)
        self.assertEqual(status_call[0][0][1], "success")
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    @patch('api.depobangunan.sentry_monitoring.start_span')
    @patch('api.depobangunan.sentry_monitoring.capture_exception')
    def test_decorator_exception(self, mock_capture_exception, mock_start_span, mock_sentry):
        """Test decorator on function that raises exception"""
        # Setup mock span
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = Mock(return_value=False)
        
        # Create decorated function that raises exception
        @monitor_depobangunan_function("failing_operation", "parser")
        def failing_function():
            raise ValueError("Test error")
        
        # Execute and verify exception is raised
        with self.assertRaises(ValueError):
            failing_function()
        
        # Verify span data for error
        span_data_calls = mock_span.set_data.call_args_list
        status_call = [c for c in span_data_calls if c[0][0] == "status"]
        self.assertTrue(len(status_call) > 0)
        self.assertEqual(status_call[0][0][1], "error")
        
        error_type_call = [c for c in span_data_calls if c[0][0] == "error_type"]
        self.assertTrue(len(error_type_call) > 0)
        self.assertEqual(error_type_call[0][0][1], "ValueError")
        
        # Verify exception was captured
        mock_capture_exception.assert_called_once()
        captured_exception = mock_capture_exception.call_args[0][0]
        self.assertIsInstance(captured_exception, ValueError)
        self.assertEqual(str(captured_exception), "Test error")


class TestTrackDepoBangunanTransaction(TestCase):
    """Test cases for track_depobangunan_transaction context manager"""
    
    @patch('api.depobangunan.sentry_monitoring.start_transaction')
    def test_transaction_creation(self, mock_start_transaction):
        """Test transaction is created with correct parameters"""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value = mock_transaction
        
        transaction = track_depobangunan_transaction("test_transaction")
        
        # Verify transaction was created
        mock_start_transaction.assert_called_once_with(
            op="scraping.depobangunan",
            name="test_transaction"
        )
        
        # Verify tags were set
        tag_calls = mock_transaction.set_tag.call_args_list
        self.assertIn(call("vendor", "depobangunan"), tag_calls)
        self.assertIn(call("transaction_type", "scraping"), tag_calls)
    
    @patch('api.depobangunan.sentry_monitoring.start_transaction')
    def test_transaction_as_context_manager(self, mock_start_transaction):
        """Test transaction can be used as context manager"""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value = mock_transaction
        
        with track_depobangunan_transaction("test_transaction") as transaction:
            self.assertIsNotNone(transaction)
        
        mock_start_transaction.assert_called_once()


class TestDepoBangunanTaskMonitor(TestCase):
    """Test cases for DepoBangunanTaskMonitor class"""
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    def test_task_monitor_initialization(self, mock_sentry):
        """Test task monitor initialization"""
        task_id = "test_task_123"
        task_type = "scraping"
        
        monitor = DepoBangunanTaskMonitor(task_id, task_type)
        
        # Verify attributes
        self.assertEqual(monitor.task_id, task_id)
        self.assertEqual(monitor.task_type, task_type)
        self.assertIsNotNone(monitor.start_time)
        
        # Verify tags were set
        tag_calls = mock_sentry.set_tag.call_args_list
        self.assertIn(call("task_id", task_id), tag_calls)
        self.assertIn(call("task_type", task_type), tag_calls)
        
        # Verify context was set
        context_name, context_data = mock_sentry.set_context.call_args[0]
        self.assertEqual(context_name, "task_context")
        self.assertEqual(context_data["task_id"], task_id)
        self.assertEqual(context_data["task_type"], task_type)
        self.assertEqual(context_data["vendor"], "depobangunan")
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    def test_record_progress(self, mock_sentry):
        """Test recording task progress"""
        monitor = DepoBangunanTaskMonitor("task_123", "scraping")
        
        mock_sentry.reset_mock()  # Reset to ignore initialization calls
        
        # Record progress
        monitor.record_progress(5, 10, "Half way done")
        
        # Verify measurement was set
        mock_sentry.set_measurement.assert_called_once_with("task_progress", 50.0)
        
        # Verify breadcrumb was added
        mock_sentry.add_breadcrumb.assert_called_once()
        breadcrumb_kwargs = mock_sentry.add_breadcrumb.call_args[1]
        self.assertEqual(breadcrumb_kwargs["message"], "Half way done")
        self.assertEqual(breadcrumb_kwargs["category"], "task.progress")
        self.assertEqual(breadcrumb_kwargs["data"]["items_processed"], 5)
        self.assertEqual(breadcrumb_kwargs["data"]["total_items"], 10)
        self.assertEqual(breadcrumb_kwargs["data"]["progress_percent"], 50.0)
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    @patch('api.depobangunan.sentry_monitoring.capture_message')
    @patch('api.depobangunan.sentry_monitoring.time.time')
    def test_complete_success(self, mock_time, mock_capture_message, mock_sentry):
        """Test completing task successfully"""
        # Mock time to control duration
        mock_time.side_effect = [1000.0, 1005.0]  # 5 seconds duration
        
        monitor = DepoBangunanTaskMonitor("task_123", "scraping")
        
        mock_sentry.reset_mock()  # Reset to ignore initialization calls
        
        result_data = {"products": 10, "errors": 0}
        monitor.complete(success=True, result_data=result_data)
        
        # Verify measurement was set
        mock_sentry.set_measurement.assert_called_once_with("task_duration", 5.0)
        
        # Verify tag was set
        mock_sentry.set_tag.assert_called_once_with("task_status", "success")
        
        # Verify breadcrumb
        mock_sentry.add_breadcrumb.assert_called_once()
        breadcrumb_kwargs = mock_sentry.add_breadcrumb.call_args[1]
        self.assertIn("Task completed", breadcrumb_kwargs["message"])
        self.assertIn("success", breadcrumb_kwargs["message"])
        self.assertEqual(breadcrumb_kwargs["level"], "info")
        
        # Verify capture_message
        mock_capture_message.assert_called_once()
        message, level = mock_capture_message.call_args[0][0], mock_capture_message.call_args[1]['level']
        self.assertIn("DepoBangunan task", message)
        self.assertIn("task_123", message)
        self.assertIn("completed", message)
        self.assertEqual(level, "info")
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    @patch('api.depobangunan.sentry_monitoring.capture_message')
    @patch('api.depobangunan.sentry_monitoring.time.time')
    def test_complete_failure(self, mock_time, mock_capture_message, mock_sentry):
        """Test completing task with failure"""
        # Mock time to control duration
        mock_time.side_effect = [1000.0, 1003.0]  # 3 seconds duration
        
        monitor = DepoBangunanTaskMonitor("task_456", "database_save")
        
        mock_sentry.reset_mock()  # Reset to ignore initialization calls
        
        monitor.complete(success=False)
        
        # Verify tag was set to failed
        mock_sentry.set_tag.assert_called_once_with("task_status", "failed")
        
        # Verify breadcrumb level is error
        breadcrumb_kwargs = mock_sentry.add_breadcrumb.call_args[1]
        self.assertEqual(breadcrumb_kwargs["level"], "error")
        self.assertIn("failed", breadcrumb_kwargs["message"])
        
        # Verify capture_message level is warning
        message, level = mock_capture_message.call_args[0][0], mock_capture_message.call_args[1]['level']
        self.assertEqual(level, "warning")


class TestSentryMonitoringIntegration(TestCase):
    """Integration tests for Sentry monitoring components"""
    
    @patch('api.depobangunan.sentry_monitoring.sentry_sdk')
    @patch('api.depobangunan.sentry_monitoring.start_span')
    @patch('api.depobangunan.sentry_monitoring.start_transaction')
    def test_full_scraping_workflow(self, mock_start_transaction, mock_start_span, mock_sentry):
        """Test complete scraping workflow with Sentry monitoring"""
        # Setup mocks
        mock_transaction = MagicMock()
        mock_start_transaction.return_value = mock_transaction
        
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = Mock(return_value=False)
        
        # Simulate scraping workflow
        with track_depobangunan_transaction("test_scraping"):
            # Set context
            DepoBangunanSentryMonitor.set_scraping_context(
                keyword="cement",
                page=0,
                additional_data={"sort_by_price": True}
            )
            
            # Create task monitor
            task = DepoBangunanTaskMonitor("scrape_001", "product_scraping")
            
            # Add breadcrumbs
            DepoBangunanSentryMonitor.add_breadcrumb(
                "Starting product scraping",
                category="depobangunan.scraper",
                level="info"
            )
            
            # Simulate decorated function
            @monitor_depobangunan_function("scrape_products", "scraper")
            def scrape_products():
                return {"products": [{"name": "Product1"}, {"name": "Product2"}]}
            
            result = scrape_products()
            
            # Record progress
            task.record_progress(1, 2, "Scraping done")
            
            # Track result
            DepoBangunanSentryMonitor.track_scraping_result({
                'products_count': 2,
                'success': True,
                'errors_count': 0
            })
            
            # Complete task
            task.record_progress(2, 2, "Complete")
            task.complete(success=True, result_data={'products': 2})
        
        # Verify transaction was created
        mock_start_transaction.assert_called_once()
        
        # Verify context was set
        self.assertTrue(mock_sentry.set_context.called)
        
        # Verify breadcrumbs were added
        self.assertTrue(mock_sentry.add_breadcrumb.called)
        
        # Verify function was monitored
        mock_start_span.assert_called_once()
        
        # Verify result tracking
        self.assertTrue(mock_sentry.set_measurement.called)


class TestSentryMonitoringConstants(TestCase):
    """Test Sentry monitoring constants and configuration"""
    
    def test_vendor_constant(self):
        """Test vendor constant is correct"""
        self.assertEqual(DepoBangunanSentryMonitor.VENDOR, "depobangunan")
    
    def test_component_constants(self):
        """Test component constants are defined"""
        self.assertEqual(DepoBangunanSentryMonitor.COMPONENT_SCRAPER, "scraper")
        self.assertEqual(DepoBangunanSentryMonitor.COMPONENT_PARSER, "parser")
        self.assertEqual(DepoBangunanSentryMonitor.COMPONENT_HTTP_CLIENT, "http_client")
        self.assertEqual(DepoBangunanSentryMonitor.COMPONENT_LOCATION, "location_scraper")


if __name__ == '__main__':
    unittest.main()
