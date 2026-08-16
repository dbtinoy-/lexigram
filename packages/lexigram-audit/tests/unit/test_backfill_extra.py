"""Focused tests for checksum backfill utility."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.audit.verification.backfill import backfill_checksums


class _Row(dict):
    pass


class _FakeDb:
    def __init__(self, batches: list[list[dict[str, Any]]]) -> None:
        self._batches = batches
        self.queries: list[tuple[str, list]] = []

    async def execute_query(self, sql: str, params: list) -> Any:
        self.queries.append((sql, params))
        if sql.startswith("SELECT"):
            return type("Result", (), {"rows": self._batches.pop(0) if self._batches else []})()
        return type("Result", (), {})()


class _FakeResult:
    rows: list = []


class _FakeStore:
    def __init__(self, db: Any | None, table: str = "audit_log") -> None:
        self._db = db
        self._table = table


@pytest.mark.asyncio
async def test_backfill_without_db_returns_zero() -> None:
    store = _FakeStore(db=None)
    assert await backfill_checksums(store, b"key") == 0


@pytest.mark.asyncio
async def test_backfill_updates_rows() -> None:
    db = _FakeDb(
        [
            [{"id": 1, "action": "a", "checksum": None, "entry_schema_version": 1}],
            [],
        ]
    )
    store = _FakeStore(db=db)
    updated = await backfill_checksums(store, b"key")
    assert updated == 1
    assert db.queries[0][0].startswith("SELECT")
    assert db.queries[1][0].startswith("UPDATE")
    assert "checksum = ?" in db.queries[1][0]
    assert db.queries[1][1][-1] == 1


@pytest.mark.asyncio
async def test_backfill_upgrade_schema_sets_version() -> None:
    db = _FakeDb(
        [
            [{"id": 5, "action": "b", "checksum": None, "entry_schema_version": 1}],
            [],
        ]
    )
    store = _FakeStore(db=db)
    updated = await backfill_checksums(store, b"key", upgrade_schema=True)
    assert updated == 1
    update_sql, params = db.queries[1]
    assert "entry_schema_version = ?" in update_sql
    assert params == [db.queries[1][1][0], 2, 5]


@pytest.mark.asyncio
async def test_backfill_multi_batch_advances_offset() -> None:
    db = _FakeDb(
        [
            [{"id": 1, "action": "a"}],
            [{"id": 2, "action": "b"}],
            [],
        ]
    )
    store = _FakeStore(db=db)
    updated = await backfill_checksums(store, b"key")
    assert updated == 2
    assert db.queries[2][1] == [100, 100]