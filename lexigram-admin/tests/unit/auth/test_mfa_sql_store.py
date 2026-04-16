"""Unit tests for AdminMfaSqlStore with a fake DB provider."""

from __future__ import annotations

import pytest

from lexigram.admin.auth.store.mfa_sql import AdminMfaSqlStore


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
    store = AdminMfaSqlStore(provider)

    await store.ensure_schema()

    assert any("CREATE TABLE IF NOT EXISTS" in sql for sql, _ in provider.executed)
    assert any("admin_mfa_totp" in sql for sql, _ in provider.executed)


@pytest.mark.asyncio
async def test_is_enabled_false_when_no_row() -> None:
    store = AdminMfaSqlStore(FakeProvider())

    assert await store.is_enabled("user-001") is False


@pytest.mark.asyncio
async def test_is_enabled_true_when_row_present() -> None:
    provider = FakeProvider(rows=[{"secret": "SECRET"}])
    store = AdminMfaSqlStore(provider)

    assert await store.is_enabled("user-001") is True

    sql, params = provider.queries[0]
    assert "user_id = ?" in sql
    assert params == ["user-001"]


@pytest.mark.asyncio
async def test_save_secret_upserts_row() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider)

    await store.save_secret("user-001", "SECRET")

    sql, params = provider.executed[0]
    assert "INSERT INTO" in sql
    assert "ON CONFLICT" in sql
    assert params == ["user-001", "SECRET"]


@pytest.mark.asyncio
async def test_get_secret_returns_stored_value() -> None:
    provider = FakeProvider(rows=[{"secret": "SECRET"}])
    store = AdminMfaSqlStore(provider)

    secret = await store.get_secret("user-001")

    assert secret == "SECRET"
    sql, params = provider.queries[0]
    assert "admin_mfa_totp" in sql
    assert params == ["user-001"]


@pytest.mark.asyncio
async def test_get_secret_returns_none_when_missing() -> None:
    store = AdminMfaSqlStore(FakeProvider())

    assert await store.get_secret("user-001") is None


@pytest.mark.asyncio
async def test_disable_deletes_row() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider)

    await store.disable("user-001")

    sql, params = provider.executed[0]
    assert "DELETE" in sql
    assert params == ["user-001"]


@pytest.mark.asyncio
async def test_resave_after_disable_re_enables() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider)

    await store.save_secret("user-001", "SECRET")
    await store.disable("user-001")
    await store.save_secret("user-001", "SECRET2")

    assert len(provider.executed) == 3
    assert "DELETE" in provider.executed[1][0]
