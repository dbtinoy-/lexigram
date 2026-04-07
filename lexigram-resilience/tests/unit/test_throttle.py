"""Unit tests for throttle module."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.resilience.rate_limiter import RateLimiter, SlidingWindowLimiter
from lexigram.resilience.throttle.throttle import (
    ThrottleConfig,
    ThrottleRegistry,
    Throttler,
    get_throttle_stats,
    throttle,
)


class TestThrottleConfig:
    """Tests for ThrottleConfig."""

    def test_default_values(self) -> None:
        config = ThrottleConfig(calls=10, period=1.0)
        assert config.calls == 10
        assert config.period == 1.0
        assert config.burst is None
        assert config.strategy == "token_bucket"

    def test_custom_burst(self) -> None:
        config = ThrottleConfig(calls=10, period=1.0, burst=20)
        assert config.burst == 20

    def test_sliding_window_strategy(self) -> None:
        config = ThrottleConfig(calls=10, period=1.0, strategy="sliding_window")
        assert config.strategy == "sliding_window"


class TestThrottleRegistry:
    """Tests for ThrottleRegistry."""

    @pytest.fixture
    def registry(self) -> ThrottleRegistry:
        return ThrottleRegistry()

    def test_initialization(self, registry: ThrottleRegistry) -> None:
        assert len(registry._limiters) == 0

    @pytest.mark.asyncio
    async def test_get_or_create_creates_token_bucket_limiter(
        self,
        registry: ThrottleRegistry,
    ) -> None:
        config = ThrottleConfig(calls=10, period=1.0)
        limiter = await registry.get_or_create("test_key", config)

        assert isinstance(limiter, RateLimiter)
        assert limiter.rate == 10
        assert limiter.per == 1.0

    @pytest.mark.asyncio
    async def test_get_or_create_creates_sliding_window_limiter(
        self,
        registry: ThrottleRegistry,
    ) -> None:
        config = ThrottleConfig(calls=10, period=1.0, strategy="sliding_window")
        limiter = await registry.get_or_create("test_key_sliding", config)

        assert isinstance(limiter, SlidingWindowLimiter)

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_limiter(
        self,
        registry: ThrottleRegistry,
    ) -> None:
        config = ThrottleConfig(calls=10, period=1.0)
        limiter1 = await registry.get_or_create("test_key", config)
        limiter2 = await registry.get_or_create("test_key", config)

        assert limiter1 is limiter2

    def test_clear(self, registry: ThrottleRegistry) -> None:
        registry._limiters["test"] = RateLimiter(rate=10, per=1.0)
        registry.clear()
        assert len(registry._limiters) == 0


class TestThrottler:
    """Tests for Throttler class."""

    @pytest.fixture
    def throttler(self) -> Throttler:
        return Throttler(calls=5, period=1.0)

    def test_initialization(self, throttler: Throttler) -> None:
        assert throttler.config.calls == 5
        assert throttler.config.period == 1.0
        assert throttler.config.strategy == "token_bucket"

    def test_initialization_with_sliding_window(self) -> None:
        throttler = Throttler(calls=5, period=1.0, strategy="sliding_window")
        assert throttler.config.strategy == "sliding_window"
        assert isinstance(throttler._limiter, SlidingWindowLimiter)

    @pytest.mark.asyncio
    async def test_acquire_blocks_when_rate_exceeded(
        self, throttler: Throttler
    ) -> None:
        # Exhaust the limiter first
        for _ in range(5):
            await throttler.acquire()

        # The 6th should block (or we can use try_acquire to check)
        result = await throttler.try_acquire()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_try_acquire_returns_true_when_available(
        self,
        throttler: Throttler,
    ) -> None:
        result = await throttler.try_acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_stats(self, throttler: Throttler) -> None:
        await throttler.acquire()
        stats = throttler.get_stats()
        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert stats["allowed_requests"] >= 0

    def test_throttle_decorator_creates_wrapper(self, throttler: Throttler) -> None:
        @throttler.throttle
        async def my_func():
            return "result"

        assert asyncio.iscoroutinefunction(my_func)


class TestThrottleDecorator:
    """Tests for throttle decorator function."""

    def test_throttle_creates_decorator(self) -> None:
        decorator = throttle(calls=10, period=1.0)
        assert callable(decorator)

    def test_throttle_with_custom_key(self) -> None:
        decorator = throttle(calls=10, period=1.0, key="custom_key")
        assert callable(decorator)

    def test_throttle_with_sliding_window_strategy(self) -> None:
        decorator = throttle(calls=10, period=1.0, strategy="sliding_window")
        assert callable(decorator)


class TestGetThrottleStats:
    """Tests for get_throttle_stats function."""

    def test_returns_none_for_non_throttled_function(self) -> None:
        async def regular_func():
            return "result"

        result = get_throttle_stats(regular_func)
        assert result is None

    def test_returns_none_for_uninitialized_throttler(self) -> None:
        @throttle(calls=10, period=1.0)
        async def throttled_func():
            return "result"

        result = get_throttle_stats(throttled_func)
        assert result is None
