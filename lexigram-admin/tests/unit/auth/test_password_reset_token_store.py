"""Unit tests for AdminPasswordResetTokenSqlStore with a fake DB provider."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lexigram.admin.auth.store.password_reset_token_sql import (
    AdminPasswordResetTokenSqlStore,
)


class FakeProvider:
    """Records calls; returns configurable rows."""

    def __init__(self, rows: list[dict] | None = None) -> None:
        self.database_type = "sqlite"
        self.executed: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list]] = []
        self._rows = rows or []

    async def execute(self, sql: str, params: list | None = None) -> None:
        self.executed.append((sql, params or []))

    async def execute_query(self, sql: str, params: list | None = None) -> list[dict]:
        self.queries.append((sql, params or []))
        return self._rows


@pytest.mark.asyncio
async def test_ensure_schema_creates_table() -> None:
    provider = FakeProvider()
    store = AdminPasswordResetTokenSqlStore(provider)

    await store.ensure_schema()

    assert any("CREATE TABLE IF NOT EXISTS" in sql for sql, _ in provider.executed)
    assert any("admin_password_reset_tokens" in sql for sql, _ in provider.executed)


@pytest.mark.asyncio
async def test_create_inserts_record() -> None:
    provider = FakeProvider()
    store = AdminPasswordResetTokenSqlStore(provider)
    expires = datetime(2030, 1, 1, tzinfo=UTC)

    await store.create("admin@example.com", "abc123", expires)

    sql, params = provider.executed[0]
    assert "INSERT INTO" in sql
    assert params == ["abc123", "admin@example.com", expires]


@pytest.mark.asyncio
async def test_find_by_hash_returns_record() -> None:
    provider = FakeProvider(
        rows=[
            {
                "token_hash": "abc123",
                "email": "admin@example.com",
                "expires_at": "2030-01-01T00:00:00+00:00",
                "consumed_at": None,
            }
        ]
    )
    store = AdminPasswordResetTokenSqlStore(provider)

    record = await store.find_by_hash("abc123")

    assert record is not None
    assert record.email == "admin@example.com"
    assert record.consumed_at is None


@pytest.mark.asyncio
async def test_find_by_hash_returns_none_when_missing() -> None:
    store = AdminPasswordResetTokenSqlStore(FakeProvider())

    record = await store.find_by_hash("missing")

    assert record is None


@pytest.mark.asyncio
async def test_mark_consumed_issues_update() -> None:
    provider = FakeProvider()
    store = AdminPasswordResetTokenSqlStore(provider)

    await store.mark_consumed("abc123")

    sql, params = provider.executed[0]
    assert "UPDATE" in sql
    assert "consumed_at" in sql
    assert params == ["abc123"]
