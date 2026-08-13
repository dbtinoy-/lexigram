"""Cross-owner isolation tests for DatabaseMemoryBackend.

Uses a test-local fake DatabaseProviderProtocol that records every
execute call and applies naive ``WHERE owner_id``/``LIMIT`` semantics,
mirroring the SQL the backend issues.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from lexigram.ai.memory.backends.database import DatabaseMemoryBackend
from lexigram.contracts.ai.memory import MemoryQuery

from helpers import make_entry


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows


class _FakeConnection:
    def __init__(self, rows_by_id: dict[str, dict[str, Any]]) -> None:
        self._rows_by_id = rows_by_id
        self.calls: list[tuple[str, list[Any]]] = []

    async def execute(self, sql: str, params: list[Any]) -> _FakeResult:
        self.calls.append((sql, params))
        if sql.startswith("SELECT"):
            rows = [
                row
                for row in self._rows_by_id.values()
                if row["owner_id"] == params[0]
            ]
            if "LIMIT $2" in sql:
                rows.sort(key=lambda r: r["timestamp"], reverse=True)
                rows = rows[: params[1]]
            return _FakeResult(rows)
        if sql.startswith("INSERT"):
            row = {
                "id": params[0],
                "owner_id": params[1],
                "content": params[2],
                "role": params[3],
                "timestamp": params[4],
                "importance": params[5],
                "metadata": params[6],
                "embedding": params[7],
            }
            self._rows_by_id[row["id"]] = row
        elif sql.startswith("DELETE") and "WHERE owner_id = $1" in sql:
            for key in [
                key
                for key, row in self._rows_by_id.items()
                if row["owner_id"] == params[0]
            ]:
                del self._rows_by_id[key]
        elif sql.startswith("DELETE") and "AND owner_id = $2" in sql:
            row = self._rows_by_id.get(params[0])
            if row and row["owner_id"] == params[1]:
                del self._rows_by_id[params[0]]
        return _FakeResult([])


class _FakeProvider:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}
        self.conn = _FakeConnection(self._rows)

    def scoped_context(self) -> Any:
        class _Ctx:
            def __init__(self, owner: _FakeProvider) -> None:
                self.owner = owner

            async def __aenter__(self) -> _FakeProvider:
                return self.owner

            async def __aexit__(self, *args: Any) -> None:
                return None

        return _Ctx(self)

    async def get_scoped_connection(self) -> _FakeConnection:
        return self.conn


def _iso(ts: datetime) -> str:
    return ts.isoformat()


class TestDatabaseMemoryBackendOwnerIsolation:
    def setup_method(self) -> None:
        self.provider = _FakeProvider()
        self.backend = DatabaseMemoryBackend(self.provider)

    @pytest.mark.asyncio
    async def test_retrieve_scopes_sql_and_rows(self) -> None:
        await self.backend.store(make_entry("a1", owner_id="A"))
        await self.backend.store(make_entry("b1", owner_id="B"))

        results = await self.backend.retrieve(
            MemoryQuery(owner_id="B", query="x")
        )

        assert len(results) == 1
        assert results[0].entry.owner_id == "B"
        insert_sql, _ = self.provider.conn.calls[0]
        select_sql, params = self.provider.conn.calls[-1]
        assert "owner_id = $1" in select_sql
        assert params == ["B"]

    @pytest.mark.asyncio
    async def test_get_recent_excludes_other_owner(self) -> None:
        await self.backend.store(make_entry("a1", owner_id="A"))
        await self.backend.store(make_entry("b1", owner_id="B"))

        recent = await self.backend.get_recent(10, "A")

        assert [e.owner_id for e in recent] == ["A"]

    @pytest.mark.asyncio
    async def test_clear_targets_owner(self) -> None:
        await self.backend.store(make_entry("a1", owner_id="A"))
        await self.backend.store(make_entry("b1", owner_id="B"))

        await self.backend.clear("A")

        assert len(await self.backend.get_recent(10, "A")) == 0
        assert len(await self.backend.get_recent(10, "B")) == 1
        sql, params = next(
            (s, p) for s, p in self.provider.conn.calls if s.startswith("DELETE")
        )
        assert sql == "DELETE FROM memory_entries WHERE owner_id = $1"
        assert params == ["A"]

    @pytest.mark.asyncio
    async def test_delete_carries_owner_bind(self) -> None:
        b_entry = make_entry("b1", owner_id="B")
        await self.backend.store(b_entry)

        await self.backend.delete(b_entry.id, "A")

        sql, params = next(
            (s, p) for s, p in self.provider.conn.calls if s.startswith("DELETE")
        )
        assert "id = $1 AND owner_id = $2" in sql
        assert params == [b_entry.id, "A"]
        assert len(await self.backend.get_recent(10, "B")) == 1

    @pytest.mark.asyncio
    async def test_metadata_filter_applies_within_owner(self) -> None:
        await self.backend.store(
            make_entry("turn", metadata={"type": "turn"}, owner_id="A")
        )
        await self.backend.store(
            make_entry("note", metadata={"type": "note"}, owner_id="A")
        )

        results = await self.backend.retrieve(
            MemoryQuery(owner_id="A", query="x", filters={"type": "turn"})
        )

        assert len(results) == 1
        assert results[0].entry.metadata["type"] == "turn"

    @pytest.mark.asyncio
    async def test_row_round_trip_preserves_owner(self) -> None:
        entry = make_entry("stored", owner_id="A")
        await self.backend.store(entry)

        results = await self.backend.retrieve(MemoryQuery(owner_id="A", query="x"))

        assert results[0].entry.owner_id == "A"
        assert results[0].entry.id == entry.id