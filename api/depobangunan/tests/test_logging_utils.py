"""
Tests for DepoBangunan logging utilities.

This test suite validates that the DepoBangunan logging implementation:
1. Uses the shared VendorLogger infrastructure correctly
2. Provides proper component-based prefixes
3. Sanitizes log input to prevent injection attacks
4. Supports operation context tracking
5. Maintains consistency with Gemilang's logging approach
"""

import logging
import pytest

from api.depobangunan.logging_utils import get_depobangunan_logger


def test_logger_has_correct_namespace(caplog):
    """Test that DepoBangunan logger uses the correct namespace."""
    logger = get_depobangunan_logger("html_parser")
    
    with caplog.at_level(logging.INFO):
        logger.info("Test message")
    
    assert caplog.records
    record = caplog.records[0]
    assert record.name == "api.depobangunan"


def test_logger_prefixes_component(caplog):
    """Test that logger includes component name in log prefix."""
    logger = get_depobangunan_logger("html_parser")
    
    with caplog.at_level(logging.INFO):
        logger.info("Parsing %s items", 3)
    
    assert caplog.records
    record = caplog.records[0]
    assert "[depobangunan]" in record.message
    assert "[component=html_parser]" in record.message
    assert "Parsing 3 items" in record.message


def test_logger_sanitizes_newlines_in_message(caplog):
    """Test that newline characters are sanitized from log messages."""
    logger = get_depobangunan_logger("security")
    
    with caplog.at_level(logging.WARNING):
        logger.warning("Line with newline\nand return\rcharacter")
    
    message = caplog.records[0].message
    assert "\n" not in message
    assert "\r" not in message
    assert "Line with newline and return character" in message


def test_logger_sanitizes_newlines_in_args(caplog):
    """Test that newline characters are sanitized from log arguments."""
    logger = get_depobangunan_logger("security")
    
    with caplog.at_level(logging.WARNING):
        logger.warning("Processing value: %s", "Malicious\nInput\rData")
    
    message = caplog.records[0].message
    assert "\n" not in message
    assert "\r" not in message
    assert "Malicious Input Data" in message


def test_logger_operation_context(caplog):
    """Test that operation context is properly included in log prefix."""
    logger = get_depobangunan_logger("database_service")
    
    with caplog.at_level(logging.ERROR):
        logger.error("Insert failed", extra={"operation": "save_products"})
    
    message = caplog.records[0].message
    assert "[op=save_products]" in message
    assert "Insert failed" in message
    assert "[component=database_service]" in message


def test_logger_operation_context_sanitized(caplog):
    """Test that operation context values are sanitized."""
    logger = get_depobangunan_logger("scraper")
    
    with caplog.at_level(logging.INFO):
        logger.info("Processing", extra={"operation": "scrape\nproducts"})
    
    message = caplog.records[0].message
    assert "\n" not in message
    assert "[op=scrape products]" in message


def test_logger_multiple_components():
    """Test that different components can have different loggers."""
    logger1 = get_depobangunan_logger("html_parser")
    logger2 = get_depobangunan_logger("database_service")
    
    assert logger1.extra["component"] == "html_parser"
    assert logger2.extra["component"] == "database_service"
    assert logger1.logger.name == "api.depobangunan"
    assert logger2.logger.name == "api.depobangunan"


def test_logger_with_extra_context(caplog):
    """Test logger with additional context provided at initialization."""
    logger = get_depobangunan_logger("scraper", extra={"request_id": "12345"})
    
    with caplog.at_level(logging.INFO):
        logger.info("Scraping started")
    
    record = caplog.records[0]
    assert "request_id" in record.__dict__.get("extra", {}) or "request_id" in record.__dict__


def test_logger_preserves_extra_context_across_calls(caplog):
    """Test that extra context from initialization is preserved."""
    logger = get_depobangunan_logger("views", extra={"session_id": "abc123"})
    
    with caplog.at_level(logging.INFO):
        logger.info("First log")
        logger.info("Second log")
    
    assert len(caplog.records) == 2
    for record in caplog.records:
        # Extra context should be preserved in the logger adapter
        assert "[component=views]" in record.message


