"""Tests for resilience constants."""

from __future__ import annotations

import pytest

from lexigram.resilience import constants


class TestResilienceConstants:
    """Test resilience constants are properly defined."""

    def test_version_defined(self) -> None:
        """Test __version__ is defined."""
        assert constants.__version__ is not None
        assert isinstance(constants.__version__, str)

    def test_env_prefix(self) -> None:
        """Test environment variable prefix."""
        assert constants.ENV_PREFIX == "LEX_RESILIENCE__"
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_retry_defaults(self) -> None:
        """Test retry default values."""
        assert constants.DEFAULT_RETRY_ATTEMPTS == 3
        assert constants.DEFAULT_RETRY_DELAY == 1.0

    def test_circuit_breaker_defaults(self) -> None:
        """Test circuit breaker defaults."""
        assert constants.DEFAULT_CB_FAILURE_THRESHOLD == 5
        assert constants.DEFAULT_CB_RECOVERY_TIMEOUT == 60.0

    def test_bulkhead_defaults(self) -> None:
        """Test bulkhead defaults."""
        assert constants.DEFAULT_BULKHEAD_MAX_CONCURRENT == 10

    def test_rate_limiter_defaults(self) -> None:
        """Test rate limiter defaults."""
        assert constants.DEFAULT_RATE_LIMIT_WINDOW == 60.0

    def test_timeout_defaults(self) -> None:
        """Test timeout defaults."""
        assert constants.DEFAULT_TIMEOUT == 30.0


class TestIdempotencyConstants:
    """Test merged idempotency constants."""

    def test_idempotency_defaults(self) -> None:
        """Test idempotency default values."""
        assert constants.DEFAULT_CLEANUP_INTERVAL == 300.0
        assert constants.DEFAULT_KEY_PREFIX == "idempotency:"
        assert constants.DEFAULT_MAX_ENTRIES == 10000
        assert constants.DEFAULT_MAX_KEY_LENGTH == 256
        assert constants.DEFAULT_TTL == 3600


class TestConstantsAllExports:
    """Test __all__ contains expected constants."""

    def test_all_contains_expected(self) -> None:
        """Test __all__ is complete."""
        expected = [
            "DEFAULT_BULKHEAD_MAX_CONCURRENT",
            "DEFAULT_CB_FAILURE_THRESHOLD",
            "DEFAULT_CB_RECOVERY_TIMEOUT",
            "DEFAULT_CLEANUP_INTERVAL",
            "DEFAULT_KEY_PREFIX",
            "DEFAULT_MAX_ENTRIES",
            "DEFAULT_MAX_KEY_LENGTH",
            "DEFAULT_RATE_LIMIT_WINDOW",
            "DEFAULT_RETRY_ATTEMPTS",
            "DEFAULT_RETRY_DELAY",
            "DEFAULT_TTL",
            "DEFAULT_TIMEOUT",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
        ]
        assert sorted(constants.__all__) == sorted(expected)