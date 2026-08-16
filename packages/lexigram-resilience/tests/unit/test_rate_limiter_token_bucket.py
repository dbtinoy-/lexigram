"""Tests for TokenBucket rate limiter."""

import asyncio
import pytest
import time

from lexigram.resilience.rate_limiter import TokenBucket


class TestTokenBucketInit:
    """Tests for TokenBucket initialization."""

    def test_init_default_tokens(self) -> None:
        """Test initialization with default initial tokens."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.capacity == 10.0
        assert bucket.refill_rate == 1.0
        assert bucket.available_tokens == 10.0

    def test_init_custom_tokens(self) -> None:
        """Test initialization with custom initial tokens."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0, initial_tokens=5.0)
        assert bucket.available_tokens == 5.0

    def test_init_zero_capacity(self) -> None:
        """Test initialization with zero capacity."""
        bucket = TokenBucket(capacity=0.0, refill_rate=1.0)
        assert bucket.capacity == 0.0
        assert bucket.available_tokens == 0.0

    def test_init_float_capacity(self) -> None:
        """Test initialization with float capacity."""
        bucket = TokenBucket(capacity=10.5, refill_rate=2.5)
        assert bucket.capacity == 10.5
        assert bucket.refill_rate == 2.5


class TestTokenBucketAcquire:
    """Tests for acquire method."""

    @pytest.mark.asyncio
    async def test_acquire_single_token(self) -> None:
        """Test acquiring single token."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        await bucket.acquire(1)
        assert bucket.available_tokens == 9.0

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self) -> None:
        """Test acquiring multiple tokens."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        await bucket.acquire(3)
        assert bucket.available_tokens == 7.0

    @pytest.mark.asyncio
    async def test_acquire_exceeding_capacity_raises(self) -> None:
        """Test that acquiring more than capacity raises ValueError."""
        bucket = TokenBucket(capacity=5.0, refill_rate=1.0)
        with pytest.raises(ValueError, match="Cannot acquire more tokens"):
            await bucket.acquire(10)

    @pytest.mark.asyncio
    async def test_acquire_exactly_capacity(self) -> None:
        """Test acquiring exactly capacity tokens."""
        bucket = TokenBucket(capacity=5.0, refill_rate=1.0)
        await bucket.acquire(5)
        assert bucket.available_tokens == 0.0


class TestTokenBucketTryAcquire:
    """Tests for try_acquire method."""

    @pytest.mark.asyncio
    async def test_try_acquire_success(self) -> None:
        """Test successful try_acquire."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        result = await bucket.try_acquire(1)
        assert result is True
        assert bucket.available_tokens == 9.0

    @pytest.mark.asyncio
    async def test_try_acquire_insufficient_tokens(self) -> None:
        """Test try_acquire with insufficient tokens."""
        bucket = TokenBucket(capacity=2.0, refill_rate=1.0)
        result = await bucket.try_acquire(5)
        assert result is False
        assert bucket.available_tokens == 2.0

    @pytest.mark.asyncio
    async def test_try_acquire_exact_capacity(self) -> None:
        """Test try_acquire with exact capacity."""
        bucket = TokenBucket(capacity=5.0, refill_rate=1.0)
        result = await bucket.try_acquire(5)
        assert result is True
        assert bucket.available_tokens == 0.0


class TestTokenBucketRefill:
    """Tests for token refill behavior."""

    @pytest.mark.asyncio
    async def test_tokens_refill_over_time(self) -> None:
        """Test that tokens refill over time."""
        bucket = TokenBucket(capacity=10.0, refill_rate=10.0, initial_tokens=0.0)
        await bucket.try_acquire(1)
        assert bucket.available_tokens < 1.0
        await asyncio.sleep(0.2)
        result = await bucket.try_acquire(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_tokens_capped_at_capacity(self) -> None:
        """Test that tokens don't exceed capacity."""
        bucket = TokenBucket(capacity=10.0, refill_rate=100.0, initial_tokens=0.0)
        await asyncio.sleep(0.2)
        assert bucket.available_tokens <= 10.0


class TestTokenBucketConcurrency:
    """Tests for concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self) -> None:
        """Test concurrent acquire operations."""
        bucket = TokenBucket(capacity=100.0, refill_rate=1000.0)

        async def acquire_tokens(n: int) -> None:
            for _ in range(n):
                await bucket.acquire(1)

        await asyncio.gather(acquire_tokens(10), acquire_tokens(10), acquire_tokens(10))
        assert bucket.available_tokens >= 69.0


class TestTokenBucketAvailableTokens:
    """Tests for available_tokens property."""

    def test_available_tokens_returns_float(self) -> None:
        """Test available_tokens returns float."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert isinstance(bucket.available_tokens, float)

    def test_available_tokens_initial(self) -> None:
        """Test available_tokens initial value."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0, initial_tokens=7.5)
        assert bucket.available_tokens == 7.5
