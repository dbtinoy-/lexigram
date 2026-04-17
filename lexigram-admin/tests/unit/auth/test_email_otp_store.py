"""Unit tests for AdminEmailOtpSqlStore with a fake DB provider."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from lexigram.admin.auth.store.email_otp_sql import AdminEmailOtpSqlStore


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
    store = AdminEmailOtpSqlStore(provider)

    await store.ensure_schema()

    assert any("CREATE TABLE IF NOT EXISTS" in sql for sql, _ in provider.executed)
    assert any("admin_email_otps" in sql for sql, _ in provider.executed)


@pytest.mark.asyncio
async def test_save_inserts_record_with_id() -> None:
    provider = FakeProvider()
    store = AdminEmailOtpSqlStore(provider)
    expires = datetime(2030, 1, 1, tzinfo=UTC)

    await store.save("user-001", "abc123", expires)

    sql, params = provider.executed[0]
    assert "INSERT INTO" in sql
    assert "admin_email_otps" in sql
    assert params[0]  # generated id
    assert params[1:] == ["user-001", "abc123", expires]


@pytest.mark.asyncio
async def test_consume_returns_true_when_updated() -> None:
    provider = FakeProvider(row_count=1)
    store = AdminEmailOtpSqlStore(provider)

    consumed = await store.consume("user-001", "abc123")

    assert consumed is True
    sql, params = provider.executed[0]
    assert "used_at" in sql
    assert "expires_at > NOW()" in sql
    assert params == ["user-001", "abc123"]


@pytest.mark.asyncio
async def test_consume_returns_false_when_not_updated() -> None:
    provider = FakeProvider(row_count=0)
    store = AdminEmailOtpSqlStore(provider)

    consumed = await store.consume("user-001", "abc123")

    assert consumed is False


@pytest.mark.asyncio
async def test_last_sent_at_returns_most_recent() -> None:
    provider = FakeProvider(
        rows=[{"created_at": "2030-01-01T00:00:00+00:00"}]
    )
    store = AdminEmailOtpSqlStore(provider)

    sent_at = await store.last_sent_at("user-001")

    assert sent_at == datetime(2030, 1, 1, tzinfo=UTC)
    sql, _ = provider.queries[0]
    assert "ORDER BY created_at DESC" in sql


@pytest.mark.asyncio
async def test_last_sent_at_returns_none_when_no_otp() -> None:
    store = AdminEmailOtpSqlStore(FakeProvider())

    sent_at = await store.last_sent_at("user-001")

    assert sent_at is None
