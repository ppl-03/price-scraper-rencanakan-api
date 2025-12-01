import logging
from unittest.mock import MagicMock, patch
from django.test import TestCase

from api.mitra10.logging_utils import (
    _sanitize_log_input,
    Mitra10Logger,
    get_mitra10_logger,
    LOG_NAMESPACE
)


class SanitizeLogInputTest(TestCase):
    """Tests for _sanitize_log_input function."""
    
    def test_sanitize_removes_newlines(self):
        """Should remove newline characters from strings."""
        input_str = "Line 1\nLine 2\nLine 3"
        result = _sanitize_log_input(input_str)
        self.assertEqual(result, "Line 1 Line 2 Line 3")
        self.assertNotIn("\n", result)
    
    def test_sanitize_removes_carriage_returns(self):
        """Should remove carriage return characters from strings."""
        input_str = "Text\rMore text\rEven more"
        result = _sanitize_log_input(input_str)
        self.assertEqual(result, "Text More text Even more")
        self.assertNotIn("\r", result)
    
    def test_sanitize_handles_mixed_line_endings(self):
        """Should handle both newlines and carriage returns."""
        input_str = "Windows\r\nLinux\nMac\r"
        result = _sanitize_log_input(input_str)
        self.assertNotIn("\r", result)
        self.assertNotIn("\n", result)
    
    def test_sanitize_non_string_unchanged(self):
        """Should return non-string values unchanged."""
        test_cases = [
            123,
            45.67,
            None,
            True,
            False,
            {"key": "value"},
            [1, 2, 3]
        ]
        for value in test_cases:
            with self.subTest(value=value):
                result = _sanitize_log_input(value)
                self.assertEqual(result, value)
    
    def test_sanitize_empty_string(self):
        """Should handle empty strings."""
        result = _sanitize_log_input("")
        self.assertEqual(result, "")


class Mitra10LoggerTest(TestCase):
    """Tests for Mitra10Logger class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.component = "test_component"
        self.logger = Mitra10Logger(self.component)
    
    def test_initialization_with_component(self):
        """Should initialize with component name."""
        logger = Mitra10Logger("scraper")
        self.assertEqual(logger.extra["component"], "scraper")
    
    def test_initialization_with_extra_context(self):
        """Should initialize with additional context."""
        extra = {"request_id": "12345", "user": "test_user"}
        logger = Mitra10Logger("database_service", extra=extra)
        self.assertEqual(logger.extra["component"], "database_service")
        self.assertEqual(logger.extra["request_id"], "12345")
        self.assertEqual(logger.extra["user"], "test_user")
    
    def test_process_adds_component_prefix(self):
        """Should add component to log message prefix."""
        msg, _ = self.logger.process("Test message", {})
        self.assertIn("[mitra10]", msg)
        self.assertIn(f"[component={self.component}]", msg)
        self.assertIn("Test message", msg)
    
    def test_process_adds_operation_from_extra(self):
        """Should add operation to prefix when provided in extra."""
        kwargs = {"extra": {"operation": "scrape_products"}}
        msg, _ = self.logger.process("Starting scrape", kwargs)
        self.assertIn("[op=scrape_products]", msg)
    
    def test_process_adds_operation_from_logger_extra(self):
        """Should use operation from logger's extra if not in kwargs."""
        logger = Mitra10Logger("scraper", extra={"operation": "default_op"})
        msg, _ = logger.process("Test", {})
        self.assertIn("[op=default_op]", msg)
    
    def test_process_sanitizes_message(self):
        """Should sanitize message content."""
        msg, _ = self.logger.process("Message\nwith\nnewlines", {})
        self.assertNotIn("\n", msg)
    
    def test_process_sanitizes_component(self):
        """Should sanitize component name."""
        logger = Mitra10Logger("component\nwith\nnewlines")
        msg, _ = logger.process("Test", {})
        self.assertNotIn("\n", msg)
    
    def test_process_sanitizes_operation(self):
        """Should sanitize operation name."""
        kwargs = {"extra": {"operation": "op\nwith\nnewlines"}}
        msg, _ = self.logger.process("Test", kwargs)
        self.assertNotIn("\n", msg)
    
    def test_process_merges_extra_context(self):
        """Should merge extra context from kwargs with logger extra."""
        logger = Mitra10Logger("scraper", extra={"static": "value"})
        kwargs = {"extra": {"dynamic": "data"}}
        _, processed_kwargs = logger.process("Test", kwargs)
        
        self.assertIn("static", processed_kwargs["extra"])
        self.assertIn("dynamic", processed_kwargs["extra"])
        self.assertEqual(processed_kwargs["extra"]["static"], "value")
        self.assertEqual(processed_kwargs["extra"]["dynamic"], "data")
    
    @patch('logging.LoggerAdapter.log')
    def test_log_checks_level_enabled(self, mock_parent_log):
        """Should check if log level is enabled before processing."""
        with patch.object(self.logger, 'isEnabledFor', return_value=False):
            self.logger.log(logging.INFO, "Test message")
            mock_parent_log.assert_not_called()
    
    @patch('logging.Logger.log')
    def test_log_sanitizes_arguments(self, mock_log):
        """Should sanitize all arguments passed to log."""
        with patch.object(self.logger, 'isEnabledFor', return_value=True):
            self.logger.log(logging.INFO, "Test %s %s", "arg1\nwith\nnewline", "arg2\rwith\rcarriage")
            
            # Check that log was called
            self.assertTrue(mock_log.called)
            call_args = mock_log.call_args
            
            # Verify arguments were sanitized
            args = call_args[0][2:]  # Skip level and message
            for arg in args:
                self.assertNotIn("\n", str(arg))
                self.assertNotIn("\r", str(arg))
    
    def test_logger_uses_correct_namespace(self):
        """Should use correct log namespace."""
        logger = Mitra10Logger("test")
        self.assertEqual(logger.logger.name, LOG_NAMESPACE)
        self.assertEqual(LOG_NAMESPACE, "api.mitra10")


