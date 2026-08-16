"""Tests for FlagManager background task tracking (F2 — RUF006 compliance).

Verifies that async change-listener tasks are stored in
``FlagManager._background_tasks`` and removed upon completion,
following the AGENTS.md pattern for proper asyncio task lifecycle.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from lexigram.features.manager import FlagManager


class TestFlagManagerBackgroundTasksAttribute:
    """FlagManager has a _background_tasks set initialised in __init__."""

    def test_background_tasks_attribute_exists(self) -> None:
        """FlagManager initialises with a ``_background_tasks`` set."""
        mgr = FlagManager()
        assert hasattr(mgr, "_background_tasks")

    def test_background_tasks_is_set(self) -> None:
        """``_background_tasks`` is a ``set`` instance."""
        mgr = FlagManager()
        assert isinstance(mgr._background_tasks, set)

    def test_background_tasks_empty_on_init(self) -> None:
        """``_background_tasks`` is empty for a newly created manager."""
        mgr = FlagManager()
        assert len(mgr._background_tasks) == 0


class TestFlagManagerAsyncListenerTaskTracking:
    """Async listener tasks are tracked in _background_tasks during execution."""

    @pytest.mark.asyncio
    async def test_async_listener_task_tracked_during_execution(self) -> None:
        """An asyncio.Task for an async listener is added to _background_tasks."""
        mgr = FlagManager()
        gate = asyncio.Event()
        pending_task_refs: list[asyncio.Task[Any]] = []

        async def slow_listener(name: str, old: bool, new: bool) -> None:
            # Record the running task so we can inspect it from outside
            current = asyncio.current_task()
            if current is not None:
                pending_task_refs.append(current)
            await gate.wait()  # Hold the task until we release it

        mgr.add_listener(slow_listener)
        # enable() calls _notify_listeners internally
        mgr.enable("flag-x")

        # Give the event loop a tick so the task starts
        await asyncio.sleep(0)

        # At this point the task is blocked on gate.wait() and should still
        # be in _background_tasks
        assert len(mgr._background_tasks) >= 1

        # Release the task
        gate.set()
        # Allow the task to complete and the done-callback to fire
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        # After completion the set should shrink back toward zero
        # (exact timing: give up to 10 iterations for task teardown)
        for _ in range(10):
            if len(mgr._background_tasks) == 0:
                break
            await asyncio.sleep(0)

        assert len(mgr._background_tasks) == 0

    @pytest.mark.asyncio
    async def test_no_lambda_callback_in_notify_listeners(self) -> None:
        """_notify_listeners does NOT use lambda _t: None (GC-unsafe) callback style."""
        import inspect

        mgr = FlagManager()
        source = inspect.getsource(mgr._notify_listeners)
        # The old unsafe pattern was: task.add_done_callback(lambda _t: None)
        assert "lambda _t: None" not in source, (
            "The lambda _t: None callback was removed and replaced with "
            "self._background_tasks.discard (RUF006 compliance)."
        )

    @pytest.mark.asyncio
    async def test_create_tracked_task_in_notify_listeners(self) -> None:
        """_notify_listeners uses create_tracked_task (RUF006 compliance via framework pattern)."""
        import inspect

        mgr = FlagManager()
        source = inspect.getsource(mgr._notify_listeners)
        assert "create_tracked_task" in source, (
            "_notify_listeners should use create_tracked_task from lexigram.concurrency "
            "to ensure proper background task tracking (RUF006 compliance)."
        )
