"""Cross-owner isolation tests for feedback storage and service layers.

A record written under owner A must be invisible to a query scoped to
owner B: the SQL predicate / cache key must carry owner_id, and the
service layer must thread it through.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.feedback.storage.database import DatabaseFeedbackStore
from lexigram.ai.feedback.types import FeedbackItem, FeedbackType

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
