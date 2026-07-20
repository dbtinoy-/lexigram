"""Tests for feedback storage backends and FeedbackProvider boot wiring.

Covers:
- DatabaseFeedbackStore.save() / find_by_session() / find_by_type() / aggregate()
- CachedFeedbackStore write-through, cache-hit, and cache-invalidation behaviour
- FeedbackProvider.boot() wiring (DB-only, DB+cache, no-DB)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.feedback.di.provider import FeedbackProvider
from lexigram.ai.feedback.exceptions import FeedbackError
from lexigram.ai.feedback.storage.cache import CachedFeedbackStore
from lexigram.ai.feedback.storage.database import DatabaseFeedbackStore
from lexigram.ai.feedback.storage.protocols import FeedbackSummary
from lexigram.ai.feedback.types import FeedbackItem, FeedbackType

# ---------------------------------------------------------------------------
# Test helpers / factories
# ---------------------------------------------------------------------------


def _item(
    feedback_type: FeedbackType = FeedbackType.RATING,
    value: Any = 4.5,
    owner_id: str = "owner-1",
    session_id: str | None = "session-1",
) -> FeedbackItem:
    ctx: dict[str, Any] = {}
    if session_id:
        ctx["session_id"] = session_id
    return FeedbackItem(
        feedback_type=feedback_type, value=value, owner_id=owner_id, context=ctx
    )


def _row(item: FeedbackItem) -> dict[str, Any]:
    """Build a fake DB row dict matching the ai_feedback schema."""
    from lexigram.serialization import dumps_str

    return {
        "id": item.id,
        "type": item.type.value,
        "value": dumps_str(item.value),
        "context": dumps_str(item.context),
        "metadata": dumps_str(item.metadata),
        "session_id": item.context.get("session_id"),
        "owner_id": item.owner_id,
        "created_at": item.created_at.isoformat(),
    }


def _db_mock(rows: list[dict[str, Any]] | None = None) -> MagicMock:
    """Build a DatabaseProviderProtocol mock with configurable query results."""
    db = MagicMock()
    db.execute = AsyncMock()
    result = MagicMock()
    result.rows = rows or []
    db.execute_query = AsyncMock(return_value=result)
    return db


def _cache_mock(cached_value: Any = None) -> MagicMock:
    cache = MagicMock()
    cache.get = AsyncMock(return_value=cached_value)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    return cache


def _store_mock(
    save_result: Any = None,
    session_items: list[FeedbackItem] | None = None,
    type_items: list[FeedbackItem] | None = None,
    summary: FeedbackSummary | None = None,
) -> MagicMock:
    store = MagicMock()
    store.save = AsyncMock(return_value=save_result)
    store.find_by_session = AsyncMock(return_value=session_items or [])
    store.find_by_type = AsyncMock(return_value=type_items or [])
    store.aggregate = AsyncMock(
        return_value=summary or FeedbackSummary(total_count=0, count_by_type={})
    )
    return store


# ---------------------------------------------------------------------------
# DatabaseFeedbackStore
# ---------------------------------------------------------------------------


class TestDatabaseFeedbackStore:
    @pytest.mark.asyncio
    async def test_save_rating_returns_ok_with_id(self) -> None:
        db = _db_mock()
        store = DatabaseFeedbackStore(provider=db)
        item = _item(FeedbackType.RATING, value=5.0)
        result = await store.save(item)
        assert result.is_ok()
        assert result.unwrap() == item.id

    @pytest.mark.asyncio
    async def test_save_text_feedback_returns_ok(self) -> None:
        db = _db_mock()
        store = DatabaseFeedbackStore(provider=db)
        item = _item(FeedbackType.TEXT, value="Great response!")
        result = await store.save(item)
        assert result.is_ok()
        assert result.unwrap() == item.id

    @pytest.mark.asyncio
    async def test_save_correction_feedback_returns_ok(self) -> None:
        db = _db_mock()
        store = DatabaseFeedbackStore(provider=db)
        item = _item(FeedbackType.CORRECTION, value={"original": "A", "corrected": "B"})
        result = await store.save(item)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_save_label_feedback_returns_ok(self) -> None:
        db = _db_mock()
        store = DatabaseFeedbackStore(provider=db)
        item = _item(FeedbackType.LABEL, value="helpful")
        result = await store.save(item)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_save_calls_db_execute(self) -> None:
        db = _db_mock()
        store = DatabaseFeedbackStore(provider=db)
        item = _item()
        await store.save(item)
        # _ensure_table + INSERT = 4+ calls
        assert db.execute.await_count >= 1

    @pytest.mark.asyncio
    async def test_save_returns_err_on_connection_error(self) -> None:
        db = _db_mock()
        db.execute = AsyncMock(side_effect=ConnectionError("db offline"))
        store = DatabaseFeedbackStore(provider=db)
        item = _item()
        result = await store.save(item)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FeedbackError)

    @pytest.mark.asyncio
    async def test_save_returns_err_on_timeout(self) -> None:
        db = _db_mock()
        db.execute = AsyncMock(side_effect=TimeoutError("timeout"))
        store = DatabaseFeedbackStore(provider=db)
        result = await store.save(_item())
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_find_by_session_returns_items(self) -> None:
        item = _item(session_id="s-abc")
        db = _db_mock(rows=[_row(item)])
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True  # skip _ensure_table
        results = await store.find_by_session("s-abc", owner_id="owner-1")
        assert len(results) == 1
        assert results[0].id == item.id
        assert results[0].type == FeedbackType.RATING

    @pytest.mark.asyncio
    async def test_find_by_session_returns_empty_when_no_match(self) -> None:
        db = _db_mock(rows=[])
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True
        results = await store.find_by_session("unknown-session", owner_id="owner-1")
        assert results == []

    @pytest.mark.asyncio
    async def test_find_by_session_queries_correct_sql(self) -> None:
        db = _db_mock(rows=[])
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True
        await store.find_by_session("s-1", owner_id="owner-1")
        call_args = db.execute_query.await_args
        sql: str = call_args[0][0]
        assert "session_id" in sql
        assert call_args[0][1] == ["s-1", "owner-1"]

    @pytest.mark.asyncio
    async def test_find_by_type_returns_items(self) -> None:
        item = _item(FeedbackType.TEXT, value="good")
        db = _db_mock(rows=[_row(item)])
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True
        results = await store.find_by_type(FeedbackType.TEXT, owner_id="owner-1")
        assert len(results) == 1
        assert results[0].id == item.id
        assert results[0].type == FeedbackType.TEXT

    @pytest.mark.asyncio
    async def test_find_by_type_passes_limit_to_query(self) -> None:
        db = _db_mock(rows=[])
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True
        await store.find_by_type(FeedbackType.RATING, limit=25, owner_id="owner-1")
        call_args = db.execute_query.await_args
        params: list = call_args[0][1]
        assert params == ["rating", "owner-1", 25]

    @pytest.mark.asyncio
    async def test_aggregate_computes_summary(self) -> None:
        # Set up three execute_query calls with correct return values
        db = MagicMock()
        db.execute = AsyncMock()
        count_result = MagicMock()
        count_result.rows = [{"cnt": 10}]
        avg_result = MagicMock()
        avg_result.rows = [{"avg_rating": 4.2}]
        type_result = MagicMock()
        type_result.rows = [
            {"type": "rating", "cnt": 7},
            {"type": "text", "cnt": 3},
        ]
        db.execute_query = AsyncMock(
            side_effect=[count_result, avg_result, type_result]
        )
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True

        summary = await store.aggregate(owner_id="owner-1", window_hours=24)
        assert summary.total_count == 10
        assert abs(summary.average_rating - 4.2) < 1e-9
        assert summary.count_by_type == {"rating": 7, "text": 3}

    @pytest.mark.asyncio
    async def test_aggregate_handles_null_average_rating(self) -> None:
        db = MagicMock()
        db.execute = AsyncMock()
        db.execute_query = AsyncMock(
            side_effect=[
                MagicMock(rows=[{"cnt": 0}]),
                MagicMock(rows=[{"avg_rating": None}]),
                MagicMock(rows=[]),
            ]
        )
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True
        summary = await store.aggregate(owner_id="owner-1")
        assert summary.average_rating is None
        assert summary.total_count == 0


# ---------------------------------------------------------------------------
# CachedFeedbackStore
# ---------------------------------------------------------------------------


class TestCachedFeedbackStore:
    @pytest.mark.asyncio
    async def test_save_writes_through_to_backing_store(self) -> None:
        from lexigram.result import Ok

        backing = _store_mock()
        cache = _cache_mock()
        item = _item()
        backing.save = AsyncMock(return_value=Ok(item.id))
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        result = await cstore.save(item)
        assert result.is_ok()
        backing.save.assert_awaited_once_with(item)

    @pytest.mark.asyncio
    async def test_save_invalidates_session_cache_on_success(self) -> None:
        from lexigram.result import Ok

        item = _item(session_id="s-99")
        backing = _store_mock()
        backing.save = AsyncMock(return_value=Ok(item.id))
        cache = _cache_mock()
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        await cstore.save(item)
        cache.delete.assert_any_await("feedback:session:s-99")

    @pytest.mark.asyncio
    async def test_save_invalidates_type_cache_on_success(self) -> None:
        from lexigram.result import Ok

        item = _item(FeedbackType.TEXT)
        backing = _store_mock()
        backing.save = AsyncMock(return_value=Ok(item.id))
        cache = _cache_mock()
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        await cstore.save(item)
        cache.delete.assert_any_await("feedback:type:text")

    @pytest.mark.asyncio
    async def test_save_does_not_invalidate_cache_on_err(self) -> None:
        from lexigram.result import Err

        item = _item()
        backing = _store_mock()
        backing.save = AsyncMock(return_value=Err(FeedbackError("db error")))
        cache = _cache_mock()
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        result = await cstore.save(item)
        assert result.is_err()
        cache.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_find_by_session_returns_cache_hit(self) -> None:
        items = [_item(), _item()]
        cache = _cache_mock(cached_value=items)
        backing = _store_mock()
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        results = await cstore.find_by_session("s-1")
        assert results is items
        backing.find_by_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_find_by_session_populates_cache_on_miss(self) -> None:
        items = [_item()]
        cache = _cache_mock(cached_value=None)
        backing = _store_mock(session_items=items)
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        results = await cstore.find_by_session("s-2")
        assert results == items
        backing.find_by_session.assert_awaited_once_with("s-2")
        cache.set.assert_awaited_once()
        key_used = cache.set.await_args[0][0]
        assert "s-2" in key_used

    @pytest.mark.asyncio
    async def test_find_by_type_returns_cache_hit(self) -> None:
        items = [_item(FeedbackType.RATING)] * 5
        cache = _cache_mock(cached_value=items)
        backing = _store_mock()
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        results = await cstore.find_by_type(FeedbackType.RATING, limit=3)
        # Limited to 3 from cached 5
        assert len(results) == 3
        backing.find_by_type.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_find_by_type_populates_cache_on_miss(self) -> None:
        items = [_item(FeedbackType.TEXT)]
        cache = _cache_mock(cached_value=None)
        backing = _store_mock(type_items=items)
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        results = await cstore.find_by_type(FeedbackType.TEXT)
        assert results == items
        backing.find_by_type.assert_awaited_once()
        cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aggregate_delegates_to_backing_store(self) -> None:
        summary = FeedbackSummary(
            total_count=5, average_rating=3.8, count_by_type={"rating": 3, "text": 2}
        )
        backing = _store_mock(summary=summary)
        cache = _cache_mock()
        cstore = CachedFeedbackStore(store=backing, cache=cache)
        result = await cstore.aggregate(window_hours=12)
        assert result is summary
        backing.aggregate.assert_awaited_once_with(window_hours=12)
        cache.get.assert_not_awaited()


# ---------------------------------------------------------------------------
# FeedbackProvider.boot() wiring
# ---------------------------------------------------------------------------


class TestFeedbackProviderBoot:
    def _make_container(
        self,
        has_db: bool = False,
        has_cache: bool = False,
    ) -> MagicMock:
        """Build a mock DI container."""
        from lexigram.contracts.data import DatabaseProviderProtocol
        from lexigram.contracts.infra.cache import CacheBackendProtocol

        db_mock = MagicMock() if has_db else None
        cache_mock = MagicMock() if has_cache else None

        async def resolve_optional(protocol: type) -> Any:  # type: ignore[return]
            if protocol is DatabaseProviderProtocol:
                return db_mock
            if protocol is CacheBackendProtocol:
                return cache_mock
            return None

        container = MagicMock()
        container.singleton = MagicMock()
        container.resolve_optional = AsyncMock(side_effect=resolve_optional)
        collector = MagicMock()
        container.resolve = AsyncMock(return_value=collector)
        container._collector = collector
        return container

    @pytest.mark.asyncio
    async def test_boot_with_db_only_wires_database_store(self) -> None:
        container = self._make_container(has_db=True, has_cache=False)
        provider = FeedbackProvider()
        await provider.boot(container)
        collector = container._collector
        assert isinstance(collector.storage, DatabaseFeedbackStore)

    @pytest.mark.asyncio
    async def test_boot_with_db_and_cache_wires_cached_store(self) -> None:
        container = self._make_container(has_db=True, has_cache=True)
        provider = FeedbackProvider()
        await provider.boot(container)
        collector = container._collector
        assert isinstance(collector.storage, CachedFeedbackStore)

    @pytest.mark.asyncio
    async def test_boot_without_db_leaves_default_storage(self) -> None:
        container = self._make_container(has_db=False)
        provider = FeedbackProvider()
        initial_storage = object()
        collector = container._collector
        collector.storage = initial_storage
        await provider.boot(container)
        # When no DB available, boot returns early — storage unchanged
        assert collector.storage is initial_storage

    @pytest.mark.asyncio
    async def test_boot_skipped_when_config_disabled(self) -> None:
        from lexigram.ai.feedback.config import FeedbackConfig

        container = self._make_container(has_db=True, has_cache=True)
        provider = FeedbackProvider(config=FeedbackConfig(enabled=False))
        collector = container._collector
        collector.storage = sentinel = object()
        await provider.boot(container)
        # boot returns early — nothing wired
        container.resolve_optional.assert_not_awaited()
        assert collector.storage is sentinel
