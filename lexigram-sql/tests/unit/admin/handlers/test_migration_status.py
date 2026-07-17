"""Tests for the migration_status admin widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import WidgetParams
from lexigram.result import Ok
from lexigram.sql.admin.handlers.migration_status import MigrationStatusWidgetHandler


class _FakeMigrations:
    def __init__(self, applied: list, pending: list) -> None:
        self._applied = applied
        self._pending = pending

    async def get_applied_migrations(self) -> list:
        return self._applied

    async def get_pending_migrations(self) -> list:
        return self._pending


async def test_migration_status_reports_real_counts() -> None:
    handler = MigrationStatusWidgetHandler(_FakeMigrations(["a", "b"], ["c"]))
    result = await handler.get_data(WidgetParams(time_window_minutes=60))
    assert isinstance(result, Ok)
    values = [s.value for s in result.unwrap().stats]
    assert "2 applied" in values
    assert "1 pending" in values


async def test_migration_status_no_pending_is_success() -> None:
    handler = MigrationStatusWidgetHandler(_FakeMigrations(["a", "b"], []))
    result = await handler.get_data(WidgetParams(time_window_minutes=60))
    assert isinstance(result, Ok)
    values = [s.value for s in result.unwrap().stats]
    assert "2 applied" in values
    assert "0 pending" in values


__all__ = [
    "test_migration_status_reports_real_counts",
    "test_migration_status_no_pending_is_success",
]
