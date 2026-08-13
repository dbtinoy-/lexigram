"""Tests for logging/__init__.py lazy imports."""

import pytest


class TestLoggingLazyImports:
    """Test lazy imports from logging module."""

    def test_import_get_logger(self) -> None:
        """Test lazy import of get_logger."""
        from lexigram.logging import get_logger
        assert callable(get_logger)

    def test_import_logger_factory(self) -> None:
        """Test lazy import of LoggerFactoryProtocol."""
        from lexigram.logging import LoggerFactoryProtocol
        assert LoggerFactoryProtocol is not None

    def test_import_logger_factory_impl(self) -> None:
        """Test lazy import of LoggerFactoryImpl."""
        from lexigram.logging import LoggerFactoryImpl
        assert LoggerFactoryImpl is not None

    def test_import_logger_protocol(self) -> None:
        """Test lazy import of LoggerProtocol."""
        from lexigram.logging import LoggerProtocol
        assert LoggerProtocol is not None

    def test_import_logger_alias(self) -> None:
        """Test lazy import of Logger (alias for LoggerProtocol)."""
        from lexigram.logging import Logger
        assert Logger is not None

    def test_import_configure_logging(self) -> None:
        """Test lazy import of configure_logging."""
        from lexigram.logging import configure_logging
        assert callable(configure_logging)

    def test_import_apply_config(self) -> None:
        """Test lazy import of apply_config."""
        from lexigram.logging import apply_config
        assert callable(apply_config)

    def test_import_logging_config(self) -> None:
        """Test lazy import of LoggingConfig."""
        from lexigram.logging import LoggingConfig
        assert LoggingConfig is not None

    def test_import_logging_provider(self) -> None:
        """Test lazy import of LoggingProvider."""
        from lexigram.logging import LoggingProvider
        assert LoggingProvider is not None

    def test_import_log_level(self) -> None:
        """Test lazy import of LogLevel."""
        from lexigram.logging import LogLevel
        assert LogLevel is not None

    def test_import_critical(self) -> None:
        """Test lazy import of CRITICAL."""
        from lexigram.logging import CRITICAL
        assert CRITICAL is not None

    def test_import_debug(self) -> None:
        """Test lazy import of DEBUG."""
        from lexigram.logging import DEBUG
        assert DEBUG is not None

    def test_import_error(self) -> None:
        """Test lazy import of ERROR."""
        from lexigram.logging import ERROR
        assert ERROR is not None

    def test_import_info(self) -> None:
        """Test lazy import of INFO."""
        from lexigram.logging import INFO
        assert INFO is not None

    def test_import_warning(self) -> None:
        """Test lazy import of WARNING."""
        from lexigram.logging import WARNING
        assert WARNING is not None

    def test_import_query_log_entry(self) -> None:
        """Test lazy import of QueryLogEntry."""
        from lexigram.logging import QueryLogEntry
        assert QueryLogEntry is not None

    def test_import_query_logger_protocol(self) -> None:
        """Test lazy import of QueryLoggerProtocol."""
        from lexigram.logging import QueryLoggerProtocol
        assert QueryLoggerProtocol is not None


class TestLoggingDir:
    """Test __dir__ returns expected keys."""

    def test_dir_contains_expected(self) -> None:
        """Test __dir__ contains expected attributes."""
        from lexigram import logging
        attrs = dir(logging)
        assert "get_logger" in attrs
        assert "Logger" in attrs
        assert "LoggerFactoryProtocol" in attrs
        assert "LoggingConfig" in attrs


class TestLoggingAll:
    """Test __all__ exports."""

    def test_all_contains_expected(self) -> None:
        """Test __all__ contains expected items."""
        from lexigram import logging
        assert "get_logger" in logging.__all__
        assert "Logger" in logging.__all__
        assert "LoggerFactoryProtocol" in logging.__all__


class TestLoggingInvalidImport:
    """Test that invalid imports raise appropriate errors."""

    def test_invalid_attribute_raises(self) -> None:
        """Test that accessing invalid attribute raises AttributeError."""
        from lexigram import logging
        with pytest.raises(AttributeError):
            logging.nonexistent_attribute
