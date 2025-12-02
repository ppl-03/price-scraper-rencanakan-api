import logging
import unittest
from unittest.mock import patch, MagicMock
from api.juragan_material.logging_utils import (
    _sanitize_log_input,
    JuraganMaterialLogger,
    get_juragan_material_logger,
    LOG_NAMESPACE
)


class TestSanitizeLogInput(unittest.TestCase):
    """Test _sanitize_log_input function"""
    
    def test_sanitize_string_with_newlines(self):
        """Test that newlines are replaced with spaces"""
        result = _sanitize_log_input("Hello\nWorld")
        self.assertEqual(result, "Hello World")
    
    def test_sanitize_string_with_carriage_returns(self):
        """Test that carriage returns are replaced with spaces"""
        result = _sanitize_log_input("Hello\rWorld")
        self.assertEqual(result, "Hello World")
    
    def test_sanitize_string_with_both_newlines_and_carriage_returns(self):
        """Test that both newlines and carriage returns are replaced"""
        result = _sanitize_log_input("Hello\n\rWorld\r\n!")
        self.assertEqual(result, "Hello  World  !")
    
    def test_sanitize_non_string_returns_unchanged(self):
        """Test that non-string values are returned unchanged"""
        self.assertEqual(_sanitize_log_input(123), 123)
        self.assertIsNone(_sanitize_log_input(None))
        self.assertEqual(_sanitize_log_input([1, 2, 3]), [1, 2, 3])
        self.assertEqual(_sanitize_log_input({"key": "value"}), {"key": "value"})
    
    def test_sanitize_empty_string(self):
        """Test that empty strings are handled correctly"""
        result = _sanitize_log_input("")
        self.assertEqual(result, "")
    
    def test_sanitize_log_injection_attempt(self):
        """Test protection against log injection attacks"""
        malicious_input = "User login\nINFO:Fake admin login successful"
        result = _sanitize_log_input(malicious_input)
        self.assertNotIn("\n", result)
        self.assertEqual(result, "User login INFO:Fake admin login successful")


