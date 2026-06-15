"""Tests for the migration_status admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.contracts.admin import HealthCheckPayload, WidgetParams
from lexigram.contracts.core.health import HealthStatus
from lexigram.sql.admin.handlers.migration_status import MigrationStatusWidgetHandler


def _fake_manager() -> MagicMock:
    return MagicMock()


async def test_migration_status_handler_returns_health_check_payload() -> None:
    handler = MigrationStatusWidgetHandler(migration_manager=_fake_manager())
    result = await handler.get_data(WidgetParams())
    payload = result.unwrap()
    assert isinstance(payload, HealthCheckPayload)


async def test_migration_status_up_to_date_is_healthy() -> None:
    handler = MigrationStatusWidgetHandler(migration_manager=_fake_manager())
    result = await handler.get_data(WidgetParams())
    payload = result.unwrap()
    assert payload.component == "sql.migrations"
    assert payload.status is HealthStatus.HEALTHY
    assert "20240101_000001" in payload.detail


__all__ = [
    "test_migration_status_handler_returns_health_check_payload",
    "test_migration_status_up_to_date_is_healthy",
]