"""Unit tests for AdminEmailVerificationSqlStore with a fake DB provider."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from lexigram.admin.auth.store.email_verification_sql import (
    AdminEmailVerificationSqlStore,
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
async def test_ensure_schema_creates_table_and_index() -> None:
    provider = FakeProvider()
    store = AdminEmailVerificationSqlStore(provider)

    await store.ensure_schema()

    assert any("CREATE TABLE IF NOT EXISTS" in sql for sql, _ in provider.executed)
    assert any("admin_email_verifications" in sql for sql, _ in provider.executed)
    assert any("token_hash" in sql for sql, _ in provider.executed)


@pytest.mark.asyncio
async def test_save_token_upserts() -> None:
    provider = FakeProvider()
    store = AdminEmailVerificationSqlStore(provider)
    expires = datetime(2030, 1, 1, tzinfo=UTC)

    await store.save_token("user-001", "abc123", expires)

    sql, params = provider.executed[0]
    assert "INSERT INTO" in sql
    assert "ON CONFLICT" in sql
    assert params == ["user-001", "abc123", expires]


@pytest.mark.asyncio
async def test_is_verified_true_when_verified_at_present() -> None:
    provider = FakeProvider(rows=[{"email_verified_at": "2030-01-01T00:00:00+00:00"}])
    store = AdminEmailVerificationSqlStore(provider)

    verified = await store.is_verified("user-001")

    assert verified is True


@pytest.mark.asyncio
async def test_is_verified_false_when_not_verified() -> None:
    store = AdminEmailVerificationSqlStore(FakeProvider())

    verified = await store.is_verified("user-001")

    assert verified is False


@pytest.mark.asyncio
async def test_find_user_by_token_hash_returns_user() -> None:
    provider = FakeProvider(rows=[{"user_id": "user-001"}])
    store = AdminEmailVerificationSqlStore(provider)

    user_id = await store.find_user_by_token_hash("abc123")

    assert user_id == "user-001"


@pytest.mark.asyncio
async def test_find_user_by_token_hash_returns_none_when_missing() -> None:
    store = AdminEmailVerificationSqlStore(FakeProvider())

    user_id = await store.find_user_by_token_hash("missing")

    assert user_id is None


@pytest.mark.asyncio
async def test_consume_token_returns_true_when_updated() -> None:
    provider = FakeProvider(row_count=1)
    store = AdminEmailVerificationSqlStore(provider)

    consumed = await store.consume_token("user-001", "abc123")

    assert consumed is True
    sql, params = provider.executed[0]
    assert "email_verified_at" in sql
    assert "token_expires_at > CURRENT_TIMESTAMP" in sql
    assert params == ["user-001", "abc123"]


@pytest.mark.asyncio
async def test_consume_token_returns_false_when_not_updated() -> None:
    provider = FakeProvider(row_count=0)
    store = AdminEmailVerificationSqlStore(provider)

    consumed = await store.consume_token("user-001", "abc123")

    assert consumed is False


@pytest.mark.asyncio
async def test_clear_token_issues_update() -> None:
    provider = FakeProvider()
    store = AdminEmailVerificationSqlStore(provider)

    await store.clear_token("user-001")

    sql, params = provider.executed[0]
    assert "UPDATE" in sql
    assert "token_hash" in sql
    assert params == ["user-001"]
