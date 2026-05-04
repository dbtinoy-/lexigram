"""Tests for the server_status admin widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import HealthCheckPayload
from lexigram.contracts.admin import WidgetParams
from lexigram.contracts.core.health import HealthStatus
from lexigram.web.admin.handlers.server_status import ServerStatusWidgetHandler


async def test_server_status_handler_returns_health_check_payload() -> None:
    handler = ServerStatusWidgetHandler()
    result = await handler.get_data(WidgetParams())
    payload = result.unwrap()
    assert isinstance(payload, HealthCheckPayload)
    assert payload.status is HealthStatus.HEALTHY
    assert payload.component == "HTTP Server"
    assert "1.0.0" in payload.detail


__all__ = ["test_server_status_handler_returns_health_check_payload"]