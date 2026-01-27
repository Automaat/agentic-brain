"""Tests for logging configuration."""

import logging

import structlog

from src.logging_config import add_request_id, get_logger, request_id_var, setup_logging


def test_setup_logging_json_format() -> None:
    """Test logging setup with JSON format."""
    setup_logging(log_level="INFO", json_format=True)

    logger = get_logger("test")
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")


def test_setup_logging_console_format() -> None:
    """Test logging setup with console format."""
    setup_logging(log_level="DEBUG", json_format=False)

    logger = get_logger("test")
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")


def test_setup_logging_warning_level() -> None:
    """Test logging setup with WARNING level."""
    setup_logging(log_level="WARNING", json_format=True)
    assert logging.getLogger().level == logging.WARNING


def test_add_request_id_with_context() -> None:
    """Test request ID is added from context."""
    request_id_var.set("test-request-123")

    event_dict = {}
    result = add_request_id(None, "info", event_dict)

    assert result["request_id"] == "test-request-123"

    # Clean up
    request_id_var.set(None)


def test_add_request_id_without_context() -> None:
    """Test request ID is not added when not in context."""
    request_id_var.set(None)

    event_dict = {}
    result = add_request_id(None, "info", event_dict)

    assert "request_id" not in result


def test_get_logger() -> None:
    """Test logger retrieval."""
    logger = get_logger("test_module")
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")


def test_logging_with_request_id() -> None:
    """Test end-to-end logging with request ID."""
    setup_logging(log_level="INFO", json_format=True)
    request_id_var.set("req-456")

    logger = get_logger("test")
    # This should not raise
    logger.info("test message", extra_field="value")

    # Clean up
    request_id_var.set(None)
