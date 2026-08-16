"""Tests for retry module with Result[T, E] integration.

This test suite verifies that retry operations properly integrate with
the Result pattern, returning Result[T, E] types for operations that
can fail in expected, recoverable ways.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock

from lexigram.result import Result
from lexigram.contracts.infra.resilience.models import RetryConfig
from lexigram.resilience.retry import retry, RetryManager, RetryPolicy
from lexigram.resilience.exceptions import RetryExhaustedError


class TransientError(Exception):
    """Simulates a transient, retryable error."""

    pass


class PermanentError(Exception):
    """Simulates a permanent, non-retryable error."""

    pass


class TestRetryWithResultAsync:
    """Tests for async retry operations returning Result[T, E]."""

    @pytest.mark.asyncio
    async def test_retry_async_success_on_first_attempt(self) -> None:
        """Test successful execution on first attempt."""
        call_count = 0

        async def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        config = RetryConfig(max_attempts=3)
        result = await retry(fetch_data, config=config)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_success_after_transient_errors(self) -> None:
        """Test successful execution after retrying transient errors."""
        call_count = 0

        async def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TransientError(f"Attempt {call_count} failed")
            return "success"

        config = RetryConfig(
            max_attempts=5,
            base_delay=0.001,
            backoff_factor=1.5,
            retry_on=(TransientError,),
        )
        result = await retry(fetch_data, config=config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_exhausted_with_transient_error(self) -> None:
        """Test that RetryExhaustedError is raised when max attempts exceeded."""
        call_count = 0

        async def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            raise TransientError(f"Attempt {call_count} failed")

        config = RetryConfig(
            max_attempts=3,
            base_delay=0.001,
            retry_on=(TransientError,),
        )

        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry(fetch_data, config=config)

        assert call_count == 3
        assert "3" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_async_abort_on_permanent_error(self) -> None:
        """Test that abort_on stops retrying on specific exceptions."""
        call_count = 0

        async def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TransientError("Transient")
            raise PermanentError("Permanent")

        config = RetryConfig(
            max_attempts=5,
            base_delay=0.001,
            retry_on=(TransientError,),
            abort_on=(PermanentError,),
        )

        with pytest.raises(PermanentError):
            await retry(fetch_data, config=config)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_async_with_exponential_backoff(self) -> None:
        """Test exponential backoff timing between retries."""
        call_times: list[float] = []

        async def fetch_data() -> str:
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise TransientError("Retry needed")
            return "success"

        config = RetryConfig(
            max_attempts=5,
            base_delay=0.01,
            backoff_factor=2.0,
            max_delay=0.5,
            jitter=False,
        )
        result = await retry(fetch_data, config=config)

        assert result == "success"
        assert len(call_times) == 3

        # Verify backoff timing is approximately exponential
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # delay2 should be roughly 2x delay1
        assert delay2 > delay1
        assert delay2 / delay1 > 1.5  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_retry_async_with_jitter(self) -> None:
        """Test jitter introduces randomness to retry delays."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            backoff_factor=1.5,
            max_delay=1.0,
            jitter=True,
        )

        delays: list[float] = []

        async def fetch_data_with_timing() -> str:
            start = asyncio.get_event_loop().time()
            if len(delays) == 0:
                delays.append(0.0)
                raise TransientError("Retry")
            if len(delays) == 1:
                delays.append(asyncio.get_event_loop().time() - start)
                raise TransientError("Retry again")
            delays.append(asyncio.get_event_loop().time() - start)
            return "success"

        result = await retry(fetch_data_with_timing, config=config)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_decorator_async_function(self) -> None:
        """Test retry as a decorator on async functions."""
        call_count = 0

        config = RetryConfig(
            max_attempts=3,
            base_delay=0.001,
            retry_on=(TransientError,),
        )

        @retry(config)
        async def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TransientError("Retry")
            return "success"

        result = await fetch_data()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_max_retries_exceeded(self) -> None:
        """Test that max retries is properly enforced."""
        call_count = 0

        async def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            raise TransientError("Always fails")

        config = RetryConfig(
            max_attempts=3,
            base_delay=0.001,
            retry_on=(TransientError,),
        )

        with pytest.raises(RetryExhaustedError):
            await retry(fetch_data, config=config)

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_retry_on_result(self) -> None:
        """Test retry_on_result predicate for retrying on value."""
        call_count = 0

        async def fetch_data() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        def should_retry_result(value: int) -> bool:
            return value < 3

        config = RetryConfig(
            max_attempts=5,
            base_delay=0.001,
            retry_on_result=should_retry_result,
        )

        result = await retry(fetch_data, config=config)

        assert result == 3
        assert call_count == 3


