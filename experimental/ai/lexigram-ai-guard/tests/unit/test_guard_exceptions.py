"""Tests for guard exceptions."""

from __future__ import annotations

import pytest
from lexigram.ai.guard.exceptions import (
    GuardConfigurationError,
    GuardError,
    GuardPipelineError,
)


class TestGuardError:
    """Tests for base GuardError exception."""

    def test_guard_error_inherits_from_exception(self) -> None:
        assert issubclass(GuardError, Exception)

    def test_guard_error_can_be_raised(self) -> None:
        with pytest.raises(GuardError):
            raise GuardError("test message")

    def test_guard_error_message(self) -> None:
        error = GuardError("test message")
        assert error.message == "test message"
        assert "test message" in str(error)

    def test_guard_error_no_message(self) -> None:
        error = GuardError()
        assert error.message == "Guard error"


class TestGuardConfigurationError:
    """Tests for GuardConfigurationError exception."""

    def test_inherits_from_guard_error(self) -> None:
        assert issubclass(GuardConfigurationError, GuardError)

    def test_guard_configuration_error_can_be_raised(self) -> None:
        with pytest.raises(GuardConfigurationError):
            raise GuardConfigurationError("configuration is invalid")

    def test_guard_configuration_error_message(self) -> None:
        error = GuardConfigurationError("invalid threshold")
        assert error.message == "invalid threshold"
        assert "invalid threshold" in str(error)

    def test_guard_configuration_error_chaining(self) -> None:
        cause = ValueError("underlying cause")
        error = GuardConfigurationError("config error")
        error.__cause__ = cause
        assert error.__cause__ is cause


class TestGuardPipelineError:
    """Tests for GuardPipelineError exception."""

    def test_inherits_from_guard_error(self) -> None:
        assert issubclass(GuardPipelineError, GuardError)

    def test_guard_pipeline_error_can_be_raised(self) -> None:
        with pytest.raises(GuardPipelineError):
            raise GuardPipelineError("pipeline failed")

    def test_guard_pipeline_error_message(self) -> None:
        error = GuardPipelineError("execution failed")
        assert error.message == "execution failed"
        assert "execution failed" in str(error)

    def test_guard_pipeline_error_chaining(self) -> None:
        cause = RuntimeError("internal error")
        error = GuardPipelineError("pipeline error")
        error.__cause__ = cause
        assert error.__cause__ is cause


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_all_guards_can_be_caught_as_guard_error(self) -> None:
        """All guard exceptions should be catchable via GuardError."""
        with pytest.raises(GuardError):
            raise GuardConfigurationError("test")

        with pytest.raises(GuardError):
            raise GuardPipelineError("test")

    def test_exception_order_in_mro(self) -> None:
        """Verify correct Method Resolution Order for exceptions."""
        from lexigram.contracts.exceptions.base import LexigramError

        assert GuardError in GuardError.__mro__
        assert Exception in GuardError.__mro__
        assert LexigramError in GuardError.__mro__

        assert GuardConfigurationError in GuardConfigurationError.__mro__
        assert GuardError in GuardConfigurationError.__mro__
        assert LexigramError in GuardConfigurationError.__mro__

        assert GuardPipelineError in GuardPipelineError.__mro__
        assert GuardError in GuardPipelineError.__mro__
        assert LexigramError in GuardPipelineError.__mro__