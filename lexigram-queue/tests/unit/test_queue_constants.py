"""Unit tests for queue constants."""

from __future__ import annotations

import pytest

from lexigram.queue import constants


class TestConstants:
    """Tests for lexigram-queue constants."""

    def test_version_is_string(self) -> None:
        """Verify __version__ is a string."""
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        """Verify version matches expected format."""
        version = constants.__version__
        parts = version.split(".")
        assert len(parts) >= 3
        for part in parts:
            assert part.isdigit()

    def test_env_prefix(self) -> None:
        """Verify ENV_PREFIX value."""
        assert constants.ENV_PREFIX == "LEX_QUEUE__"

    def test_env_nested_delimiter(self) -> None:
        """Verify ENV_NESTED_DELIMITER value."""
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_default_consumer_concurrency(self) -> None:
        """Verify DEFAULT_CONSUMER_CONCURRENCY is a positive int."""
        assert isinstance(constants.DEFAULT_CONSUMER_CONCURRENCY, int)
        assert constants.DEFAULT_CONSUMER_CONCURRENCY > 0

    def test_default_consumer_prefetch(self) -> None:
        """Verify DEFAULT_CONSUMER_PREFETCH is a positive int."""
        assert isinstance(constants.DEFAULT_CONSUMER_PREFETCH, int)
        assert constants.DEFAULT_CONSUMER_PREFETCH > 0

    def test_default_max_retries(self) -> None:
        """Verify DEFAULT_MAX_RETRIES is a non-negative int."""
        assert isinstance(constants.DEFAULT_MAX_RETRIES, int)
        assert constants.DEFAULT_MAX_RETRIES >= 0

    def test_default_visibility_timeout(self) -> None:
        """Verify DEFAULT_VISIBILITY_TIMEOUT is a positive int."""
        assert isinstance(constants.DEFAULT_VISIBILITY_TIMEOUT, int)
        assert constants.DEFAULT_VISIBILITY_TIMEOUT > 0

    def test_constants_are_exported(self) -> None:
        """Verify all expected constants are in __all__."""
        expected = [
            "DEFAULT_CONSUMER_CONCURRENCY",
            "DEFAULT_CONSUMER_PREFETCH",
            "DEFAULT_MAX_RETRIES",
            "DEFAULT_VISIBILITY_TIMEOUT",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
        ]
        assert constants.__all__ == expected