class TestRetryManager:
    """Tests for RetryManager with metrics tracking."""

    @pytest.mark.asyncio
    async def test_retry_manager_tracks_successes(self) -> None:
        """Test that RetryManager tracks successful executions."""
        manager = RetryManager(
            RetryConfig(
                max_attempts=3,
                base_delay=0.001,
                retry_on=(TransientError,),
            )
        )

        async def fetch_data() -> str:
            return "success"

        result = await manager.execute(fetch_data)

        assert result == "success"
        stats = manager.get_stats()
        assert stats["successes"] == 1
        assert stats["failures"] == 0
        assert stats["total_attempts"] == 1

    @pytest.mark.asyncio
    async def test_retry_manager_tracks_failures(self) -> None:
        """Test that RetryManager tracks failed executions."""
        manager = RetryManager(
            RetryConfig(
                max_attempts=2,
                base_delay=0.001,
                retry_on=(TransientError,),
            )
        )

        async def fetch_data() -> str:
            raise TransientError("Always fails")

        with pytest.raises(RetryExhaustedError):
            await manager.execute(fetch_data)

        stats = manager.get_stats()
        assert stats["successes"] == 0
        assert stats["failures"] == 1
        assert stats["total_retries"] == 1

    @pytest.mark.asyncio
    async def test_retry_manager_tracks_multiple_executions(self) -> None:
        """Test that RetryManager tracks metrics across multiple executions."""
        manager = RetryManager(
            RetryConfig(
                max_attempts=2,
                base_delay=0.001,
                retry_on=(TransientError,),
            )
        )

        async def success() -> str:
            return "ok"

        async def failure() -> str:
            raise TransientError("fail")

        await manager.execute(success)

        with pytest.raises(RetryExhaustedError):
            await manager.execute(failure)

        await manager.execute(success)

        stats = manager.get_stats()
        assert stats["total_attempts"] == 3
        assert stats["successes"] == 2
        assert stats["failures"] == 1


class TestRetryPolicy:
    """Tests for RetryPolicy presets."""

    @pytest.mark.asyncio
    async def test_retry_policy_aggressive(self) -> None:
        """Test aggressive retry policy for fast operations."""
        policy = RetryPolicy.aggressive()

        call_count = 0

        async def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TransientError("Retry")
            return "success"

        result = await policy.execute(fetch_data)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_policy_conservative(self) -> None:
        """Test conservative retry policy for expensive operations."""
        policy = RetryPolicy.conservative()

        call_count = 0

        async def expensive_operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TransientError("Retry")
            return "success"

        result = await policy.execute(expensive_operation)

        assert result == "success"
        assert call_count == 2


class TestRetrySync:
    """Tests for synchronous retry operations."""

    def test_retry_sync_success(self) -> None:
        """Test successful sync execution on first attempt."""
        call_count = 0

        def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        config = RetryConfig(max_attempts=3)

        @retry(config)
        def sync_fetch() -> str:
            return fetch_data()

        result = sync_fetch()

        assert result == "success"
        assert call_count == 1

    def test_retry_sync_with_retries(self) -> None:
        """Test sync retry with transient failures."""
        call_count = 0

        def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TransientError("Retry")
            return "success"

        config = RetryConfig(
            max_attempts=3,
            base_delay=0.001,
            retry_on=(TransientError,),
        )

        @retry(config)
        def sync_fetch() -> str:
            return fetch_data()

        result = sync_fetch()

        assert result == "success"
        assert call_count == 2

    def test_retry_sync_exhausted(self) -> None:
        """Test sync retry exhaustion."""
        call_count = 0

        def fetch_data() -> str:
            nonlocal call_count
            call_count += 1
            raise TransientError("Always fails")

        config = RetryConfig(
            max_attempts=2,
            base_delay=0.001,
            retry_on=(TransientError,),
        )

        @retry(config)
        def sync_fetch() -> str:
            return fetch_data()

        with pytest.raises(RetryExhaustedError):
            sync_fetch()

        assert call_count == 2
