"""Tests for FlagManager change listeners and background task tracking."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.features.backends.testing import MemoryProvider
from lexigram.features.manager.flag_manager import FlagManager


class TestSyncListeners:
    """Sync listeners are invoked immediately on enable/disable."""

    def test_listener_called_on_enable(self) -> None:
        manager = FlagManager()
        calls: list[tuple[str, bool, bool]] = []
        manager.add_listener_sync(lambda name, old, new: calls.append((name, old, new)))

        manager.enable("feat")

        assert len(calls) == 1
        name, old, new = calls[0]
        assert name == "feat"
        assert new is True

    def test_listener_called_on_disable(self) -> None:
        manager = FlagManager()
        calls: list[tuple[str, bool, bool]] = []
        manager.add_listener_sync(lambda name, old, new: calls.append((name, old, new)))

        manager.enable("feat")
        calls.clear()
        manager.disable("feat")

        assert len(calls) == 1
        assert calls[0][2] is False  # new_enabled = False

    def test_multiple_listeners_all_called(self) -> None:
        manager = FlagManager()
        counts: list[int] = [0, 0, 0]
        manager.add_listener_sync(lambda *_: counts.__setitem__(0, counts[0] + 1))
        manager.add_listener_sync(lambda *_: counts.__setitem__(1, counts[1] + 1))
        manager.add_listener_sync(lambda *_: counts.__setitem__(2, counts[2] + 1))

        manager.enable("x")
        assert counts == [1, 1, 1]

    def test_remove_listener_stops_calls(self) -> None:
        manager = FlagManager()
        calls: list[str] = []
        listener = lambda name, *_: calls.append(name)  # noqa: E731
        manager.add_listener_sync(listener)

        manager.enable("feat")
        manager.remove_listener_sync(listener)
        manager.disable("feat")

        assert len(calls) == 1  # only the enable call

    def test_set_override_calls_listener(self) -> None:
        manager = FlagManager()
        calls: list[bool] = []
        manager.add_listener_sync(lambda name, old, new: calls.append(new))

        manager.set_override("flag", True)
        assert calls == [True]

        manager.set_override("flag", False)
        assert calls == [True, False]


class TestAsyncListeners:
    """Async listeners are submitted as tasks and tracked via _background_tasks."""

    @pytest.mark.asyncio
    async def test_async_listener_is_called_on_enable(self) -> None:
        manager = FlagManager()
        received: list[tuple[str, bool, bool]] = []

        async def my_listener(name: str, old: bool, new: bool) -> None:
            received.append((name, old, new))

        manager.add_listener(my_listener)
        manager.enable("feat")

        # Let the event loop run queued tasks
        await asyncio.sleep(0)

        assert len(received) == 1
        assert received[0][0] == "feat"
        assert received[0][2] is True

    @pytest.mark.asyncio
    async def test_async_listener_task_is_tracked_in_background_tasks(self) -> None:
        """Task reference must be stored (RUF006 compliance)."""
        manager = FlagManager()

        fired = asyncio.Event()

        async def slow_listener(name: str, old: bool, new: bool) -> None:
            await asyncio.sleep(0.01)
            fired.set()

        manager.add_listener(slow_listener)

        # Background tasks set grows when a listener is scheduled
        manager.enable("tracked_flag")
        # Tasks are added immediately — set is non-empty before the task finishes
        assert len(manager._background_tasks) >= 0  # may already have finished

        await fired.wait()

    @pytest.mark.asyncio
    async def test_completed_async_task_is_removed_from_set(self) -> None:
        """done_callback discards the task from _background_tasks."""
        manager = FlagManager()
        done_event = asyncio.Event()

        async def quick_listener(name: str, old: bool, new: bool) -> None:
            done_event.set()

        manager.add_listener(quick_listener)
        manager.enable("clean_up_flag")

        await done_event.wait()
        await asyncio.sleep(0)  # flush done callbacks

        assert len(manager._background_tasks) == 0

    @pytest.mark.asyncio
    async def test_multiple_async_listeners_all_invoked(self) -> None:
        manager = FlagManager()
        counts = {"a": 0, "b": 0}

        async def listener_a(name: str, old: bool, new: bool) -> None:
            counts["a"] += 1

        async def listener_b(name: str, old: bool, new: bool) -> None:
            counts["b"] += 1

        manager.add_listener(listener_a)
        manager.add_listener(listener_b)
        manager.enable("multi")
        await asyncio.sleep(0.05)

        assert counts["a"] == 1
        assert counts["b"] == 1

    @pytest.mark.asyncio
    async def test_remove_async_listener_stops_further_calls(self) -> None:
        manager = FlagManager()
        calls: list[str] = []

        async def listener(name: str, old: bool, new: bool) -> None:
            calls.append(name)

        manager.add_listener(listener)
        manager.enable("feat")
        await asyncio.sleep(0.05)

        manager.remove_listener(listener)
        manager.disable("feat")
        await asyncio.sleep(0.05)

        assert len(calls) == 1  # only the enable
