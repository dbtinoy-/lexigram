"""Contract tests for optional admin integration adapters."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.integrations.cache import CacheIntegration
from lexigram.admin.integrations.features import FeaturesIntegration
from lexigram.admin.integrations.monitor import MonitorIntegration
from lexigram.admin.integrations.resilience import ResilienceIntegration
from lexigram.admin.integrations.storage import StorageIntegration
from lexigram.admin.integrations.tasks import TasksIntegration
from lexigram.contracts.infra.storage import StorageUnsupportedOperationError
from lexigram.result import Ok


class TestCacheIntegration:
    @pytest.mark.asyncio
    async def test_get_or_compute_uses_contract_get_and_set(self) -> None:
        backend = MagicMock()
        backend.get = AsyncMock(return_value=Ok(None))
        backend.set = AsyncMock(return_value=Ok(None))
        integration = CacheIntegration(SimpleNamespace(default_ttl_seconds=30))
        integration._cache = backend

        factory = AsyncMock(return_value=([], 0))
        result = await integration.get_or_compute("admin:users", factory, ttl=12)

        assert result == ([], 0)
        factory.assert_awaited_once()
        backend.get.assert_awaited_once_with("admin:users")
        backend.set.assert_awaited_once_with("admin:users", ([], 0), 12)

    @pytest.mark.asyncio
    async def test_get_or_compute_returns_cache_hit_without_recomputing(
        self,
    ) -> None:
        backend = MagicMock()
        backend.get = AsyncMock(return_value=Ok(([{"id": "1"}], 1)))
        backend.set = AsyncMock()
        integration = CacheIntegration(SimpleNamespace(default_ttl_seconds=30))
        integration._cache = backend

        factory = AsyncMock()
        result = await integration.get_or_compute("admin:users", factory)

        assert result == ([{"id": "1"}], 1)
        factory.assert_not_awaited()
        backend.set.assert_not_awaited()


class TestStorageIntegration:
    @pytest.mark.asyncio
    async def test_noop_storage_preserves_public_adapter_methods(self) -> None:
        integration = StorageIntegration(SimpleNamespace(presigned_url_expiry=60))

        assert (await integration.put("a.txt", b"abc"))["size"] == 3
        assert await integration.get("a.txt") == b""
        assert await integration.delete("a.txt") is True
        assert await integration.presigned_url("a.txt") == ""

    @pytest.mark.asyncio
    async def test_presigned_url_uses_blob_store_timedelta_contract(self) -> None:
        backend = MagicMock()
        backend.get_presigned_url = AsyncMock(return_value="https://storage.test/a")
        integration = StorageIntegration(SimpleNamespace(presigned_url_expiry=60))
        integration._store = backend

        result = await integration.presigned_url("a.txt", expires_in=90)

        assert result == "https://storage.test/a"
        backend.get_presigned_url.assert_awaited_once_with(
            "a.txt", expires_in=timedelta(seconds=90), method="GET"
        )

    @pytest.mark.asyncio
    async def test_presigned_url_falls_back_when_backend_does_not_support_it(
        self,
    ) -> None:
        backend = MagicMock()
        backend.get_presigned_url = AsyncMock(
            side_effect=StorageUnsupportedOperationError("unsupported")
        )
        backend.get_url = AsyncMock(return_value="memory://a.txt")
        integration = StorageIntegration(SimpleNamespace(presigned_url_expiry=60))
        integration._store = backend

        assert await integration.presigned_url("a.txt") == "memory://a.txt"
        backend.get_url.assert_awaited_once_with("a.txt")


class TestMonitorIntegration:
    @pytest.mark.asyncio
    async def test_fresh_adapter_reports_noop_and_accepts_metrics(self) -> None:
        integration = MonitorIntegration(SimpleNamespace())

        integration.increment("admin.test")
        integration.gauge("admin.test", 1.0)
        integration.histogram("admin.test", 0.5)

        assert await integration.health_check() == {"status": "noop"}


class TestFeaturesIntegration:
    @pytest.mark.asyncio
    async def test_async_flag_manager_is_awaited(self) -> None:
        flags = MagicMock()
        flags.is_enabled = AsyncMock(return_value=False)
        integration = FeaturesIntegration(SimpleNamespace())
        integration._flags = flags

        assert await integration.is_enabled_async("new-dashboard") is False
        flags.is_enabled.assert_awaited_once_with("new-dashboard", None)


class TestResilienceIntegration:
    @pytest.mark.asyncio
    async def test_boot_materializes_pipeline_factory(self) -> None:
        pipeline = MagicMock()
        pipeline.execute = AsyncMock(return_value="ok")
        factory_calls: list[tuple[object, ...]] = []

        def factory(*args: object) -> MagicMock:
            factory_calls.append(args)
            return pipeline

        container = MagicMock()
        container.resolve = AsyncMock(return_value=factory)
        integration = ResilienceIntegration(
            SimpleNamespace(retry_max_attempts=2, circuit_failure_threshold=7)
        )
        integration._enabled = True

        await integration.boot(container)

        assert integration._pipeline is pipeline
        args = factory_calls[0]
        assert args[0].max_attempts == 2
        assert args[1].failure_threshold == 7

        async def work() -> str:
            return "done"

        assert await integration.execute(work) == "ok"


class TestTasksIntegration:
    @pytest.mark.asyncio
    async def test_dispatch_adapts_task_queue_enqueue_contract(self) -> None:
        queue = SimpleNamespace(enqueue=AsyncMock(return_value=Ok("task-123")))
        integration = TasksIntegration(SimpleNamespace())
        integration._tasks = queue

        result = await integration.dispatch(
            runner="admin.bulk.delete",
            action_name="delete",
            record_ids=["1", "2"],
            ctx_summary="Bulk delete",
        )

        assert result == {"status": "queued", "task_id": "task-123"}
        queue.enqueue.assert_awaited_once()
        job = queue.enqueue.await_args.args[0]
        assert job.name == "admin.bulk.delete"
        assert job.kwargs["record_ids"] == ["1", "2"]