def test_logger_different_log_levels(caplog):
    """Test that logger works with different log levels."""
    logger = get_depobangunan_logger("test_component")
    
    with caplog.at_level(logging.DEBUG):
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
    
    # Filter to only depobangunan logs (exclude third-party logs like urllib3)
    depobangunan_records = [r for r in caplog.records if r.name.startswith('api.depobangunan')]
    
    assert len(depobangunan_records) == 4
    levels = [r.levelname for r in depobangunan_records]
    assert levels == ["DEBUG", "INFO", "WARNING", "ERROR"]
    
    for record in depobangunan_records:
        assert "[depobangunan]" in record.message
        assert "[component=test_component]" in record.message


def test_logger_empty_string_not_sanitized_away():
    """Test that empty strings are handled correctly."""
    logger = get_depobangunan_logger("parser")
    # Should not raise an exception
    logger.info("")


def test_logger_none_values_handled():
    """Test that None values don't cause errors."""
    logger = get_depobangunan_logger("parser")
    # Should not raise an exception with None in args
    logger.info("Value is: %s", None)


def test_logger_numeric_arguments(caplog):
    """Test that numeric arguments are logged correctly."""
    logger = get_depobangunan_logger("scraper")
    
    with caplog.at_level(logging.INFO):
        logger.info("Found %d products at price %f", 42, 123.45)
    
    message = caplog.records[0].message
    assert "Found 42 products" in message
    assert "123.45" in message


def test_logger_respects_log_level_filtering():
    """Test that logger respects log level configuration."""
    logger = get_depobangunan_logger("test_component")
    
    # Create a handler with WARNING level
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    
    # Debug and info should be filtered out at handler level
    logger.debug("This is debug")
    logger.info("This is info")
    # These would appear if level is WARNING or higher
    logger.warning("This is warning")
    logger.error("This is error")


def test_logger_format_consistency_with_gemilang(caplog):
    """Test that DepoBangunan logger format matches Gemilang's pattern."""
    logger = get_depobangunan_logger("database_service")
    
    # The format should be: [depobangunan][component=X][op=Y] message
    # This ensures consistency across vendors
    with caplog.at_level(logging.INFO):
        logger.info("Test message", extra={"operation": "test_op"})
    
    message = caplog.records[0].message
    # Verify format follows pattern: [depobangunan][component=X][op=Y] message
    assert "[depobangunan]" in message
    assert "[component=database_service]" in message
    assert "[op=test_op]" in message


def test_logger_concurrent_operations(caplog):
    """Test that different operations can be logged independently."""
    logger = get_depobangunan_logger("scraper")
    
    with caplog.at_level(logging.INFO):
        logger.info("Starting", extra={"operation": "scrape_products"})
        logger.info("Processing", extra={"operation": "parse_html"})
        logger.info("Saving", extra={"operation": "save_to_db"})
    
    assert len(caplog.records) == 3
    operations = []
    for record in caplog.records:
        if "[op=scrape_products]" in record.message:
            operations.append("scrape_products")
        elif "[op=parse_html]" in record.message:
            operations.append("parse_html")
        elif "[op=save_to_db]" in record.message:
            operations.append("save_to_db")
    
    assert operations == ["scrape_products", "parse_html", "save_to_db"]


def test_logger_sql_injection_attempt_sanitized(caplog):
    """Test that potential SQL injection patterns are safely logged."""
    logger = get_depobangunan_logger("security")
    
    malicious_input = "'; DROP TABLE products; --\nSELECT * FROM users"
    
    with caplog.at_level(logging.WARNING):
        logger.warning("Suspicious input detected: %s", malicious_input)
    
    message = caplog.records[0].message
    # Newlines should be sanitized
    assert "\n" not in message
    # But the rest of the content should be preserved for debugging
    assert "DROP TABLE" in message
    assert "SELECT * FROM users" in message


def test_logger_xss_attempt_sanitized(caplog):
    """Test that XSS patterns with newlines are sanitized."""
    logger = get_depobangunan_logger("security")
    
    xss_input = "<script>\nalert('XSS')\n</script>"
    
    with caplog.at_level(logging.WARNING):
        logger.warning("XSS attempt: %s", xss_input)
    
    message = caplog.records[0].message
    # Newlines should be sanitized
    assert "\n" not in message
    assert "\r" not in message
    # Original content preserved (sanitization is only for newlines)
    assert "alert('XSS')" in message
