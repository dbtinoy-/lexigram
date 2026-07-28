"""Tests for logging/redaction module."""
import pytest
from unittest.mock import patch, MagicMock

from lexigram.logging.redaction import (
    NoOpRedactor,
    get_redactor,
    set_redactor,
)


class TestNoOpRedactor:
    """Tests for NoOpRedactor class."""

    def test_redact_dict_passes_through(self) -> None:
        """Test redact_dict returns data unchanged."""
        redactor = NoOpRedactor()
        data = {"key": "value", "nested": {"inner": "data"}}
        result = redactor.redact_dict(data)
        assert result == data

    def test_redact_dict_empty_dict(self) -> None:
        """Test redact_dict with empty dict."""
        redactor = NoOpRedactor()
        result = redactor.redact_dict({})
        assert result == {}

    def test_redact_value_passes_through(self) -> None:
        """Test redact_value returns value unchanged."""
        redactor = NoOpRedactor()
        value = "sensitive password"
        result = redactor.redact_value(value)
        assert result == value

    def test_redact_value_none(self) -> None:
        """Test redact_value with None."""
        redactor = NoOpRedactor()
        result = redactor.redact_value(None)
        assert result is None

    def test_redact_value_list(self) -> None:
        """Test redact_value with list."""
        redactor = NoOpRedactor()
        value = [1, 2, 3]
        result = redactor.redact_value(value)
        assert result == value


class TestGetRedactor:
    """Tests for get_redactor function."""

    def test_get_redactor_returns_noop_by_default(self) -> None:
        """Test get_redactor returns NoOpRedactor when no override."""
        redactor = get_redactor()
        assert isinstance(redactor, NoOpRedactor)

    def test_get_redactor_with_context_override(self) -> None:
        """Test get_redactor returns context override when set."""
        custom_redactor = MagicMock()
        custom_redactor.redact_dict = lambda d: d
        custom_redactor.redact_value = lambda v: v
        
        token = set_redactor(custom_redactor)
        try:
            redactor = get_redactor()
            assert redactor is custom_redactor
        finally:
            from lexigram.logging.redaction import _redactor_var
            _redactor_var.reset(token)

    def test_get_redactor_after_reset_returns_noop(self) -> None:
        """Test get_redactor returns NoOpRedactor after token reset."""
        custom_redactor = MagicMock()
        custom_redactor.redact_dict = lambda d: d
        custom_redactor.redact_value = lambda v: v
        
        from lexigram.logging.redaction import _redactor_var
        token = set_redactor(custom_redactor)
        _redactor_var.reset(token)
        
        redactor = get_redactor()
        assert isinstance(redactor, NoOpRedactor)


class TestSetRedactor:
    """Tests for set_redactor function."""

    def test_set_redactor_returns_token(self) -> None:
        """Test set_redactor returns a token."""
        custom_redactor = MagicMock()
        token = set_redactor(custom_redactor)
        
        # Token should be used for reset
        from lexigram.logging.redaction import _redactor_var
        _redactor_var.reset(token)
        
        assert token is not None


class TestModuleExports:
    """Tests for module exports."""

    def test_noop_redactor_exported(self) -> None:
        """Test NoOpRedactor is exported."""
        from lexigram.logging.redaction import NoOpRedactor
        assert NoOpRedactor is not None

    def test_get_redactor_exported(self) -> None:
        """Test get_redactor is exported."""
        from lexigram.logging.redaction import get_redactor
        assert callable(get_redactor)

    def test_set_redactor_exported(self) -> None:
        """Test set_redactor is exported."""
        from lexigram.logging.redaction import set_redactor
        assert callable(set_redactor)