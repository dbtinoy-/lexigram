"""Cross-owner isolation tests for feedback storage and service layers.

A record written under owner A must be invisible to a query scoped to
owner B: the SQL predicate / cache key must carry owner_id, and the
service layer must thread it through.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

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
