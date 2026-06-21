"""Identifier safety tests for AdminSessionSqlRepository (F8)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from lexigram.admin.auth.store.session_sql import AdminSessionSqlRepository


class FakeProvider:
    """Records calls; returns configurable query rows."""

    def __init__(self, rows: list[dict] | None = None) -> None:
        self.database_type = "sqlite"
        self.executed: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list]] = []
        self.inserts: list[tuple[object, dict]] = []
        self._rows = rows or []

    async def execute(self, sql: str, params: list | None = None) -> object:
        self.executed.append((sql, params or []))
        return SimpleNamespace(row_count=0)

    async def execute_query(self, sql: str, params: list | None = None) -> list[dict]:
        self.queries.append((sql, params or []))
        return self._rows

    async def execute_insert(self, table: object, data: dict) -> object:
        self.inserts.append((table, data))
        return SimpleNamespace(success=True, row_count=1)


@pytest.mark.asyncio
async def test_dml_statements_use_quoted_table() -> None:
    """SELECT/UPDATE statements render the table as a quoted identifier."""
    provider = FakeProvider()
    repo = AdminSessionSqlRepository(provider)

    await repo.find_active("sess-1")

    dml = provider.queries[-1][0]
    assert dml.startswith('SELECT * FROM "admin_sessions" WHERE')
    assert "admin_sessions" not in dml.replace('"admin_sessions"', "")


@pytest.mark.asyncio
async def test_table_exists_uses_unquoted_name_in_literal() -> None:
    """information_schema comparisons use the raw (unquoted) `.name`."""
    provider = FakeProvider(rows=[{"exists": True}])
    provider.database_type = "postgres"
    repo = AdminSessionSqlRepository(provider)

    await repo.ensure_schema()

    assert "table_name = 'admin_sessions'" in provider.queries[0][0]
    assert (
        "executed" not in {s for s, _ in provider.executed}
        or len(provider.executed) == 0
    )


@pytest.mark.asyncio
async def test_index_ddl_uses_name_in_identifier_and_quoted_table() -> None:
    """Index names derive from `.name`; target table is quoted."""
    provider = FakeProvider()
    repo = AdminSessionSqlRepository(provider)

    await repo.ensure_schema()

    index_ddl = [sql for sql, _ in provider.executed if "CREATE INDEX" in sql]
    assert index_ddl
    assert "ix_admin_sessions_admin_id" in index_ddl[0]
    assert all('ON "admin_sessions"(' in sql for sql in index_ddl)


@pytest.mark.asyncio
async def test_insert_passes_table_name() -> None:
    """execute_insert receives the raw table name; providers quote it safely."""
    provider = FakeProvider()
    repo = AdminSessionSqlRepository(provider)
    now = datetime(2030, 1, 1, tzinfo=UTC)

    await repo.insert(
        {
            "session_id": "sess-1",
            "admin_id": "user-1",
            "expires_at": now,
        }
    )

    table, data = provider.inserts[0]
    assert table == "admin_sessions"
    assert data["session_id"] == "sess-1"
