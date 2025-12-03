import pytest
from unittest.mock import Mock, patch, MagicMock, call, ANY
from django.test import TestCase, RequestFactory, Client
from django.http import JsonResponse
import time

from api.juragan_material.sentry_monitoring import (
    JuraganMaterialSentryMonitor,
    track_juragan_material_transaction,
    JuraganMaterialTaskMonitor,
    monitor_juragan_material_function
)
from api.juragan_material.views import (
    scrape_products,
    scrape_and_save_products,
    scrape_popularity,
    _save_products_to_database
)
from api.interfaces import ScrapingResult, Product


class TestJuraganMaterialSentryMonitor(TestCase):
    """Test the JuraganMaterialSentryMonitor class."""
    
    def test_vendor_constant(self):
        """Test that vendor constant is set correctly."""
        self.assertEqual(JuraganMaterialSentryMonitor.VENDOR, "juragan_material")
    
    def test_component_constants(self):
        """Test that component constants are defined."""
        self.assertEqual(JuraganMaterialSentryMonitor.COMPONENT_SCRAPER, "scraper")
        self.assertEqual(JuraganMaterialSentryMonitor.COMPONENT_PARSER, "parser")
        self.assertEqual(JuraganMaterialSentryMonitor.COMPONENT_HTTP_CLIENT, "http_client")
        self.assertEqual(JuraganMaterialSentryMonitor.COMPONENT_DATABASE, "database")
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_set_scraping_context(self, mock_sentry):
        """Test setting scraping context."""
        keyword = "test_keyword"
        page = 1
        additional_data = {"sort_by_price": True}
        
        JuraganMaterialSentryMonitor.set_scraping_context(
            keyword=keyword,
            page=page,
            additional_data=additional_data
        )
        
        # Verify set_context was called
        self.assertTrue(mock_sentry.set_context.called)
        context_call = mock_sentry.set_context.call_args
        self.assertEqual(context_call[0][0], "scraping_context")
        context_data = context_call[0][1]
        self.assertEqual(context_data["keyword"], keyword)
        self.assertEqual(context_data["page"], page)
        self.assertEqual(context_data["vendor"], "juragan_material")
        self.assertEqual(context_data["sort_by_price"], True)
        
        # Verify tags were set
        tag_calls = mock_sentry.set_tag.call_args_list
        self.assertIn(call("vendor", "juragan_material"), tag_calls)
        self.assertIn(call("search_keyword", keyword), tag_calls)
        self.assertIn(call("page_number", str(page)), tag_calls)
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_add_breadcrumb(self, mock_sentry):
        """Test adding breadcrumbs."""
        message = "Test breadcrumb"
        category = "test_category"
        level = "info"
        data = {"test": "data"}
        
        JuraganMaterialSentryMonitor.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data
        )
        
        mock_sentry.add_breadcrumb.assert_called_once_with(
            category=category,
            message=message,
            level=level,
            data=data
        )
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    @patch('api.juragan_material.sentry_monitoring.capture_message')
    def test_track_scraping_result_success(self, mock_capture, mock_sentry):
        """Test tracking successful scraping result."""
        result = {
            'products_count': 10,
            'success': True,
            'errors_count': 0
        }
        
        JuraganMaterialSentryMonitor.track_scraping_result(result)
        
        # Verify measurements
        measurement_calls = mock_sentry.set_measurement.call_args_list
        self.assertIn(call("products_scraped", 10), measurement_calls)
        self.assertIn(call("scraping_errors", 0), measurement_calls)
        
        # Verify tag
        self.assertIn(call("scraping_success", "True"), mock_sentry.set_tag.call_args_list)
        
        # Verify context
        self.assertTrue(mock_sentry.set_context.called)
        
        # Verify message capture
        self.assertTrue(mock_capture.called)
        message_call = mock_capture.call_args
        self.assertIn("10 products", message_call[0][0])
        self.assertEqual(message_call[1]["level"], "info")
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    @patch('api.juragan_material.sentry_monitoring.capture_message')
    def test_track_scraping_result_failure(self, mock_capture, mock_sentry):
        """Test tracking failed scraping result."""
        result = {
            'products_count': 0,
            'success': False,
            'errors_count': 3
        }
        
        JuraganMaterialSentryMonitor.track_scraping_result(result)
        
        # Verify tag
        self.assertIn(call("scraping_success", "False"), mock_sentry.set_tag.call_args_list)
        
        # Verify message capture
        message_call = mock_capture.call_args
        self.assertIn("failed", message_call[0][0])
        self.assertEqual(message_call[1]["level"], "warning")
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_track_database_operation(self, mock_sentry):
        """Test tracking database operations."""
        operation = "save_products"
        result = {
            'success': True,
            'inserted': 5,
            'updated': 3,
            'categorized': 4
        }
        
        JuraganMaterialSentryMonitor.track_database_operation(operation, result)
        
        # Verify measurements
        measurement_calls = mock_sentry.set_measurement.call_args_list
        self.assertIn(call("db_inserted", 5), measurement_calls)
        self.assertIn(call("db_updated", 3), measurement_calls)
        self.assertIn(call("db_categorized", 4), measurement_calls)
        
        # Verify context
        self.assertTrue(mock_sentry.set_context.called)
        context_call = mock_sentry.set_context.call_args
        self.assertEqual(context_call[0][0], "database_operation")
        self.assertEqual(context_call[0][1]["operation"], operation)
        self.assertEqual(context_call[0][1]["inserted"], 5)


