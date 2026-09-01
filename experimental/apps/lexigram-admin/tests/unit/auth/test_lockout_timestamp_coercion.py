"""Lockout store must return real datetimes, not driver strings.

Regression for a live 500: SQLite hands TIMESTAMP columns back as text, and
``AdminLoginAttemptService.check_account_lockout`` computes
``unlock_at - datetime.now(UTC)`` — string passthrough raised
``TypeError: unsupported operand type(s) for -: 'str' and 'datetime.datetime'``
on every login attempt against a locked account.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from lexigram.admin.auth.store.lockout_sql import (
    AdminAccountLockoutSqlStore,
    _coerce_dt,
)


class FakeProvider:
    """Returns one active lockout row with string timestamps (SQLite shape)."""

    def __init__(self, rows: list[dict]) -> None:
        self.database_type = "sqlite"
        self._rows = rows

    async def execute(self, sql: str, params: list | None = None) -> object:
        return SimpleNamespace(row_count=0)

    async def execute_query(self, sql: str, params: list | None = None) -> list[dict]:
        return self._rows

    async def execute_insert(self, table: object, data: dict) -> object:
        return SimpleNamespace(success=True, row_count=1)


class TestCoerceDt:
    def test_none_passes_through(self) -> None:
        assert _coerce_dt(None) is None

    def test_naive_sqlite_string_becomes_aware_utc(self) -> None:
        dt = _coerce_dt("2026-09-01 15:11:02")
        assert dt == datetime(2026, 9, 1, 15, 11, 2, tzinfo=UTC)

    def test_offset_string_preserved(self) -> None:
        dt = _coerce_dt("2026-09-01 15:26:02.124057+00:00")
        assert dt is not None
        assert dt.tzinfo is not None
        assert dt.year == 2026 and dt.microsecond == 124057

    def test_datetime_passes_through_with_tz(self) -> None:
        naive = datetime(2026, 9, 1, 12, 0, 0)
        aware = _coerce_dt(naive)
        assert aware is not None and aware.tzinfo is not None

    def test_garbage_returns_none(self) -> None:
        assert _coerce_dt("not-a-timestamp") is None
        assert _coerce_dt("") is None


@pytest.mark.asyncio
async def test_get_active_lockout_returns_datetime_fields() -> None:
    """String timestamps from the driver must arrive as aware datetimes."""
    unlock = (datetime.now(UTC) + timedelta(minutes=15)).isoformat(" ")
    provider = FakeProvider(
        rows=[
            {
                "id": "l-1",
                "email": "locked@example.com",
                "locked_at": "2026-09-01 15:11:02",
                "unlock_at": unlock,
                "consecutive_failures": 5,
                "is_permanent": False,
            }
        ]
    )
    store = AdminAccountLockoutSqlStore(provider)

    info = await store.get_active_lockout("locked@example.com")

    assert info is not None
    assert isinstance(info.unlock_at, datetime)
    assert info.unlock_at.tzinfo is not None
    assert isinstance(info.locked_at, datetime)
    # The exact arithmetic that used to 500:
    retry_after = int((info.unlock_at - datetime.now(UTC)).total_seconds())
    assert retry_after > 0
