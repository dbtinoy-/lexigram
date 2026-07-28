"""Unit tests for CacheBackendResultStore and TaskProvider result-store wiring."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from lexigram import serialization as json

import pytest

from lexigram.tasks.results import CacheBackendResultStore, InMemoryResultStore
from lexigram.tasks.results.core import ResultStore


class TestCacheBackendResultStore:
    """CacheBackendResultStore delegates to a CacheBackendProtocol."""

    def _make_store(self, *, ttl: int = 3600) -> tuple[CacheBackendResultStore, MagicMock]:
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.delete = AsyncMock(return_value=True)
        store = CacheBackendResultStore(cache, ttl=ttl)
        return store, cache

    def _make_result(self, job_id: str = "job-1", status: str = "success") -> MagicMock:
        result = MagicMock()
        result.job_id = job_id
        result.status = status
        result.to_dict.return_value = {"job_id": job_id, "status": status}
        return result

    # -- store / get --

    @pytest.mark.asyncio
    async def test_store_calls_cache_set_with_json(self) -> None:
        store, cache = self._make_store()
        result = self._make_result()

        await store.store("job-1", result)

        cache.set.assert_awaited_once()
        call_kwargs = cache.set.call_args
        key = call_kwargs[0][0]
        assert "job-1" in key

    @pytest.mark.asyncio
    async def test_get_returns_none_when_cache_miss(self) -> None:
        store, cache = self._make_store()
        cache.get = AsyncMock(return_value=None)

        result = await store.get("missing")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_deserialises_cached_value(self) -> None:
        from lexigram.tasks.models import JobResult

        store, cache = self._make_store()
        job_result = JobResult.ok(data="done")
        cache.get = AsyncMock(return_value=json.dumps(job_result.to_dict()))

        outcome = await store.get("job-1")

        assert outcome is not None
        assert outcome.success is True
        assert outcome.data == "done"

    # -- delete --

    @pytest.mark.asyncio
    async def test_delete_calls_cache_delete(self) -> None:
        store, cache = self._make_store()
        cache.delete = AsyncMock(return_value=True)

        deleted = await store.delete("job-1")

        assert deleted is True
        cache.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self) -> None:
        store, cache = self._make_store()
        cache.delete = AsyncMock(return_value=False)

        deleted = await store.delete("no-such-job")

        assert deleted is False

    # -- cleanup_expired --

    @pytest.mark.asyncio
    async def test_cleanup_expired_returns_zero(self) -> None:
        store, _ = self._make_store()
        count = await store.cleanup_expired()
        assert count == 0

    # -- wait timeout --

    @pytest.mark.asyncio
    async def test_wait_returns_none_when_timeout_exceeded(self) -> None:
        store, cache = self._make_store()
        cache.get = AsyncMock(return_value=None)

        result = await store.wait("job-1", timeout=0.05, poll_interval=0.01)

        assert result is None

    # -- interface conformance --

    def test_is_subclass_of_result_store(self) -> None:
        store, _ = self._make_store()
        assert isinstance(store, ResultStore)


class TestInMemoryResultStore:
    """InMemoryResultStore basic round-trip (regression guard)."""

    @pytest.mark.asyncio
    async def test_store_and_get_round_trip(self) -> None:
        from lexigram.tasks.models import JobResult

        store = InMemoryResultStore()
        result = JobResult.ok(data=42)

        await store.store("j1", result)
        retrieved = await store.get("j1")

        assert retrieved is not None
        assert retrieved.success is True
        assert retrieved.data == 42
