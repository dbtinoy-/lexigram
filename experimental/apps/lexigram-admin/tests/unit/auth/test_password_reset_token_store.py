"""Unit tests for AdminPasswordResetTokenSqlStore with a fake DB provider."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from lexigram.admin.auth.store.password_reset_token_sql import (
    AdminPasswordResetTokenSqlStore,
)


class FakeProvider:
    """Records calls; returns configurable rows."""

    def __init__(
        self,
        rows: list[dict] | None = None,
        row_count: int | None = None,
    ) -> None:
        self.database_type = "sqlite"
        self.executed: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list]] = []
        self._rows = rows or []
        self._row_count = row_count

    async def execute(self, sql: str, params: list | None = None) -> object:
        self.executed.append((sql, params or []))
        if self._row_count is not None:
            return SimpleNamespace(row_count=self._row_count)
        return None

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
async def test_mark_consumed_returns_true_when_updated() -> None:
    provider = FakeProvider(row_count=1)
    store = AdminPasswordResetTokenSqlStore(provider)

    consumed = await store.mark_consumed("abc123")

    assert consumed is True
    sql, params = provider.executed[0]
    assert "UPDATE" in sql
    assert "consumed_at" in sql
    assert "expires_at > CURRENT_TIMESTAMP" in sql
    assert params == ["abc123"]


@pytest.mark.asyncio
async def test_mark_consumed_returns_false_when_expired_unconsumed() -> None:
    provider = FakeProvider(row_count=0)
    store = AdminPasswordResetTokenSqlStore(provider)

    consumed = await store.mark_consumed("abc123")

    assert consumed is False
    sql, params = provider.executed[0]
    assert "expires_at > CURRENT_TIMESTAMP" in sql
    assert params == ["abc123"]


@pytest.mark.asyncio
async def test_mark_consumed_returns_false_when_already_consumed() -> None:
    provider = FakeProvider(row_count=0)
    store = AdminPasswordResetTokenSqlStore(provider)

    consumed = await store.mark_consumed("abc123")

    assert consumed is False
