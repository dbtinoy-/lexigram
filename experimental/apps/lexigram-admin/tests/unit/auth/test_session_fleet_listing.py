"""Fleet-wide session listing (R12): store `list_active` + service wrapper."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.services.session_service import AdminSessionService
from lexigram.admin.auth.store.session_sql import AdminSessionSqlRepository


class FakeProvider:
    """Records calls; returns configurable query rows."""

    def __init__(self, rows: list[dict] | None = None) -> None:
        self.database_type = "sqlite"
        self.executed: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list]] = []
        self._rows = rows or []

    async def execute(self, sql: str, params: list | None = None) -> object:
        self.executed.append((sql, params or []))
        return SimpleNamespace(row_count=0)

    async def execute_query(self, sql: str, params: list | None = None) -> list[dict]:
        self.queries.append((sql, params or []))
        return self._rows

    async def execute_insert(self, table: object, data: dict) -> object:
        return SimpleNamespace(success=True, row_count=1)


@pytest.mark.asyncio
async def test_list_active_filters_active_unexpired_and_orders() -> None:
    provider = FakeProvider(rows=[{"session_id": "s1", "admin_id": "u1"}])
    repo = AdminSessionSqlRepository(provider)
    cutoff = datetime(2026, 9, 1, tzinfo=UTC)

    rows = await repo.list_active(cutoff, limit=50)

    sql, params = provider.queries[-1]
    assert "is_active = TRUE" in sql
    assert "expires_at > ?" in sql
    assert "ORDER BY last_active_at DESC" in sql
    assert "LIMIT 50" in sql
    assert params == [cutoff]
    assert rows[0]["session_id"] == "s1"


@pytest.mark.asyncio
async def test_list_active_limit_is_coerced_to_int() -> None:
    """The LIMIT clause is interpolated — it must never accept raw strings."""
    provider = FakeProvider()
    repo = AdminSessionSqlRepository(provider)

    await repo.list_active(datetime.now(UTC), limit="25")  # type: ignore[arg-type]
    assert "LIMIT 25" in provider.queries[-1][0]

    with pytest.raises((ValueError, TypeError)):
        await repo.list_active(datetime.now(UTC), limit="25; DROP TABLE x")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_service_list_active_sessions_delegates() -> None:
    repo = MagicMock()
    repo.list_active = AsyncMock(return_value=[{"session_id": "s1"}])
    service = AdminSessionService(session_repo=repo)

    rows = await service.list_active_sessions(limit=10)

    assert rows == [{"session_id": "s1"}]
    args = repo.list_active.await_args
    assert args.args[1] == 10 or args.kwargs.get("limit") == 10


@pytest.mark.asyncio
async def test_service_degrades_when_repo_lacks_list_active() -> None:
    class MinimalRepo:
        """Third-party repo satisfying only the base protocol."""

    service = AdminSessionService(session_repo=MinimalRepo())  # type: ignore[arg-type]
    assert await service.list_active_sessions() == []
