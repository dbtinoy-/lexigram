"""Tests for :class:`GaugeReconciliationWorker` and its imports.

Covers the cycle behavior (reconcile, error isolation, registration) and
the boundary rule: the module must never import ``lexigram.tasks``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import subprocess
import sys
from typing import TypeVar

import pytest

from lexigram.ai.governance.persistence import InMemoryGovernancePersistence
from lexigram.ai.governance.resource.reconciliation import (
    GaugeReconciliationWorker,
)
from lexigram.ai.governance.resource.registry import ResourceUnitRegistry
from lexigram.ai.governance.resource.tracker import ResourceUnitTracker
from lexigram.contracts.ai.governance.resource_unit import (
    ResourceUnit,
    ResourceWindowKind,
)
from lexigram.contracts.infra.tasks import TaskManagerProtocol

T = TypeVar("T")


def test_reconciliation_module_imports_no_lexigram_tasks() -> None:
    """Importing the worker must not pull ``lexigram.tasks`` into a fresh process.

    Guards the inviolable rule that ``lexigram.ai.governance`` never imports
    ``lexigram.tasks`` (spec 2026-08-18-architecture-ai-governance-tasks-import).
    """
    code = (
        "import importlib, sys\n"
        "importlib.import_module('lexigram.ai.governance.resource.reconciliation')\n"
        "assert 'lexigram.tasks' not in sys.modules, 'lexigram.tasks imported'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


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


class _CountingCallback:
    """GaugeReconciliationCallback double with recorded call counts."""

    def __init__(self, per_tenant: dict[str, float]) -> None:
        self._per_tenant = per_tenant
        self.list_tenants_calls = 0

    async def list_tenants(self) -> list[str]:
        self.list_tenants_calls += 1
        return list(self._per_tenant.keys())

    async def count_active(self, tenant_id: str) -> float:
        return self._per_tenant[tenant_id]


class _RaisingCallback:
    """Callback whose list_tenants always raises (poison-pill check)."""

    async def list_tenants(self) -> list[str]:
        raise RuntimeError("no store")

    async def count_active(self, tenant_id: str) -> float:
        raise RuntimeError("no store")


def _make_tracker() -> ResourceUnitTracker:
    registry = ResourceUnitRegistry.from_list([
        ResourceUnit(
            name="concurrent_episodes",
            unit_kind="count",
            window_kind=ResourceWindowKind.INSTANTANEOUS,
        ),
    ])
    return ResourceUnitTracker(
        registry=registry,
        persistence=InMemoryGovernancePersistence(),
        get_quota=lambda _tid, _un: 10.0,
    )


def _make_worker(
    manager: TaskManagerProtocol,
    tracker: ResourceUnitTracker,
    *,
    interval_seconds: float | None = None,
) -> GaugeReconciliationWorker:
    return GaugeReconciliationWorker(
        task_manager=manager,
        tracker=tracker,
        interval_seconds=interval_seconds,
    )


def test_default_interval_is_five_minutes() -> None:
    """The worker keeps the documented 5-minute default cadence."""
    worker = _make_worker(FakeTaskManager(), _make_tracker())
    assert worker.interval_seconds == 300.0


@pytest.mark.asyncio
async def test_run_cycle_writes_ground_truth_for_every_tenant() -> None:
    """A full cycle must reconcile each registered unit to ground truth."""
    tracker = _make_tracker()
    worker = _make_worker(FakeTaskManager(), tracker)
    callback = _CountingCallback({"t1": 3.0, "t2": 0.0})
    worker.register("concurrent_episodes", callback)

    await worker.run_cycle()

    assert callback.list_tenants_calls == 1
    snap_t1 = await tracker.usage("t1", "concurrent_episodes")
    snap_t2 = await tracker.usage("t2", "concurrent_episodes")
    assert snap_t1.current == 3.0
    assert snap_t2.current == 0.0


@pytest.mark.asyncio
async def test_run_cycle_skips_poison_callback_without_raising() -> None:
    """A callback that raises must be logged and skipped, not fatal."""
    tracker = _make_tracker()
    worker = _make_worker(FakeTaskManager(), tracker)
    worker.register("concurrent_episodes", _CountingCallback({"t1": 2.0}))
    worker.register("poison_unit", _RaisingCallback())

    await worker.run_cycle()

    snap = await tracker.usage("t1", "concurrent_episodes")
    assert snap.current == 2.0


@pytest.mark.asyncio
async def test_run_cycle_isolates_per_tenant_failures() -> None:
    """A failing count_active for one tenant must not skip the others."""
    tracker = _make_tracker()
    worker = _make_worker(FakeTaskManager(), tracker)

    class _FlakyCallback:
        async def list_tenants(self) -> list[str]:
            return ["good", "bad"]

        async def count_active(self, tenant_id: str) -> float:
            if tenant_id == "bad":
                raise RuntimeError("boom")
            return 7.0

    worker.register("concurrent_episodes", _FlakyCallback())

    await worker.run_cycle()

    snap = await tracker.usage("good", "concurrent_episodes")
    assert snap.current == 7.0


@pytest.mark.asyncio
async def test_register_unregister_and_callbacks_snapshot() -> None:
    """register/unregister must be reflected in a read-only snapshot."""
    worker = _make_worker(FakeTaskManager(), _make_tracker())
    callback = _CountingCallback({"t1": 1.0})

    worker.register("concurrent_episodes", callback)
    snapshot = worker.callbacks
    assert set(snapshot) == {"concurrent_episodes"}

    snapshot.clear()
    assert "concurrent_episodes" in worker.callbacks

    worker.unregister("concurrent_episodes")
    assert worker.callbacks == {}


@pytest.mark.asyncio
async def test_start_stop_runs_reconciliation_cycles() -> None:
    """start() must drive run_cycle() periodically until stop()."""
    tracker = _make_tracker()
    manager = FakeTaskManager()
    worker = _make_worker(manager, tracker, interval_seconds=0.001)
    worker.register("concurrent_episodes", _CountingCallback({"t1": 4.0}))

    await worker.start()
    await asyncio.sleep(0.05)
    await worker.stop()

    snap = await tracker.usage("t1", "concurrent_episodes")
    assert snap.current == 4.0
    assert worker._task is not None and worker._task.done()