class TestJuraganMaterialLogger(unittest.TestCase):
    """Test JuraganMaterialLogger class"""
    
    def test_logger_initialization(self):
        """Test logger is initialized with correct component"""
        logger = JuraganMaterialLogger("test_component")
        self.assertEqual(logger.extra["component"], "test_component")
    
    def test_logger_initialization_with_extra(self):
        """Test logger initialization with extra context"""
        extra_context = {"user_id": "12345", "session": "abc"}
        logger = JuraganMaterialLogger("test_component", extra=extra_context)
        self.assertEqual(logger.extra["component"], "test_component")
        self.assertEqual(logger.extra["user_id"], "12345")
        self.assertEqual(logger.extra["session"], "abc")
    
    def test_logger_uses_correct_namespace(self):
        """Test logger uses the correct namespace"""
        logger = JuraganMaterialLogger("test_component")
        self.assertEqual(logger.logger.name, LOG_NAMESPACE)
    
    def test_process_adds_component_prefix(self):
        """Test that process method adds component prefix"""
        logger = JuraganMaterialLogger("scraper")
        msg, _ = logger.process("Test message", {})
        self.assertIn("[juragan_material][component=scraper]", msg)
        self.assertIn("Test message", msg)
    
    def test_process_adds_operation_prefix(self):
        """Test that process method adds operation prefix when provided"""
        logger = JuraganMaterialLogger("scraper")
        msg, _ = logger.process("Test message", {"extra": {"operation": "parse_html"}})
        self.assertIn("[juragan_material][component=scraper]", msg)
        self.assertIn("[op=parse_html]", msg)
        self.assertIn("Test message", msg)
    
    def test_process_sanitizes_message(self):
        """Test that process method sanitizes the message"""
        logger = JuraganMaterialLogger("scraper")
        msg, _ = logger.process("Test\nmessage", {})
        self.assertNotIn("\n", msg)
        self.assertIn("Test message", msg)
    
    def test_process_sanitizes_component(self):
        """Test that component name is sanitized"""
        logger = JuraganMaterialLogger("test\ncomponent")
        msg, _ = logger.process("Test message", {})
        self.assertNotIn("\n", msg)
        self.assertIn("component=test component", msg)
    
    def test_process_sanitizes_operation(self):
        """Test that operation name is sanitized"""
        logger = JuraganMaterialLogger("scraper")
        msg, _ = logger.process("Test message", {"extra": {"operation": "parse\nhtml"}})
        self.assertNotIn("\n", msg)
        self.assertIn("op=parse html", msg)
    
    def test_log_method_calls_base_logger(self):
        """Test that log method calls the base logger"""
        with self.assertLogs('api.juragan_material', level='INFO') as captured:
            logger = JuraganMaterialLogger("scraper")
            logger.log(logging.INFO, "Test message")
        
        self.assertEqual(len(captured.records), 1)
        self.assertIn("Test message", captured.records[0].getMessage())
    
    def test_log_sanitizes_message_argument(self):
        """Test that log method sanitizes message"""
        with self.assertLogs('api.juragan_material', level='INFO') as captured:
            logger = JuraganMaterialLogger("scraper")
            logger.log(logging.INFO, "Test\nmessage")
        
        log_message = captured.records[0].getMessage()
        self.assertNotIn("\n", log_message)
        self.assertIn("Test message", log_message)
    
    def test_log_sanitizes_format_arguments(self):
        """Test that log method sanitizes format arguments"""
        with self.assertLogs('api.juragan_material', level='INFO') as captured:
            logger = JuraganMaterialLogger("scraper")
            logger.log(logging.INFO, "Scraped %s", "test\nvalue")
        
        log_message = captured.records[0].getMessage()
        self.assertNotIn("\n", log_message)
        self.assertIn("test value", log_message)
    
    def test_log_respects_log_level(self):
        """Test that log method respects log level settings"""
        # Set logger to WARNING level
        test_logger = logging.getLogger('api.juragan_material')
        original_level = test_logger.level
        test_logger.setLevel(logging.WARNING)
        
        try:
            logger = JuraganMaterialLogger("scraper")
            # DEBUG message should not appear when level is WARNING
            with patch.object(logger, 'isEnabledFor', return_value=False):
                with patch.object(logger.logger, 'log') as mock_log:
                    logger.log(logging.DEBUG, "Debug message")
                    mock_log.assert_not_called()
        finally:
            test_logger.setLevel(original_level)
    
    def test_log_with_multiple_format_arguments(self):
        """Test logging with multiple format arguments"""
        with self.assertLogs('api.juragan_material', level='INFO') as captured:
            logger = JuraganMaterialLogger("scraper")
            logger.log(logging.INFO, "Found %d products at %s", 50, "https://example.com")
        
        log_message = captured.records[0].getMessage()
        self.assertIn("Found 50 products at https://example.com", log_message)
    
    def test_log_preserves_extra_context(self):
        """Test that extra context is preserved in log calls"""
        with self.assertLogs('api.juragan_material', level='INFO') as captured:
            logger = JuraganMaterialLogger("scraper", extra={"user_id": "12345"})
            logger.log(logging.INFO, "Test message", extra={"request_id": "abc"})
        
        record = captured.records[0]
        self.assertIn("Test message", record.getMessage())
        # Extra context is stored in the record
        self.assertEqual(record.component, "scraper")
        self.assertEqual(record.user_id, "12345")
        self.assertEqual(record.request_id, "abc")


class TestGetJuraganMaterialLogger(unittest.TestCase):
    """Test get_juragan_material_logger factory function"""
    
    def test_returns_juragan_material_logger_instance(self):
        """Test that factory returns JuraganMaterialLogger instance"""
        logger = get_juragan_material_logger("test_component")
        self.assertIsInstance(logger, JuraganMaterialLogger)
    
    def test_factory_sets_component(self):
        """Test that factory sets the component correctly"""
        logger = get_juragan_material_logger("database")
        self.assertEqual(logger.extra["component"], "database")
    
    def test_factory_accepts_extra_context(self):
        """Test that factory accepts and sets extra context"""
        extra = {"session_id": "xyz", "user": "admin"}
        logger = get_juragan_material_logger("views", extra=extra)
        self.assertEqual(logger.extra["component"], "views")
        self.assertEqual(logger.extra["session_id"], "xyz")
        self.assertEqual(logger.extra["user"], "admin")
    
    def test_factory_creates_different_loggers(self):
        """Test that factory creates different loggers for different components"""
        logger1 = get_juragan_material_logger("scraper")
        logger2 = get_juragan_material_logger("database")
        
        self.assertIsNot(logger1, logger2)
        self.assertEqual(logger1.extra["component"], "scraper")
        self.assertEqual(logger2.extra["component"], "database")


