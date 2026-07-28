"""Unit tests for TimeoutManager."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.resilience.exceptions import ResilienceTimeoutError
from lexigram.resilience.timeout.manager import TimeoutManager


class TestTimeoutManagerConfiguration:
    """Tests for TimeoutManager initialization and configuration API."""

    def test_default_timeout_is_positive(self) -> None:
        """Default timeout is applied when creating a manager without arguments."""
        manager = TimeoutManager(default_seconds=30.0)
        assert manager.get_timeout("any_operation") == 30.0

    def test_configure_sets_per_operation_override(self) -> None:
        """configure() registers a per-operation timeout."""
        manager = TimeoutManager(default_seconds=30.0)
        manager.configure("fast_op", seconds=5.0)
        assert manager.get_timeout("fast_op") == 5.0

    def test_unknown_operation_falls_back_to_default(self) -> None:
        """get_timeout returns the default for operations without an override."""
        manager = TimeoutManager(default_seconds=15.0)
        assert manager.get_timeout("unconfigured") == 15.0

    def test_configure_overrides_previous_value(self) -> None:
        """configure() on the same key replaces the previous timeout."""
        manager = TimeoutManager()
        manager.configure("op", seconds=10.0)
        manager.configure("op", seconds=3.0)
        assert manager.get_timeout("op") == 3.0

    def test_init_rejects_non_positive_default(self) -> None:
        """Constructing with a non-positive default raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            TimeoutManager(default_seconds=0.0)

    def test_configure_rejects_non_positive_timeout(self) -> None:
        """configure() with a non-positive value raises ValueError."""
        manager = TimeoutManager()
        with pytest.raises(ValueError, match="positive"):
            manager.configure("op", seconds=-1.0)


class TestTimeoutManagerRun:
    """Tests for TimeoutManager.run()."""

    @pytest.mark.asyncio
    async def test_run_returns_coroutine_result(self) -> None:
        """run() returns the coroutine's result when it completes within the timeout."""
        manager = TimeoutManager(default_seconds=5.0)

        async def fast() -> str:
            return "done"

        result = await manager.run("op", fast())
        assert result == "done"

    @pytest.mark.asyncio
    async def test_run_uses_per_operation_timeout(self) -> None:
        """run() applies the per-operation timeout, not the default."""
        manager = TimeoutManager(default_seconds=10.0)
        manager.configure("slow_but_ok", seconds=0.5)

        async def just_in_time() -> int:
            await asyncio.sleep(0.01)
            return 42

        result = await manager.run("slow_but_ok", just_in_time())
        assert result == 42

    @pytest.mark.asyncio
    async def test_run_raises_resilience_timeout_error_on_timeout(self) -> None:
        """run() raises ResilienceTimeoutError when the coro exceeds the timeout."""
        manager = TimeoutManager(default_seconds=0.05)

        async def too_slow() -> None:
            await asyncio.sleep(10)

        with pytest.raises(ResilienceTimeoutError):
            await manager.run("tardy_op", too_slow())

    @pytest.mark.asyncio
    async def test_run_with_named_timeout_raises_on_per_operation_limit(self) -> None:
        """A per-operation timeout shorter than default is honoured."""
        manager = TimeoutManager(default_seconds=60.0)
        manager.configure("tiny_budget", seconds=0.05)

        async def hangs() -> None:
            await asyncio.sleep(10)

        with pytest.raises(ResilienceTimeoutError):
            await manager.run("tiny_budget", hangs())
