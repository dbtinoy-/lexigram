"""Tests for retry module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lexigram.contracts.infra.resilience.models import RetryConfig
from lexigram.resilience.retry import (
    RetryPolicy,
    retry,
)
from lexigram.resilience.exceptions import RetryExhaustedError


# Import internal functions for testing
from lexigram.resilience.retry.retry import (
    calculate_delay,
    should_retry,
    RetryManager,
)


class TestCalculateDelay:
    """Tests for calculate_delay function."""

    def test_exponential_backoff(self) -> None:
        """Test exponential backoff calculation."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0,
            jitter=False,
        )
        
        # First attempt: 1.0 * 2^0 = 1.0
        delay = calculate_delay(0, config)
        assert delay == 1.0
        
        # Second attempt: 1.0 * 2^1 = 2.0
        delay = calculate_delay(1, config)
        assert delay == 2.0
        
        # Third attempt: 1.0 * 2^2 = 4.0
        delay = calculate_delay(2, config)
        assert delay == 4.0

    def test_max_delay_cap(self) -> None:
        """Test that max_delay caps the delay."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_factor=10.0,
            max_delay=5.0,
            jitter=False,
        )
        
        # Should be capped at 5.0
        delay = calculate_delay(3, config)
        assert delay == 5.0

    def test_jitter_enabled(self) -> None:
        """Test jitter is applied when enabled."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_factor=1.0,
            max_delay=10.0,
            jitter=True,
        )
        
        # With jitter, delay should vary
        delays = [calculate_delay(0, config) for _ in range(10)]
        # All should be non-negative
        assert all(d >= 0.0 for d in delays)

    def test_jitter_factor(self) -> None:
        """Test custom jitter factor."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_factor=1.0,
            max_delay=10.0,
            jitter=0.5,
        )
        
        delay = calculate_delay(0, config)
        # Should not exceed max_delay
        assert delay <= 10.0


class TestShouldRetry:
    """Tests for should_retry function."""

    def test_max_attempts_exceeded(self) -> None:
        """Test that retry returns False when max attempts exceeded."""
        config = RetryConfig(max_attempts=3)
        
        should, reason = should_retry(None, None, 2, config)
        assert should is False
        assert reason == "max_attempts_exceeded"

    def test_abort_on_specific_exception(self) -> None:
        """Test abort_on stops retry for specific exceptions."""
        config = RetryConfig(max_attempts=5, abort_on=(ValueError,))
        
        error = ValueError("test")
        should, reason = should_retry(error, None, 0, config)
        assert should is False
        assert "abort_on" in reason

    def test_abort_if_result(self) -> None:
        """Test abort_if stops retry based on result."""
        config = RetryConfig(max_attempts=5, abort_if=lambda r: r == "fail")
        
        should, reason = should_retry(None, "fail", 0, config)
        assert should is False
        assert "abort_if" in reason

    def test_retry_on_result(self) -> None:
        """Test retry_on_result triggers retry for specific results."""
        config = RetryConfig(max_attempts=5, retry_on_result=lambda r: r == "retry")
        
        should, reason = should_retry(None, "retry", 0, config)
        assert should is True
        assert reason == "retry_on_result"

    def test_retry_on_result_not_matching(self) -> None:
        """Test retry_on_result returns False when result doesn't match."""
        config = RetryConfig(max_attempts=5, retry_on_result=lambda r: r == "retry")
        
        should, reason = should_retry(None, "success", 0, config)
        assert should is False
        assert reason == "result_not_retryable"

    def test_exception_not_in_retry_on(self) -> None:
        """Test exception not in retry_on list."""
        config = RetryConfig(max_attempts=5, retry_on=(ValueError,))
        
        error = TypeError("test")
        should, reason = should_retry(error, None, 0, config)
        assert should is False
        assert "exception_not_in_retry_on" in reason

    def test_retry_if_returns_false(self) -> None:
        """Test retry_if callback returning False."""
        config = RetryConfig(
            max_attempts=5,
            retry_on=(Exception,),
            retry_if=lambda e: False,
        )
        
        error = Exception("test")
        should, reason = should_retry(error, None, 0, config)
        assert should is False
        assert reason == "retry_if_returned_false"

    def test_default_retry(self) -> None:
        """Test default retry behavior."""
        config = RetryConfig(max_attempts=5, retry_on=(Exception,))
        
        error = Exception("test")
        should, reason = should_retry(error, None, 0, config)
        assert should is True
        assert reason == "default"


class TestRetryDecorator:
    """Tests for retry decorator."""

    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self) -> None:
        """Test successful execution without retries."""
        call_count = 0
        
        @retry(RetryConfig(max_attempts=3))
        async def success() -> str:
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self) -> None:
        """Test retry on failure."""
        call_count = 0
        
        @retry(RetryConfig(max_attempts=3))
        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"
        
        result = await flaky()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self) -> None:
        """Test that RetryExhaustedError is raised when retries exhausted."""
        @retry(RetryConfig(max_attempts=2))
        async def always_fail() -> str:
            raise ValueError("fail")
        
        with pytest.raises(RetryExhaustedError):
            await always_fail()


class TestRetryManager:
    """Tests for RetryManager class."""

    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        """Test successful execution tracks metrics."""
        manager = RetryManager(config=RetryConfig(max_attempts=3))
        
        async def success() -> str:
            return "success"
        
        result = await manager.execute(success)
        assert result == "success"
        assert manager.total_attempts == 1
        assert manager.total_successes == 1
        assert manager.total_failures == 0

    @pytest.mark.asyncio
    async def test_failed_execution(self) -> None:
        """Test failed execution tracks metrics."""
        manager = RetryManager(config=RetryConfig(max_attempts=1))
        
        async def fail() -> str:
            raise ValueError("fail")
        
        with pytest.raises(RetryExhaustedError):
            await manager.execute(fail)
        
        assert manager.total_attempts == 1
        assert manager.total_successes == 0
        assert manager.total_failures == 1


class TestRetryPolicy:
    """Tests for RetryPolicy class."""

    def test_initialization(self) -> None:
        """Test RetryPolicy initialization."""
        config = RetryConfig(max_attempts=3)
        policy = RetryPolicy(config)
        
        assert policy.config == config

    @pytest.mark.asyncio
    async def test_execute(self) -> None:
        """Test RetryPolicy execute method."""
        config = RetryConfig(max_attempts=3)
        policy = RetryPolicy(config)
        
        async def success() -> str:
            return "success"
        
        result = await policy.execute(success)
        assert result == "success"
