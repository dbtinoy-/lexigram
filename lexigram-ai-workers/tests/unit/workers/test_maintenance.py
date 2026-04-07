"""Unit tests for lexigram.ai.workers.maintenance — Maintenance worker."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.workers.maintenance import MaintenanceWorker
from lexigram.ai.workers.types import (
    MaintenanceResult,
    MaintenanceStatus,
    MaintenanceTask,
    MaintenanceTaskType,
)


class TestMaintenanceTask:
    def test_should_run_disabled(self) -> None:
        task = MaintenanceTask(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=lambda: None, enabled=False
        )
        assert task.should_run() is False

    def test_should_run_never_run(self) -> None:
        task = MaintenanceTask(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=lambda: None, interval_seconds=60
        )
        assert task.should_run() is True

    def test_should_run_interval(self) -> None:
        task = MaintenanceTask(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=lambda: None, interval_seconds=60,
            last_run=datetime.now(UTC) - timedelta(seconds=100)
        )
        assert task.should_run() is True

        task.last_run = datetime.now(UTC) - timedelta(seconds=10)
        assert task.should_run() is False


class TestMaintenanceResult:
    def test_success(self) -> None:
        start = datetime.now(UTC) - timedelta(seconds=10)
        res = MaintenanceResult.success("t1", MaintenanceTaskType.CACHE_CLEANUP, start, items_processed=5)
        assert res.status == MaintenanceStatus.COMPLETED
        assert res.items_processed == 5
        assert res.duration_seconds >= 10.0

    def test_failure(self) -> None:
        start = datetime.now(UTC) - timedelta(seconds=10)
        res = MaintenanceResult.failure("t1", MaintenanceTaskType.CACHE_CLEANUP, start, "error")
        assert res.status == MaintenanceStatus.FAILED
        assert res.error == "error"

    def test_to_dict(self) -> None:
        res = MaintenanceResult.success("t1", MaintenanceTaskType.CACHE_CLEANUP, datetime.now(UTC))
        assert res.to_dict()["task_name"] == "t1"


class TestMaintenanceWorker:
    @pytest.fixture
    def worker(self) -> MaintenanceWorker:
        return MaintenanceWorker(check_interval=1)

    @pytest.mark.asyncio
    async def test_register_unregister(self, worker: MaintenanceWorker) -> None:
        worker.register_task(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=lambda: None, interval_seconds=60
        )
        assert "t1" in worker._tasks
        
        worker.disable_task("t1")
        assert worker._tasks["t1"].enabled is False
        
        worker.enable_task("t1")
        assert worker._tasks["t1"].enabled is True
        
        worker.unregister_task("t1")
        assert "t1" not in worker._tasks

    @pytest.mark.asyncio
    async def test_run_task_now_success_sync(self, worker: MaintenanceWorker) -> None:
        called = False
        def sync_handler() -> dict[str, Any]:
            nonlocal called
            called = True
            return {"items_processed": 10}

        worker.register_task(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=sync_handler, interval_seconds=60
        )
        
        res = await worker.run_task_now("t1")
        assert called is True
        assert res.status == MaintenanceStatus.COMPLETED
        assert res.items_processed == 10
        assert res.task_name == "t1"

    @pytest.mark.asyncio
    async def test_run_task_now_success_async(self, worker: MaintenanceWorker) -> None:
        handler = AsyncMock(return_value=5) # 5 items processed
        worker.register_task(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=handler, interval_seconds=60
        )
        
        res = await worker.run_task_now("t1")
        handler.assert_awaited_once()
        assert res.status == MaintenanceStatus.COMPLETED
        assert res.items_processed == 5

    @pytest.mark.asyncio
    async def test_run_task_now_failure(self, worker: MaintenanceWorker) -> None:
        async def failing():
            raise ValueError("bad task")

        worker.register_task(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=failing, interval_seconds=60
        )
        
        res = await worker.run_task_now("t1")
        assert res.status == MaintenanceStatus.FAILED
        assert res.error == "bad task"

    @pytest.mark.asyncio
    async def test_run_task_now_timeout(self, worker: MaintenanceWorker) -> None:
        async def slow_handler():
            await asyncio.sleep(2)

        worker.register_task(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=slow_handler, interval_seconds=60, timeout=0.1
        )
        
        res = await worker.run_task_now("t1")
        assert res.status == MaintenanceStatus.FAILED
        assert "timed out" in res.error

    @pytest.mark.asyncio
    async def test_get_stats(self, worker: MaintenanceWorker) -> None:
        async def passing(): return 1
        worker.register_task(
            name="t1", task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=passing, interval_seconds=60
        )
        
        # force run loop once
        worker._running = True
        worker._worker_task = asyncio.create_task(worker._maintenance_loop())
        await asyncio.sleep(0.1)
        await worker.stop()
        
        stats = worker.get_stats()
        assert stats["total_runs"] >= 1
        assert stats["successful_runs"] >= 1
        assert stats["registered_tasks"] == 1

    @pytest.mark.asyncio
    async def test_builtin_handlers(self) -> None:
        # optimize_vector_indexes
        vec = MagicMock()
        vec.optimize_indexes = AsyncMock(return_value={"collections_optimized": 2})
        w = MaintenanceWorker(vector_store=vec)
        
        res = await w.optimize_vector_indexes()
        assert res["items_processed"] == 2
        
        # fallback if not supported
        class StoreWithoutOptimize:
            pass

        w2 = MaintenanceWorker(vector_store=StoreWithoutOptimize()) # no optimize_indexes
        res2 = await w2.optimize_vector_indexes()
        assert res2["items_processed"] == 0

        # other placeholders
        assert (await w.cleanup_old_embeddings_cache())["items_deleted"] == 0
        assert (await w.aggregate_metrics())["items_processed"] == 0
