"""Tests for mount failure health tracking in AdminProvider.

These are integration-level tests that verify mount-time resolution
failures are reflected in health check status.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from lexigram.contracts.core.health import HealthStatus


class _BrokenResource:
    name = "broken"


class _ContainerStub:
    """Minimal stub that accepts singleton registrations and resolves
    all requested types by returning MagicMock instances.  Only
    ``_BrokenResource`` raises on resolve so we can test mount failures."""

    def __init__(self) -> None:
        self._fail_on: set[type] = {_BrokenResource}

    def singleton(self, key: Any, value: Any = None, **kwargs: Any) -> None:
        pass

    async def resolve(self, key: type, **kwargs: Any) -> Any:
        if key in self._fail_on:
            raise RuntimeError("resource missing dependency")
        return MagicMock()


@pytest.mark.asyncio
async def test_permissive_mount_failure_marks_admin_degraded() -> None:
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminProvider

    app = MagicMock()
    app.state = MagicMock()
    container = _ContainerStub()

    provider = AdminProvider(
        config=AdminConfig.from_dict(
            {
                "strict_resource_resolution": False,
                "auth": {"security": {"setup_token": "test-setup-token"}},
            }
        ),
        resources=[_BrokenResource],
    )
    await provider.register(container)
    await provider.boot(container)
    await provider.mount_to_app(app, container)

    result = await provider.health_check()
    assert result.status is HealthStatus.DEGRADED
    assert "resource:_BrokenResource" in result.details["mount_failures"]