class TestJuraganMaterialTaskMonitor(TestCase):
    """Test the JuraganMaterialTaskMonitor class."""
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_task_monitor_initialization(self, mock_sentry):
        """Test task monitor initialization."""
        task_id = "test_task_123"
        task_type = "scraping"
        
        JuraganMaterialTaskMonitor(task_id=task_id, task_type=task_type)
        
        # Verify tags were set
        tag_calls = mock_sentry.set_tag.call_args_list
        self.assertIn(call("task_id", task_id), tag_calls)
        self.assertIn(call("task_type", task_type), tag_calls)
        
        # Verify context
        self.assertTrue(mock_sentry.set_context.called)
        context_call = mock_sentry.set_context.call_args
        self.assertEqual(context_call[0][0], "task_context")
        self.assertEqual(context_call[0][1]["task_id"], task_id)
        self.assertEqual(context_call[0][1]["task_type"], task_type)
        self.assertEqual(context_call[0][1]["vendor"], "juragan_material")
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_record_progress(self, mock_sentry):
        """Test recording task progress."""
        monitor = JuraganMaterialTaskMonitor(task_id="test", task_type="scraping")
        
        monitor.record_progress(items_processed=5, total_items=10, message="Processing...")
        
        # Verify measurement
        self.assertIn(call("task_progress", 50.0), mock_sentry.set_measurement.call_args_list)
        
        # Verify breadcrumb
        self.assertTrue(mock_sentry.add_breadcrumb.called)
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_record_progress_zero_total(self, mock_sentry):
        """Test recording progress with zero total items."""
        monitor = JuraganMaterialTaskMonitor(task_id="test", task_type="scraping")
        
        monitor.record_progress(items_processed=0, total_items=0)
        
        # Should not crash, progress should be 0
        self.assertIn(call("task_progress", 0), mock_sentry.set_measurement.call_args_list)
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    @patch('api.juragan_material.sentry_monitoring.capture_message')
    def test_complete_success(self, mock_capture, mock_sentry):
        """Test completing task successfully."""
        monitor = JuraganMaterialTaskMonitor(task_id="test_123", task_type="scraping")
        
        result_data = {"products": 10}
        monitor.complete(success=True, result_data=result_data)
        
        # Verify tag
        self.assertIn(call("task_status", "success"), mock_sentry.set_tag.call_args_list)
        
        # Verify message capture
        self.assertTrue(mock_capture.called)
        message_call = mock_capture.call_args
        self.assertIn("test_123", message_call[0][0])
        self.assertEqual(message_call[1]["level"], "info")
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    @patch('api.juragan_material.sentry_monitoring.capture_message')
    def test_complete_failure(self, mock_capture, mock_sentry):
        """Test completing task with failure."""
        monitor = JuraganMaterialTaskMonitor(task_id="test_456", task_type="scraping")
        
        monitor.complete(success=False)
        
        # Verify tag
        self.assertIn(call("task_status", "failed"), mock_sentry.set_tag.call_args_list)
        
        # Verify message capture with warning level
        message_call = mock_capture.call_args
        self.assertEqual(message_call[1]["level"], "warning")


