"""Tests for feature flags exceptions."""

from __future__ import annotations

import pytest

from lexigram.features.exceptions import (
    FeatureFlagDisabledError,
    FeatureFlagError,
    FlagEvaluationError,
    FlagNotFoundError,
)


class TestFeatureFlagError:
    """Tests for the base FeatureFlagError exception."""

    def test_is_exception(self) -> None:
        """FeatureFlagError should be an Exception."""
        error = FeatureFlagError()
        assert isinstance(error, Exception)

    def test_default_message(self) -> None:
        """Should work with default message."""
        error = FeatureFlagError()
        # Exception message is accessible via str()
        assert isinstance(str(error), str)


class TestFlagNotFoundError:
    """Tests for FlagNotFoundError."""

    def test_creation(self) -> None:
        """Should create with flag key."""
        error = FlagNotFoundError("my-flag")
        assert error.flag_key == "my-flag"

    def test_message_format(self) -> None:
        """Should include flag key in message."""
        error = FlagNotFoundError("test-flag")
        assert "test-flag" in str(error)

    def test_is_exception(self) -> None:
        """Should inherit from Exception."""
        error = FlagNotFoundError("test")
        assert isinstance(error, Exception)


class TestFeatureFlagDisabledError:
    """Tests for FeatureFlagDisabledError."""

    def test_creation(self) -> None:
        """Should create with flag name."""
        error = FeatureFlagDisabledError("dark-mode")
        assert error.flag_name == "dark-mode"

    def test_message_format(self) -> None:
        """Should include flag name in message."""
        error = FeatureFlagDisabledError("new-feature")
        assert "new-feature" in str(error)

    def test_is_exception(self) -> None:
        """Should inherit from Exception."""
        error = FeatureFlagDisabledError("test")
        assert isinstance(error, Exception)


class TestFlagEvaluationError:
    """Tests for FlagEvaluationError."""

    def test_creation_with_default_message(self) -> None:
        """Should create with flag key and default message."""
        error = FlagEvaluationError("my-flag")
        assert error.flag_key == "my-flag"
        assert "my-flag" in str(error)
        assert "Flag evaluation failed" in str(error)

    def test_creation_with_custom_message(self) -> None:
        """Should create with flag key and custom message."""
        error = FlagEvaluationError("test-flag", message="Custom error")
        assert error.flag_key == "test-flag"
        assert "Custom error" in str(error)

    def test_is_exception(self) -> None:
        """Should inherit from Exception."""
        error = FlagEvaluationError("test")
        assert isinstance(error, Exception)
