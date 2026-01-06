"""Integration tests for optional read-audit middleware (AUTH-14)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from lexigram.admin.middleware.read_audit import AdminReadAuditMiddleware


class _FakeAuditLogger:
    """Collects AuditEntry writes for assertion."""

    def __init__(self) -> None:
        self.entries: list[Any] = []
        self.write = AsyncMock(side_effect=self._write)

    async def _write(self, entry: Any) -> None:
        self.entries.append(entry)

    async def log(self, *args: Any, **kwargs: Any) -> None:
        pass


def _make_app(audit_logger: _FakeAuditLogger, enabled: bool = False) -> Starlette:
    """Build minimal Starlette app with read-audit middleware."""

    async def health(request: Any) -> JSONResponse:
        return JSONResponse({"ok": True})

    async def users(request: Any) -> JSONResponse:
        return JSONResponse({"users": []})

    return Starlette(
        routes=[
            Route("/admin/health", health, methods=["GET"]),
            Route("/admin/users", users, methods=["GET"]),
        ],
        middleware=[
            Middleware(
                AdminReadAuditMiddleware,
                audit_logger=audit_logger,
                read_audit_enabled=enabled,
                admin_prefix="/admin",
            ),
        ],
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_audit_disabled_by_default() -> None:
    """When read_audit is disabled, no audit entries are written."""
    logger = _FakeAuditLogger()
    app = _make_app(audit_logger=logger, enabled=False)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/admin/users")
        assert resp.status_code == 200

    assert len(logger.entries) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_audit_logs_when_enabled() -> None:
    """When read_audit is enabled, GET requests to admin paths are logged."""
    logger = _FakeAuditLogger()
    app = _make_app(audit_logger=logger, enabled=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/admin/users")
        assert resp.status_code == 200

    assert len(logger.entries) == 1
    entry = logger.entries[0]
    assert entry.action == "read.list" or entry.action == "read.detail"
    assert entry.outcome == "success"
    assert entry.admin_user_id == "anonymous"
    assert entry.resource_type == "admin_page"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_audit_skips_non_admin_paths() -> None:
    """Read-audit does not log paths outside the admin prefix."""
    logger = _FakeAuditLogger()
    app = _make_app(audit_logger=logger, enabled=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 404  # no route registered

    assert len(logger.entries) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_audit_skips_health_path() -> None:
    """Read-audit skips /admin/health paths."""
    logger = _FakeAuditLogger()
    app = _make_app(audit_logger=logger, enabled=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/admin/health")
        assert resp.status_code == 200

    assert len(logger.entries) == 0
