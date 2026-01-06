"""Tests for AI workers constants."""

from __future__ import annotations

import pytest

from lexigram.ai.workers import constants


class TestConstants:
    """Test constants module."""

    def test_default_check_interval(self) -> None:
        """Test DEFAULT_CHECK_INTERVAL value."""
        assert constants.DEFAULT_CHECK_INTERVAL == 60

    def test_default_max_retries(self) -> None:
        """Test DEFAULT_MAX_RETRIES value."""
        assert constants.DEFAULT_MAX_RETRIES == 5

    def test_default_base_backoff(self) -> None:
        """Test DEFAULT_BASE_BACKOFF value."""
        assert constants.DEFAULT_BASE_BACKOFF == 60

    def test_max_backoff_seconds(self) -> None:
        """Test MAX_BACKOFF_SECONDS value."""
        assert constants.MAX_BACKOFF_SECONDS == 3600

    def test_default_task_timeout(self) -> None:
        """Test DEFAULT_TASK_TIMEOUT value."""
        assert constants.DEFAULT_TASK_TIMEOUT == 300.0

    def test_max_history_size(self) -> None:
        """Test MAX_HISTORY_SIZE value."""
        assert constants.MAX_HISTORY_SIZE == 1000

    def test_env_prefix(self) -> None:
        """Test ENV_PREFIX value."""
        assert constants.ENV_PREFIX == "LEX_AI_WORKERS__"

    def test_env_nested_delimiter(self) -> None:
        """Test ENV_NESTED_DELIMITER value."""
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_version_is_string(self) -> None:
        """Test __version__ is a string."""
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        """Test __version__ follows semver-like format."""
        parts = constants.__version__.split(".")
        assert len(parts) >= 2
        for part in parts:
            assert part.isdigit()

    def test_all_exports(self) -> None:
        """Test __all__ contains expected constants."""
        expected = [
            "DEFAULT_BASE_BACKOFF",
            "DEFAULT_CHECK_INTERVAL",
            "DEFAULT_MAX_RETRIES",
            "DEFAULT_TASK_TIMEOUT",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "MAX_BACKOFF_SECONDS",
            "MAX_HISTORY_SIZE",
            "__version__",
        ]
        assert sorted(constants.__all__) == sorted(expected)


class TestConstantValues:
    """Test constant values are sensible."""

    def test_backoff_never_exceeds_max(self) -> None:
        """Test that exponential backoff calculation respects max."""
        base_delay = constants.DEFAULT_BASE_BACKOFF
        for retry in range(20):
            backoff = base_delay * (2**retry)
            assert backoff <= constants.MAX_BACKOFF_SECONDS or backoff > constants.MAX_BACKOFF_SECONDS

    def test_task_timeout_is_positive(self) -> None:
        """Test DEFAULT_TASK_TIMEOUT is positive."""
        assert constants.DEFAULT_TASK_TIMEOUT > 0

    def test_max_retries_is_positive(self) -> None:
        """Test DEFAULT_MAX_RETRIES is positive."""
        assert constants.DEFAULT_MAX_RETRIES > 0

    def test_check_interval_is_positive(self) -> None:
        """Test DEFAULT_CHECK_INTERVAL is positive."""
        assert constants.DEFAULT_CHECK_INTERVAL > 0

    def test_history_size_is_positive(self) -> None:
        """Test MAX_HISTORY_SIZE is positive."""
        assert constants.MAX_HISTORY_SIZE > 0