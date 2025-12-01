import logging

import pytest

from api.tokopedia.logging_utils import get_tokopedia_logger


def test_logger_prefixes_component(caplog):
    logger = get_tokopedia_logger("html_parser")

    with caplog.at_level(logging.INFO):
        logger.info("Parsing %s items", 3)

    assert caplog.records
    record = caplog.records[0]
    assert record.name == "api.tokopedia"
    assert "[component=html_parser]" in record.message
    assert "Parsing 3 items" in record.message


def test_logger_sanitizes_newlines(caplog):
    logger = get_tokopedia_logger("security")

    with caplog.at_level(logging.WARNING):
        logger.warning("Line with newline\nand return %s", "OK\nTest")

    message = caplog.records[0].message
    assert "\n" not in message
    assert "\r" not in message
    assert "Line with newline and return OK Test" in message


def test_logger_operation_context(caplog):
    logger = get_tokopedia_logger("database")

    with caplog.at_level(logging.ERROR):
        logger.error("Insert failed", extra={"operation": "save"})

    message = caplog.records[0].message
    assert "[op=save]" in message
    assert "Insert failed" in message
