"""Fleet-wide lockout listing (R41, doc 37): store `list_active_lockouts`."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lexigram.admin.auth.store.lockout_sql import AdminAccountLockoutSqlStore


class FakeProvider:
    """Records calls; returns configurable query rows."""

    def __init__(self, rows: list[dict] | None = None) -> None:
        self.database_type = "sqlite"
        self.executed: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list]] = []
        self._rows = rows or []

    async def execute(self, sql: str, params: list | None = None) -> object:
        self.executed.append((sql, list(params or [])))
        return SimpleNamespace(row_count=0)

    async def execute_query(self, sql: str, params: list | None = None) -> list[dict]:
        self.queries.append((sql, list(params or [])))
        return self._rows

    async def execute_insert(self, table: object, data: dict) -> object:
        return SimpleNamespace(success=True, row_count=1)


@pytest.mark.asyncio
async def test_lists_active_rows_newest_first() -> None:
    provider = FakeProvider(
        rows=[
            {
                "email": "b@example.com",
                "locked_at": "2026-09-02 10:00:00",
                "unlock_at": "2026-09-02 10:15:00",
                "consecutive_failures": 5,
                "is_permanent": 0,
            }
        ]
    )
    store = AdminAccountLockoutSqlStore(provider)

    rows = await store.list_active_lockouts(limit=50)

    sql, params = provider.queries[-1]
    assert "is_active = TRUE" in sql
    assert "ORDER BY locked_at DESC" in sql
    assert "LIMIT 50" in sql
    assert params == []
    assert rows == [dict(provider._rows[0])]


@pytest.mark.asyncio
async def test_sweeps_expired_temporary_lockouts_before_listing() -> None:
    """Expired temp lockouts are deactivated DB-side before the SELECT."""
    provider = FakeProvider()
    store = AdminAccountLockoutSqlStore(provider)

    await store.list_active_lockouts()

    sweep = next(
        (sql for sql, _ in provider.executed if "SET is_active = FALSE" in sql),
        None,
    )
    assert sweep is not None
    assert "is_permanent = FALSE" in sweep  # permanent lockouts never swept
    assert "unlock_at <=" in sweep  # DB clock, same as get_active_lockout


@pytest.mark.asyncio
async def test_limit_is_coerced_to_int() -> None:
    """The LIMIT clause is interpolated — it must never accept raw strings."""
    provider = FakeProvider()
    store = AdminAccountLockoutSqlStore(provider)

    await store.list_active_lockouts(limit="25")  # type: ignore[arg-type]
    assert "LIMIT 25" in provider.queries[-1][0]

    with pytest.raises((ValueError, TypeError)):
        await store.list_active_lockouts(limit="25; DROP TABLE x")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_empty_table_returns_empty_list() -> None:
    store = AdminAccountLockoutSqlStore(FakeProvider(rows=[]))
    assert await store.list_active_lockouts() == []
