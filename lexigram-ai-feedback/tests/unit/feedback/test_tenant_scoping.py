"""Cross-owner isolation tests for feedback storage and service layers.

A record written under owner A must be invisible to a query scoped to
owner B: the SQL predicate / cache key must carry owner_id, and the
service layer must thread it through.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.feedback.middleware import FeedbackMiddleware
from lexigram.ai.feedback.services.collector import FeedbackCollector
from lexigram.ai.feedback.services.feedback_service import FeedbackService
from lexigram.ai.feedback.storage.cache import CachedFeedbackStore
from lexigram.ai.feedback.storage.database import DatabaseFeedbackStore
from lexigram.ai.feedback.types import FeedbackItem, FeedbackType
from lexigram.result import Ok

OWNER_A = "tenant-a"
OWNER_B = "tenant-b"


def _item(owner_id: str = OWNER_A, session_id: str = "session-1") -> FeedbackItem:
    return FeedbackItem(
        feedback_type=FeedbackType.RATING,
        value=4.5,
        owner_id=owner_id,
        context={"session_id": session_id},
    )


def _db_mock(rows: list[dict[str, Any]] | None = None) -> MagicMock:
    """Build a DatabaseProviderProtocol mock with configurable query results."""
    db = MagicMock()
    db.execute = AsyncMock()
    result = MagicMock()
    result.rows = rows or []
    db.execute_query = AsyncMock(return_value=result)
    return db


class TestDatabaseFeedbackStoreIsolation:
    @pytest.mark.asyncio
    async def test_find_by_session_scopes_by_owner(self) -> None:
        db = _db_mock(rows=[])
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True

        await store.find_by_session("session-1", owner_id=OWNER_A)

        call_args = db.execute_query.await_args.args
        assert "owner_id" in call_args[0]
        assert call_args[1] == ["session-1", OWNER_A]

    @pytest.mark.asyncio
    async def test_find_by_type_scopes_by_owner(self) -> None:
        db = _db_mock(rows=[])
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True

        await store.find_by_type(FeedbackType.RATING, owner_id=OWNER_A, limit=5)

        call_args = db.execute_query.await_args.args
        assert "owner_id" in call_args[0]
        assert call_args[1] == [FeedbackType.RATING.value, OWNER_A, 5]

    @pytest.mark.asyncio
    async def test_aggregate_scopes_all_three_queries(self) -> None:
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

        await store.aggregate(owner_id=OWNER_A)

        assert len(db.execute_query.await_args_list) == 3
        for call in db.execute_query.await_args_list:
            sql, params = call.args
            assert "owner_id" in sql
            assert OWNER_A in params

    @pytest.mark.asyncio
    async def test_save_binds_owner_id(self) -> None:
        from lexigram.serialization import dumps_str

        db = _db_mock()
        store = DatabaseFeedbackStore(provider=db)
        item = _item(OWNER_A)

        await store.save(item)

        insert_calls = [
            call for call in db.execute.await_args_list if "INSERT" in call.args[0]
        ]
        assert len(insert_calls) == 1
        assert insert_calls[0].args[1] == [
            item.id,
            item.feedback_type.value,
            dumps_str(item.value),
            dumps_str(item.context),
            dumps_str(item.metadata),
            item.context.get("session_id"),
            item.owner_id,
            item.created_at.isoformat(),
        ]

    @pytest.mark.asyncio
    async def test_row_to_item_preserves_owner_id(self) -> None:
        from lexigram.serialization import dumps_str

        store = DatabaseFeedbackStore(provider=_db_mock())
        row = {
            "id": "fb-1",
            "type": "rating",
            "value": dumps_str(5.0),
            "context": dumps_str({}),
            "metadata": dumps_str({}),
            "session_id": "session-1",
            "owner_id": OWNER_A,
            "created_at": "2026-08-18T00:00:00+00:00",
        }

        item = store._row_to_item(row)

        assert item.owner_id == OWNER_A


def _cache_mock(cached_value: Any = None) -> MagicMock:
    cache = MagicMock()
    cache.get = AsyncMock(return_value=cached_value)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    return cache


class TestCachedFeedbackStoreIsolation:
    @pytest.mark.asyncio
    async def test_find_by_session_key_is_owner_namespaced(self) -> None:
        cache = _cache_mock()
        backing = MagicMock()
        backing.find_by_session = AsyncMock(return_value=[])
        store = CachedFeedbackStore(store=backing, cache=cache)

        await store.find_by_session("session-1", owner_id=OWNER_A)

        get_key = cache.get.await_args.args[0]
        assert get_key == f"feedback:session:{OWNER_A}:session-1"
        backing.find_by_session.assert_awaited_once_with("session-1", owner_id=OWNER_A)
        assert cache.set.await_args.args[0] == f"feedback:session:{OWNER_A}:session-1"

    @pytest.mark.asyncio
    async def test_find_by_type_key_is_owner_namespaced(self) -> None:
        cache = _cache_mock()
        backing = MagicMock()
        backing.find_by_type = AsyncMock(return_value=[])
        store = CachedFeedbackStore(store=backing, cache=cache)

        await store.find_by_type(FeedbackType.RATING, owner_id=OWNER_B, limit=10)

        get_key = cache.get.await_args.args[0]
        assert get_key == f"feedback:type:{OWNER_B}:rating"
        backing.find_by_type.assert_awaited_once_with(
            FeedbackType.RATING, owner_id=OWNER_B, limit=10
        )

    @pytest.mark.asyncio
    async def test_owner_b_never_reads_owner_a_cache_entry(self) -> None:
        """A cache entry written for owner A is not readable by owner B."""
        cache = _cache_mock()
        cache.get = AsyncMock(
            side_effect=lambda key: [_item(OWNER_A)] if OWNER_A in key else None
        )
        backing = MagicMock()
        backing.find_by_session = AsyncMock(return_value=[])
        store = CachedFeedbackStore(store=backing, cache=cache)

        items = await store.find_by_session("session-1", owner_id=OWNER_B)

        assert items == []
        backing.find_by_session.assert_awaited_once()
        assert cache.get.await_args.args[0] == (f"feedback:session:{OWNER_B}:session-1")

    @pytest.mark.asyncio
    async def test_save_invalidates_owner_namespaced_keys(self) -> None:
        cache = _cache_mock()
        backing = MagicMock()
        backing.save = AsyncMock(return_value=Ok("fb-1"))
        store = CachedFeedbackStore(store=backing, cache=cache)

        await store.save(_item(OWNER_A))

        deleted_keys = [call.args[0] for call in cache.delete.await_args_list]
        assert f"feedback:session:{OWNER_A}:session-1" in deleted_keys
        assert f"feedback:type:{OWNER_A}:rating" in deleted_keys


class TestServiceLayerIsolation:
    @pytest.mark.asyncio
    async def test_submit_feedback_marks_item_with_owner(self) -> None:
        store = MagicMock()
        store.save = AsyncMock(return_value=Ok("fb-1"))
        service = FeedbackService(store=store)

        await service.submit_feedback(trace_id="t1", score=0.9, owner_id=OWNER_A)

        item: FeedbackItem = store.save.await_args.args[0]
        assert item.owner_id == OWNER_A

    @pytest.mark.asyncio
    async def test_get_feedback_stats_scopes_aggregate(self) -> None:
        store = MagicMock()
        store.aggregate = AsyncMock(
            return_value=MagicMock(
                total_count=0, average_rating=None, count_by_type={}
            )
        )
        service = FeedbackService(store=store)

        await service.get_feedback_stats(owner_id=OWNER_B)

        store.aggregate.assert_awaited_once_with(owner_id=OWNER_B, window_hours=24)

    @pytest.mark.asyncio
    async def test_collector_memory_buffer_is_owner_scoped(self) -> None:
        collector = FeedbackCollector()
        await collector.collect_rating(rating=5.0, owner_id=OWNER_A)
        await collector.collect_rating(rating=3.0, owner_id=OWNER_B)

        a_items = await collector.get_feedback(owner_id=OWNER_A)
        b_items = await collector.get_feedback(owner_id=OWNER_B)

        assert len(a_items) == 1
        assert a_items[0].owner_id == OWNER_A
        assert len(b_items) == 1
        assert b_items[0].owner_id == OWNER_B

    @pytest.mark.asyncio
    async def test_collector_storage_path_scopes_find_by_type(self) -> None:
        backing = MagicMock()
        backing.save = AsyncMock()
        backing.find_by_type = AsyncMock(return_value=[])
        collector = FeedbackCollector(storage=backing)

        await collector.get_feedback(owner_id=OWNER_A, feedback_type=FeedbackType.RATING)

        backing.find_by_type.assert_awaited_with(
            FeedbackType.RATING, owner_id=OWNER_A, limit=100
        )

    @pytest.mark.asyncio
    async def test_middleware_feedback_handler_accepts_owner_id(self) -> None:
        registry = MagicMock()
        registry.process = AsyncMock(return_value="fb-1")
        collector = MagicMock()
        middleware = FeedbackMiddleware(
            collector=collector, registry=registry
        )
        handler = middleware.create_feedback_endpoint()

        response = await handler(
            "ctx-1", "rating", 4.5, owner_id=OWNER_A, extra="x"
        )

        assert response["feedback_id"] == "fb-1"
        registry.process.assert_awaited_once_with(
            "rating", 4.5, {"context_id": "ctx-1", "extra": "x"},
            collector, owner_id=OWNER_A,
        )