class TestMonitorDecorator(TestCase):
    """Test the monitor_juragan_material_function decorator."""
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    @patch('api.juragan_material.sentry_monitoring.start_span')
    def test_decorator_success(self, mock_start_span, mock_sentry):
        """Test decorator on successful function execution."""
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = Mock(return_value=False)
        
        @monitor_juragan_material_function("test_operation", "scraper")
        def test_function():
            return "success"
        
        result = test_function()
        
        self.assertEqual(result, "success")
        self.assertTrue(mock_start_span.called)
        self.assertTrue(mock_span.set_tag.called)
        self.assertTrue(mock_span.set_data.called)
        
        # Verify span was set with correct operation
        span_call = mock_start_span.call_args
        self.assertEqual(span_call[1]["op"], "juragan_material.scraper")
        self.assertEqual(span_call[1]["description"], "test_operation")
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    @patch('api.juragan_material.sentry_monitoring.start_span')
    @patch('api.juragan_material.sentry_monitoring.capture_exception')
    def test_decorator_error(self, mock_capture, mock_start_span, mock_sentry):
        """Test decorator on function error."""
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = Mock(return_value=False)
        
        @monitor_juragan_material_function("test_operation", "scraper")
        def test_function():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            test_function()
        
        # Verify exception was captured
        self.assertTrue(mock_capture.called)
        self.assertTrue(mock_span.set_data.called)
        
        # Verify error status was set
        set_data_calls = mock_span.set_data.call_args_list
        self.assertIn(call("status", "error"), set_data_calls)
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    @patch('api.juragan_material.sentry_monitoring.start_span')
    def test_decorator_with_args(self, mock_start_span, mock_sentry):
        """Test decorator preserves function arguments."""
        mock_span = MagicMock()
        mock_start_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_start_span.return_value.__exit__ = Mock(return_value=False)
        
        @monitor_juragan_material_function("test_operation", "scraper")
        def test_function(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        result = test_function("x", "y", c="z")
        
        self.assertEqual(result, "x-y-z")


class TestTransactionTracking(TestCase):
    """Test the track_juragan_material_transaction context manager."""
    
    @patch('api.juragan_material.sentry_monitoring.start_transaction')
    def test_transaction_creation(self, mock_start_transaction):
        """Test transaction is created with correct parameters."""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value = mock_transaction
        
        track_juragan_material_transaction("test_transaction")
        
        # Verify transaction was created
        mock_start_transaction.assert_called_once_with(
            op="scraping.juragan_material",
            name="test_transaction"
        )
        
        # Verify tags were set
        self.assertTrue(mock_transaction.set_tag.called)
        tag_calls = mock_transaction.set_tag.call_args_list
        self.assertIn(call("vendor", "juragan_material"), tag_calls)
        self.assertIn(call("transaction_type", "scraping"), tag_calls)
    
    @patch('api.juragan_material.sentry_monitoring.start_transaction')
    def test_transaction_none_handling(self, mock_start_transaction):
        """Test handles None transaction gracefully."""
        mock_start_transaction.return_value = None
        
        # Should not raise an error
        transaction = track_juragan_material_transaction("test_transaction")
        
        self.assertIsNone(transaction)


class TestViewsIntegration(TestCase):
    """Test Sentry monitoring integration in views."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.client = Client()
    
    @patch('api.juragan_material.views.track_juragan_material_transaction')
    @patch('api.juragan_material.views.JuraganMaterialTaskMonitor')
    @patch('api.juragan_material.views.JuraganMaterialSentryMonitor')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    @patch('api.juragan_material.views.InputValidator')
    @patch('api.gemilang.security.AccessControlManager.validate_token')
    def test_scrape_products_with_monitoring(
        self, mock_validate_token, mock_input_validator, mock_scraper, mock_monitor, mock_task, mock_transaction
    ):
        """Test scrape_products view has Sentry monitoring."""
        # Setup security mocks
        mock_validate_token.return_value = (True, '', {'name': 'test-token', 'permissions': ['read', 'write']})
        
        # Setup InputValidator mocks
        mock_input_validator.validate_keyword.return_value = (True, None, 'test')
        mock_input_validator.validate_integer_param.return_value = (True, 0, None)
        mock_input_validator.validate_boolean_param.side_effect = [
            (True, True, None),  # sort_by_price
            (True, False, None)  # save_to_db
        ]
        mock_input_validator.sanitize_for_logging.return_value = 'test'
        
        # Setup scraper mocks
        mock_scraper_instance = Mock()
        mock_scraper.return_value = mock_scraper_instance
        
        mock_result = ScrapingResult(
            products=[],
            success=True,
            error_message=None,
            url="https://test.com"
        )
        mock_scraper_instance.scrape_products.return_value = mock_result
        
        mock_transaction_ctx = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_transaction_ctx)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)
        
        mock_task_instance = Mock()
        mock_task.return_value = mock_task_instance
        
        # Create request with security header
        request = self.factory.get('/scrape/', {'keyword': 'test', 'page': '0'})
        request.headers = {'X-API-Token': 'test-token'}
        
        # Call view
        scrape_products(request)
        
        # Verify monitoring was called
        self.assertTrue(mock_transaction.called)
        self.assertTrue(mock_monitor.set_scraping_context.called)
        self.assertTrue(mock_monitor.add_breadcrumb.called)
        self.assertTrue(mock_monitor.track_scraping_result.called)
        self.assertTrue(mock_task_instance.complete.called)
    
    @patch('api.juragan_material.views.track_juragan_material_transaction')
    @patch('api.juragan_material.views.JuraganMaterialTaskMonitor')
    @patch('api.juragan_material.views.JuraganMaterialSentryMonitor')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    @patch('api.juragan_material.views.InputValidator')
    @patch('api.gemilang.security.AccessControlManager.validate_token')
    def test_scrape_and_save_with_monitoring(
        self, mock_validate_token, mock_input_validator, mock_scraper, mock_monitor, mock_task, mock_transaction
    ):
        """Test scrape_and_save_products view has Sentry monitoring."""
        # Setup security mocks
        mock_validate_token.return_value = (True, '', {'name': 'test-token', 'permissions': ['read', 'write']})
        
        # Setup InputValidator mocks
        mock_input_validator.validate_keyword.return_value = (True, None, 'test')
        mock_input_validator.validate_sort_type.return_value = (True, 'cheapest', None)
        mock_input_validator.validate_integer_param.return_value = (True, 0, None)
        mock_input_validator.sanitize_for_logging.return_value = 'test'
        
        # Setup scraper mocks
        mock_scraper_instance = Mock()
        mock_scraper.return_value = mock_scraper_instance
        
        mock_result = ScrapingResult(
            products=[],
            success=True,
            error_message=None,
            url="https://test.com"
        )
        mock_scraper_instance.scrape_products.return_value = mock_result
        
        mock_transaction_ctx = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_transaction_ctx)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)
        
        mock_task_instance = Mock()
        mock_task.return_value = mock_task_instance
        
        # Create request with security header
        request = self.factory.get('/scrape-save/', {'keyword': 'test', 'page': '0'})
        request.headers = {'X-API-Token': 'test-token'}
        
        # Call view
        scrape_and_save_products(request)
        
        # Verify monitoring was called
        self.assertTrue(mock_transaction.called)
        self.assertTrue(mock_monitor.set_scraping_context.called)
        self.assertTrue(mock_monitor.add_breadcrumb.called)
        self.assertTrue(mock_task_instance.complete.called)
    
    @patch('api.juragan_material.views.track_juragan_material_transaction')
    @patch('api.juragan_material.views.JuraganMaterialTaskMonitor')
    @patch('api.juragan_material.views.JuraganMaterialSentryMonitor')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    @patch('api.juragan_material.views.InputValidator')
    @patch('api.gemilang.security.AccessControlManager.validate_token')
    def test_scrape_popularity_with_monitoring(
        self, mock_validate_token, mock_input_validator, mock_scraper, mock_monitor, mock_task, mock_transaction
    ):
        """Test scrape_popularity view has Sentry monitoring."""
        # Setup security mocks
        mock_validate_token.return_value = (True, '', {'name': 'test-token', 'permissions': ['read', 'write']})
        
        # Setup InputValidator mocks
        mock_input_validator.validate_keyword.return_value = (True, None, 'test')
        mock_input_validator.validate_integer_param.side_effect = [
            (True, 0, None),  # page
            (True, 5, None)   # top_n
        ]
        mock_input_validator.sanitize_for_logging.return_value = 'test'
        
        # Setup scraper mocks
        mock_scraper_instance = Mock()
        mock_scraper.return_value = mock_scraper_instance
        
        mock_result = ScrapingResult(
            products=[],
            success=True,
            error_message=None,
            url="https://test.com"
        )
        mock_scraper_instance.scrape_popularity_products.return_value = mock_result
        
        mock_transaction_ctx = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_transaction_ctx)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)
        
        mock_task_instance = Mock()
        mock_task.return_value = mock_task_instance
        
        # Create request with security header
        request = self.factory.get('/scrape-popularity/', {'keyword': 'test', 'page': '0'})
        request.headers = {'X-API-Token': 'test-token'}
        
        # Call view
        scrape_popularity(request)
        
        # Verify monitoring was called
        self.assertTrue(mock_transaction.called)
        self.assertTrue(mock_monitor.set_scraping_context.called)
        self.assertTrue(mock_monitor.add_breadcrumb.called)
        self.assertTrue(mock_monitor.track_scraping_result.called)
        self.assertTrue(mock_task_instance.complete.called)
    
    @patch('api.juragan_material.views.track_juragan_material_transaction')
    @patch('api.juragan_material.views.JuraganMaterialTaskMonitor')
    @patch('api.juragan_material.views.JuraganMaterialSentryMonitor')
    @patch('api.juragan_material.views.create_juraganmaterial_scraper')
    @patch('api.juragan_material.views.InputValidator')
    @patch('api.gemilang.security.AccessControlManager.validate_token')
    def test_monitoring_on_error(
        self, mock_validate_token, mock_input_validator, mock_scraper, mock_monitor, mock_task, mock_transaction
    ):
        """Test monitoring tracks errors properly."""
        # Setup security mocks
        mock_validate_token.return_value = (True, '', {'name': 'test-token', 'permissions': ['read', 'write']})
        
        # Setup InputValidator to succeed initially, then scraper to fail
        mock_input_validator.validate_keyword.return_value = (True, None, 'test')
        mock_input_validator.validate_integer_param.return_value = (True, 0, None)
        mock_input_validator.validate_boolean_param.side_effect = [
            (True, True, None),  # sort_by_price
            (True, False, None)  # save_to_db
        ]
        mock_input_validator.sanitize_for_logging.return_value = 'test'
        
        # Setup mocks to raise an exception during scraping
        mock_scraper_instance = Mock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.scrape_products.side_effect = Exception("Test error")
        
        mock_transaction_ctx = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_transaction_ctx)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)
        
        mock_task_instance = Mock()
        mock_task.return_value = mock_task_instance
        
        # Create request with security header
        request = self.factory.get('/scrape/', {'keyword': 'test'})
        request.headers = {'X-API-Token': 'test-token'}
        
        # Call view - should handle exception
        scrape_products(request)
        
        # Verify error breadcrumb was added
        breadcrumb_calls = [str(call) for call in mock_monitor.add_breadcrumb.call_args_list]
        has_error_breadcrumb = any("error" in call.lower() or "fatal" in call.lower() for call in breadcrumb_calls)
        self.assertTrue(has_error_breadcrumb)


class TestDatabaseMonitoring(TestCase):
    """Test Sentry monitoring in database operations."""
    
    @patch('api.juragan_material.views.JuraganMaterialSentryMonitor')
    @patch('api.juragan_material.views.JuraganMaterialDatabaseService')
    @patch('api.juragan_material.views.time')
    def test_save_products_monitoring(self, mock_time, mock_db_service, mock_monitor):
        """Test that database save operations are monitored."""
        # Setup time mock
        mock_time.time.side_effect = [100.0, 101.0, 102.0, 103.0]
        
        # Setup mock product
        mock_product = Mock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com"
        mock_product.unit = "pcs"
        mock_product.location = "Test Location"
        
        # Setup mock database service
        mock_db_instance = Mock()
        mock_db_service.return_value = mock_db_instance
        mock_db_instance.save_with_price_update.return_value = {
            'success': True,
            'inserted': 1,
            'updated': 0,
            'anomalies': []
        }
        
        # Call function
        _save_products_to_database([mock_product])
        
        # Verify monitoring was called
        self.assertTrue(mock_monitor.add_breadcrumb.called)
        self.assertTrue(mock_monitor.track_database_operation.called)
        
        # Verify breadcrumb for database save
        breadcrumb_calls = [str(call[0]) for call in mock_monitor.add_breadcrumb.call_args_list]
        has_db_breadcrumb = any("database" in call.lower() for call in breadcrumb_calls)
        self.assertTrue(has_db_breadcrumb)
    
    @patch('api.juragan_material.views.JuraganMaterialSentryMonitor')
    @patch('api.juragan_material.views.JuraganMaterialDatabaseService')
    def test_save_products_error_monitoring(self, mock_db_service, mock_monitor):
        """Test database error monitoring."""
        # Setup mock to raise exception
        mock_db_instance = Mock()
        mock_db_service.return_value = mock_db_instance
        mock_db_instance.save_with_price_update.side_effect = Exception("DB Error")
        
        # Setup mock product
        mock_product = Mock()
        mock_product.name = "Test Product"
        mock_product.price = 10000
        mock_product.url = "https://test.com"
        mock_product.unit = "pcs"
        mock_product.location = "Test Location"
        
        # Call function - should handle error
        result = _save_products_to_database([mock_product])
        
        # Verify error result
        self.assertFalse(result['success'])
        
        # Verify error breadcrumb
        breadcrumb_calls = [str(call[0]) for call in mock_monitor.add_breadcrumb.call_args_list]
        has_error_breadcrumb = any("failed" in call.lower() for call in breadcrumb_calls)
        self.assertTrue(has_error_breadcrumb)
    
    @patch('api.juragan_material.views.JuraganMaterialSentryMonitor')
    def test_save_empty_products(self, mock_monitor):
        """Test handling of empty product list."""
        result = _save_products_to_database([])
        
        self.assertFalse(result['success'])
        self.assertEqual(result['inserted'], 0)
        self.assertEqual(result['updated'], 0)


class TestBreadcrumbTracking(TestCase):
    """Test breadcrumb tracking functionality."""
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_breadcrumb_with_default_data(self, mock_sentry):
        """Test breadcrumb with default data parameter."""
        JuraganMaterialSentryMonitor.add_breadcrumb(
            message="Test message",
            category="test"
        )
        
        call_args = mock_sentry.add_breadcrumb.call_args
        self.assertEqual(call_args[1]['data'], {})
        self.assertEqual(call_args[1]['level'], "info")
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_breadcrumb_categories(self, mock_sentry):
        """Test different breadcrumb categories."""
        categories = [
            "juragan_material.scraper",
            "juragan_material.database",
            "juragan_material.categorization",
            "juragan_material.error"
        ]
        
        for category in categories:
            JuraganMaterialSentryMonitor.add_breadcrumb(
                message=f"Test {category}",
                category=category
            )
        
        self.assertEqual(mock_sentry.add_breadcrumb.call_count, len(categories))


class TestContextManagement(TestCase):
    """Test context management in monitoring."""
    
    @patch('api.juragan_material.sentry_monitoring.sentry_sdk')
    def test_multiple_contexts(self, mock_sentry):
        """Test setting multiple contexts."""
        # Set scraping context
        JuraganMaterialSentryMonitor.set_scraping_context(
            keyword="test",
            page=0,
            additional_data={"source": "test"}
        )
        
        # Track result (sets another context)
        JuraganMaterialSentryMonitor.track_scraping_result({
            'products_count': 5,
            'success': True,
            'errors_count': 0
        })
        
        # Verify both contexts were set
        context_calls = mock_sentry.set_context.call_args_list
        context_names = [call[0][0] for call in context_calls]
        
        self.assertIn("scraping_context", context_names)
        self.assertIn("scraping_result", context_names)
