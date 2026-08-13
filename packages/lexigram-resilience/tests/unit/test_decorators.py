"""Tests for resilience decorators and helpers."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.contracts.infra.resilience import RetryConfig


class TestShouldRetry:
    """Test should_retry function from resilience module."""

    def test_max_attempts_exceeded(self) -> None:
        """Test retry returns false when max attempts reached."""
        from lexigram.resilience.decorators import should_retry

        config = RetryConfig(max_attempts=3)
        should, reason = should_retry(None, "result", 3, config)
        assert should is False
        assert reason == "max_attempts_exceeded"

    def test_abort_on_exception_type(self) -> None:
        """Test abort_on stops retry for specific exception."""
        from lexigram.resilience.decorators import should_retry

        config = RetryConfig(max_attempts=3, abort_on=(ValueError,))
        should, reason = should_retry(ValueError("test"), None, 0, config)
        assert should is False
        assert "abort_on" in reason

    def test_retry_on_allowed_exception(self) -> None:
        """Test retry allowed for exceptions not in abort_on."""
        from lexigram.resilience.decorators import should_retry

        config = RetryConfig(max_attempts=3, abort_on=(ValueError,))
        should, _ = should_retry(RuntimeError("test"), None, 0, config)
        assert should is True

    def test_abort_if_result(self) -> None:
        """Test abort_if stops retry based on result."""
        from lexigram.resilience.decorators import should_retry

        config = RetryConfig(max_attempts=3, abort_if=lambda r: r == "fail")
        should, reason = should_retry(None, "fail", 0, config)
        assert should is False
        assert "abort_if" in reason


class TestRetryDecorator:
    """Test retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_success(self) -> None:
        """Test successful call without retry."""
        from lexigram.resilience.decorators import retry

        call_count = 0

        @retry(RetryConfig(max_attempts=3))
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await succeed()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self) -> None:
        """Test retry on transient failure."""
        from lexigram.resilience.decorators import retry

        call_count = 0

        @retry(RetryConfig(max_attempts=3))
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "success"

        result = await flaky()
        assert result == "success"
        assert call_count == 3


class TestDecoratorsModuleExports:
    """Test decorators module exports."""

    def test_all_exports(self) -> None:
        """Test __all__ contains expected items."""
        from lexigram.resilience import decorators

        expected = [
            "bulkhead",
            "circuit_breaker",
            "circuit_breaker_sync",
            "calculate_delay",
            "idempotent",
            "retry",
            "should_retry",
            "with_timeout",
        ]
        assert sorted(decorators.__all__) == sorted(expected)