class TestLoggerIntegration(unittest.TestCase):
    """Integration tests for logger in real usage scenarios"""
    
    def test_info_logging_with_format(self):
        """Test INFO level logging with format arguments"""
        with self.assertLogs('api.juragan_material', level='INFO') as captured:
            logger = get_juragan_material_logger("scraper")
            logger.info("Scraped %d products from page %d", 50, 1)
        
        self.assertEqual(len(captured.records), 1)
        log_message = captured.records[0].getMessage()
        self.assertIn("[juragan_material][component=scraper]", log_message)
        self.assertIn("Scraped 50 products from page 1", log_message)
    
    def test_warning_logging_with_operation(self):
        """Test WARNING level logging with operation context"""
        with self.assertLogs('api.juragan_material', level='WARNING') as captured:
            logger = get_juragan_material_logger("database")
            logger.warning("Failed to save product", extra={"operation": "save_to_db"})
        
        self.assertEqual(len(captured.records), 1)
        log_message = captured.records[0].getMessage()
        self.assertIn("[juragan_material][component=database]", log_message)
        self.assertIn("[op=save_to_db]", log_message)
        self.assertIn("Failed to save product", log_message)
    
    def test_error_logging_with_exception_info(self):
        """Test ERROR level logging with exception info"""
        with self.assertLogs('api.juragan_material', level='ERROR') as captured:
            logger = get_juragan_material_logger("parser")
            try:
                raise ValueError("Invalid HTML structure")
            except ValueError:
                logger.error("Parse failed", exc_info=True)
        
        self.assertEqual(len(captured.records), 1)
        log_message = captured.records[0].getMessage()
        self.assertIn("[juragan_material][component=parser]", log_message)
        self.assertIn("Parse failed", log_message)
    
    def test_debug_logging_is_not_shown_by_default(self):
        """Test that DEBUG logs are not shown when level is INFO"""
        logger = get_juragan_material_logger("scraper")
        
        # DEBUG logs should not appear
        with patch('logging.Logger.isEnabledFor', return_value=False):
            with patch('logging.Logger.log') as mock_log:
                logger.debug("Debug message")
                mock_log.assert_not_called()
    
    def test_multiple_loggers_different_components(self):
        """Test multiple loggers with different components logging simultaneously"""
        with self.assertLogs('api.juragan_material', level='INFO') as captured:
            scraper_logger = get_juragan_material_logger("scraper")
            db_logger = get_juragan_material_logger("database")
            
            scraper_logger.info("Started scraping")
            db_logger.info("Connected to database")
            scraper_logger.info("Finished scraping")
        
        self.assertEqual(len(captured.records), 3)
        self.assertIn("component=scraper", captured.records[0].getMessage())
        self.assertIn("component=database", captured.records[1].getMessage())
        self.assertIn("component=scraper", captured.records[2].getMessage())
    
    def test_log_injection_prevention_integration(self):
        """Test that log injection attacks are prevented in real usage"""
        with self.assertLogs('api.juragan_material', level='WARNING') as captured:
            logger = get_juragan_material_logger("security")
            malicious_input = "User login failed\nINFO: Admin login successful"
            logger.warning("Authentication attempt: %s", malicious_input)
        
        log_output = captured.output[0]
        # Should not have actual newlines that could inject fake log entries
        self.assertNotIn("\nINFO:", log_output)
        self.assertIn("User login failed INFO: Admin login successful", log_output)


if __name__ == '__main__':
    unittest.main()
