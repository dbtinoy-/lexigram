"""Integration test for the widget-stream SSE route mounted end-to-end.

Verifies the route (a) is guarded by the same request-entry auth
middleware as any other admin route (no _PUBLIC_PATHS bypass), and (b)
a request from an authenticated, authorized user gets back a real SSE
response built from build_widget_event_stream_handler.

DEVIATION from plan (2026-08-19): the plan's test (b) used
``httpx.ASGITransport`` + ``client.stream()``. That transport awaits the
ASGI app inline and only returns once the response completes
(httpx/_transports/asgi.py:170), so an endless SSE response hangs the
request. Test (b) therefore invokes the built handler directly with a
Starlette ``Request`` for the response-shape assertion; the transport
layer of SSE framing is already covered by lexigram-web's
sse_from_stream tests.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.routing import Route

from lexigram.admin.dashboard.widget_stream import build_widget_event_stream_handler
from lexigram.admin.middleware.authorization import (
    AdminAuthorizationMiddleware,
    DefaultRequestAuthorizer,
)
from lexigram.admin.realtime.subject_hub import SubjectAdminEventHub


class _AllowAllPermissionService:
    def get_schema(self, resource_name: str) -> object | None:
        return object()

    async def can_list(self, user: object, resource_name: str) -> bool:
        return True


class _AttachUserMiddleware(BaseHTTPMiddleware):
    """Stand-in for the app's real session-auth middleware in this test."""

    def __init__(self, app, user: object | None) -> None:
        super().__init__(app)
        self._user = user

    async def dispatch(self, request, call_next):
        if self._user is not None:
            request.state.user = self._user
        request.state.tenant_id = "acme"
        return await call_next(request)


def _build_app(user: object | None) -> Starlette:
    from lexigram.web.transport.reactive import sse_from_stream

    hub = SubjectAdminEventHub()
    handler = build_widget_event_stream_handler(
        hub, _AllowAllPermissionService(), sse_bridge=sse_from_stream
    )
    app = Starlette(routes=[Route("/admin/_sse/widgets", handler, methods=["GET"])])
    app.add_middleware(
        AdminAuthorizationMiddleware, authorizer=DefaultRequestAuthorizer()
    )
    app.add_middleware(_AttachUserMiddleware, user=user)
    return app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_widget_sse_route_requires_auth() -> None:
    app = _build_app(user=None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/admin/_sse/widgets")
    assert response.status_code in (302, 401, 403)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_widget_sse_route_returns_sse_response_for_authorized_user() -> None:
    from lexigram.web.transport.reactive import sse_from_stream

    hub = SubjectAdminEventHub()
    handler = build_widget_event_stream_handler(
        hub, _AllowAllPermissionService(), sse_bridge=sse_from_stream
    )
    scope: dict = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/admin/_sse/widgets",
        "raw_path": b"/admin/_sse/widgets",
        "query_string": b"resources=users",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("1.2.3.4", 123),
        "root_path": "",
    }
    request = Request(scope)
    request.state.user = SimpleNamespace(user_id="admin-1")
    request.state.tenant_id = "acme"
    response = await handler(request)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
