"""Tests for AdminTenantMiddleware."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.admin.config import TenancyConfig
from lexigram.admin.middleware.tenant import AdminTenantMiddleware


class TestAdminTenantMiddleware:
    """Tests for AdminTenantMiddleware."""

    @pytest.fixture
    def mock_send(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_receive(self) -> AsyncMock:
        return AsyncMock()

    def _make_scope(
        self, path: str = "/users", method: str = "GET"
    ) -> dict:
        return {
            "type": "http",
            "path": path,
            "method": method,
            "headers": [],
            "query_string": b"",
        }

    @pytest.mark.asyncio
    async def test_non_http_bypass(self, mock_receive: AsyncMock, mock_send: AsyncMock) -> None:
        """Verify non-HTTP scopes bypass tenant resolution."""
        app = AsyncMock()
        config = TenancyConfig(enabled=True)
        middleware = AdminTenantMiddleware(app, config)
        scope = {"type": "websocket"}

        await middleware(scope, mock_receive, mock_send)
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_public_path_bypass(self, mock_receive: AsyncMock, mock_send: AsyncMock) -> None:
        """Verify public paths bypass tenant resolution."""
        app = AsyncMock()
        config = TenancyConfig(enabled=True)
        middleware = AdminTenantMiddleware(app, config)
        scope = self._make_scope(path="/login")

        await middleware(scope, mock_receive, mock_send)
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_path_bypass(self, mock_receive: AsyncMock, mock_send: AsyncMock) -> None:
        """Verify health check bypasses tenant resolution.
        
        Inside the admin mount, the health path is ``/health`` (no prefix).
        """
        app = AsyncMock()
        config = TenancyConfig(enabled=True)
        middleware = AdminTenantMiddleware(app, config)
        scope = self._make_scope(path="/health")

        await middleware(scope, mock_receive, mock_send)
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tenant_resolved_from_state(
        self, mock_receive: AsyncMock, mock_send: AsyncMock
    ) -> None:
        """Verify tenant resolved from request.state."""
        app = AsyncMock()
        config = TenancyConfig(enabled=True)
        middleware = AdminTenantMiddleware(app, config)
        scope = self._make_scope(path="/users")
        scope["state"] = {"tenant_id": "tenant-123"}

        await middleware(scope, mock_receive, mock_send)
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_403_when_tenant_missing_and_enabled(
        self, mock_receive: AsyncMock, mock_send: AsyncMock
    ) -> None:
        """Verify 403 returned when tenancy enabled but no tenant resolved."""
        app = AsyncMock()
        config = TenancyConfig(enabled=True)
        middleware = AdminTenantMiddleware(app, config)
        scope = self._make_scope(path="/users")

        # Capture the send call to verify response status
        sent_messages: list[dict] = []

        async def capture_send(msg: dict) -> None:
            sent_messages.append(msg)

        await middleware(scope, mock_receive, capture_send)

        app.assert_not_awaited()
        # Find the response start message
        status = None
        for msg in sent_messages:
            if msg.get("type") == "http.response.start":
                status = msg.get("status")
                break
        assert status == 403, f"Expected 403, got {status}"

    @pytest.mark.asyncio
    async def test_allows_missing_tenant_when_disabled(
        self, mock_receive: AsyncMock, mock_send: AsyncMock
    ) -> None:
        """Verify request proceeds when tenancy is disabled even without tenant."""
        app = AsyncMock()
        config = TenancyConfig(enabled=False)
        middleware = AdminTenantMiddleware(app, config)
        scope = self._make_scope(path="/users")

        await middleware(scope, mock_receive, mock_send)
        app.assert_awaited_once()