class GetMitra10LoggerTest(TestCase):
    """Tests for get_mitra10_logger factory function."""
    
    def test_returns_mitra10_logger_instance(self):
        """Should return a Mitra10Logger instance."""
        logger = get_mitra10_logger("scraper")
        self.assertIsInstance(logger, Mitra10Logger)
    
    def test_sets_component_name(self):
        """Should set component name correctly."""
        logger = get_mitra10_logger("database_service")
        self.assertEqual(logger.extra["component"], "database_service")
    
    def test_accepts_extra_context(self):
        """Should accept and set extra context."""
        extra = {"request_id": "abc123", "session": "xyz"}
        logger = get_mitra10_logger("security", extra=extra)
        self.assertEqual(logger.extra["request_id"], "abc123")
        self.assertEqual(logger.extra["session"], "xyz")
    
    def test_creates_independent_loggers(self):
        """Should create independent logger instances."""
        logger1 = get_mitra10_logger("component1")
        logger2 = get_mitra10_logger("component2")
        
        self.assertIsNot(logger1, logger2)
        self.assertEqual(logger1.extra["component"], "component1")
        self.assertEqual(logger2.extra["component"], "component2")


class Mitra10LoggerIntegrationTest(TestCase):
    """Integration tests for Mitra10Logger with actual logging."""
    
    def setUp(self):
        """Set up test logger with handler."""
        self.logger = get_mitra10_logger("integration_test")
        self.log_messages = []
        
        # Create custom handler to capture log messages
        class ListHandler(logging.Handler):
            def __init__(self, message_list):
                super().__init__()
                self.message_list = message_list
            
            def emit(self, record):
                self.message_list.append(self.format(record))
        
        self.handler = ListHandler(self.log_messages)
        self.handler.setLevel(logging.DEBUG)
        self.logger.logger.addHandler(self.handler)
        self.logger.logger.setLevel(logging.DEBUG)
    
    def tearDown(self):
        """Clean up handler."""
        self.logger.logger.removeHandler(self.handler)
    
    def test_info_logging(self):
        """Should log info messages correctly."""
        self.logger.info("Test info message")
        self.assertEqual(len(self.log_messages), 1)
        self.assertIn("[mitra10]", self.log_messages[0])
        self.assertIn("[component=integration_test]", self.log_messages[0])
        self.assertIn("Test info message", self.log_messages[0])
    
    def test_error_logging_with_operation(self):
        """Should log error messages with operation context."""
        self.logger.error("Error occurred", extra={"operation": "test_operation"})
        self.assertEqual(len(self.log_messages), 1)
        self.assertIn("[op=test_operation]", self.log_messages[0])
        self.assertIn("Error occurred", self.log_messages[0])
    
    def test_warning_logging(self):
        """Should log warning messages."""
        self.logger.warning("Warning message")
        self.assertEqual(len(self.log_messages), 1)
        self.assertIn("Warning message", self.log_messages[0])
    
    def test_debug_logging(self):
        """Should log debug messages when level is set."""
        self.logger.debug("Debug info")
        self.assertEqual(len(self.log_messages), 1)
        self.assertIn("Debug info", self.log_messages[0])
    
    def test_critical_logging(self):
        """Should log critical messages."""
        self.logger.critical("Critical error")
        self.assertEqual(len(self.log_messages), 1)
        self.assertIn("Critical error", self.log_messages[0])
    
    def test_multiple_log_calls(self):
        """Should handle multiple sequential log calls."""
        self.logger.info("First message")
        self.logger.warning("Second message")
        self.logger.error("Third message")
        
        self.assertEqual(len(self.log_messages), 3)
        self.assertIn("First message", self.log_messages[0])
        self.assertIn("Second message", self.log_messages[1])
        self.assertIn("Third message", self.log_messages[2])
