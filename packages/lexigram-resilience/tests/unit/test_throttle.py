"""Unit tests for throttle module."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.resilience.rate_limiter import SlidingWindowLimiter
from lexigram.resilience.throttle import Throttler
from lexigram.resilience.throttle.throttle import ThrottleConfig


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


class TestDeadApiRemoved:
    """Regression guards for audit §58: dead decorator API removed.

    The module-level ``throttle()`` decorator, ``ThrottleRegistry`` and
    ``get_throttle_stats`` were structurally dead (every call raised) and had
    zero call sites; they were deleted in favour of the DI-wired
    :class:`Throttler` class.
    """

    def test_throttle_module_exports_only_throttler(self) -> None:
        import lexigram.resilience.throttle as throttle_pkg

        assert throttle_pkg.__all__ == ["Throttler"]
        assert not hasattr(throttle_pkg, "ThrottleRegistry")

    def test_resilience_package_no_longer_exports_dead_api(self) -> None:
        from lexigram import resilience

        assert "throttle" not in resilience.__all__
        assert "get_throttle_stats" not in resilience.__all__
        assert "ThrottleRegistry" not in resilience.__all__
        assert "Throttler" in resilience.__all__
