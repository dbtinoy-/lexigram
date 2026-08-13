"""Tests for the governance-local scheduled worker base.

The base implements the periodic loop against
:class:`~lexigram.contracts.infra.tasks.TaskManagerProtocol` so governance
never imports ``lexigram.tasks`` (mirrors ``lexigram.monitor``'s
``MonitorScheduledWorker``).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

import pytest

from lexigram.ai.governance.resource import GovernanceScheduledWorker
from lexigram.contracts.infra.tasks import OnErrorPolicy, TaskManagerProtocol

T = TypeVar("T")


class FakeTaskManager:
    """Minimal :class:`TaskManagerProtocol` double that runs coroutines."""

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[object]] = []

    def track(self, coro: Awaitable[T]) -> asyncio.Task[T]:
        """Track *coro* like :meth:`BackgroundTaskManager.track`."""
        task = asyncio.create_task(coro)  # type: ignore[arg-type]
        self._tasks.append(task)
        return task

    def track_named(self, name: str, coro: Awaitable[T]) -> asyncio.Task[T]:
        """Track *coro* under *name* like the real task manager."""
        del name
        return self.track(coro)

    @property
    def pending_count(self) -> int:
        """Number of tasks not yet finished."""
        return len(self._tasks)

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Cancel and drain tracked tasks."""
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()


class _ProbeWorker(GovernanceScheduledWorker):
    """Counts cycles; used to exercise the base loop."""

    def __init__(
        self,
        task_manager: TaskManagerProtocol,
        *,
        interval_seconds: float | None = None,
    ) -> None:
        super().__init__(task_manager, interval_seconds=interval_seconds)
        self.cycles = 0

    async def run_cycle(self) -> None:
        self.cycles += 1


class _BoomWorker(GovernanceScheduledWorker):
    """Always raises; used to exercise error policies."""

    def __init__(
        self,
        task_manager: TaskManagerProtocol,
        *,
        on_error_policy: OnErrorPolicy | None = None,
    ) -> None:
        super().__init__(task_manager, on_error_policy=on_error_policy)

    async def run_cycle(self) -> None:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_start_tracks_loop_via_task_manager_protocol() -> None:
    """start() must route the loop through track_named on the protocol."""
    manager = FakeTaskManager()
    worker = _ProbeWorker(manager)

    await worker.start()

    assert len(manager._tasks) == 1
    assert worker._task is not None and not worker._task.done()

    await worker.stop()
    assert worker._task.done()


@pytest.mark.asyncio
async def test_loop_runs_cycles_until_stopped() -> None:
    """With a small interval the loop runs at least one full cycle."""
    manager = FakeTaskManager()
    worker = _ProbeWorker(manager, interval_seconds=0.001)

    await worker.start()
    await asyncio.sleep(0.05)
    await worker.stop()

    assert worker.cycles >= 1


@pytest.mark.asyncio
async def test_stop_before_start_is_noop() -> None:
    """stop() without a running task must not raise."""
    manager = FakeTaskManager()
    worker = _ProbeWorker(manager)

    await worker.stop()


@pytest.mark.asyncio
async def test_constructor_overrides_class_defaults() -> None:
    """Constructor kwargs override the class-level defaults."""
    manager = FakeTaskManager()
    worker = _ProbeWorker(manager, interval_seconds=7.5)

    assert worker.interval_seconds == 7.5
    assert worker.initial_delay_seconds == 0.0
    assert worker.on_error_policy is OnErrorPolicy.LOG_AND_CONTINUE


@pytest.mark.asyncio
async def test_on_error_policy_log_and_continue_keeps_looping() -> None:
    """A failing cycle must not kill the loop under the default policy."""
    manager = FakeTaskManager()
    worker = _BoomWorker(manager)

    await worker.start()
    await asyncio.sleep(0.05)

    assert worker._task is not None and not worker._task.done()

    await worker.stop()


@pytest.mark.asyncio
async def test_on_error_policy_stop_halts_loop() -> None:
    """OnErrorPolicy.STOP must terminate the loop on the first failure."""
    manager = FakeTaskManager()
    worker = _BoomWorker(manager, on_error_policy=OnErrorPolicy.STOP)

    await worker.start()
    await asyncio.sleep(0.05)

    assert worker._task is not None and worker._task.done()

    await worker.stop()
