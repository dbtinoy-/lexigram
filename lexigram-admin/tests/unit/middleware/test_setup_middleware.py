"""Tests for SetupMiddleware graceful degradation on DB errors."""

from __future__ import annotations

from typing import Any

import pytest
from starlette.responses import PlainTextResponse

from lexigram.admin.middleware.setup import SetupMiddleware


class _Store:
    """Minimal store stub for testing."""

    def __init__(self, count: int = 1, raise_on_count: bool = False) -> None:
        self._count = count
        self._raise = raise_on_count

    async def get_admin_count(self) -> int:
        if self._raise:
            msg = "await wasn't used with future"
            raise RuntimeError(msg)
        return self._count


def _make_scope(path: str = "/admin/test", root_path: str = "") -> dict[str, Any]:
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "root_path": root_path,
        "query_string": b"",
        "headers": [(b"host", b"localhost")],
        "scheme": "http",
        "server": ("test", 80),
        "client": ("127.0.0.1", 50000),
        "state": {},
    }


async def _noop_receive() -> dict[str, Any]:
    return {"type": "http.disconnect"}


@pytest.mark.asyncio
async def test_lets_request_through_on_db_error():
    """When get_admin_count raises RuntimeError, request passes through (no redirect)."""
    store = _Store(raise_on_count=True)
    messages: list[dict[str, Any]] = []

    async def ok_app(scope: Any, receive: Any, send: Any) -> None:
        response = PlainTextResponse("ok")
        await response(scope, receive, send)

    async def collect_send(message: dict[str, Any]) -> None:
        messages.append(message)

    middleware = SetupMiddleware(ok_app, store)
    await middleware(_make_scope(), _noop_receive, collect_send)

    # Must produce a response (not a redirect)
    start_msg = next((m for m in messages if m["type"] == "http.response.start"), None)
    assert start_msg is not None, "No response start message"
    assert start_msg["status"] == 200, f"Expected 200, got {start_msg['status']}"
    headers = dict(start_msg.get("headers", []))
    assert b"location" not in headers, "Unexpected redirect header"


@pytest.mark.asyncio
async def test_redirects_when_no_users():
    """When count is 0, still redirects to /setup (happy path unchanged)."""
    store = _Store(count=0)
    messages: list[dict[str, Any]] = []

    async def ok_app(scope: Any, receive: Any, send: Any) -> None:
        response = PlainTextResponse("ok")
        await response(scope, receive, send)

    async def collect_send(message: dict[str, Any]) -> None:
        messages.append(message)

    middleware = SetupMiddleware(ok_app, store)
    await middleware(
        _make_scope(path="/admin/users", root_path="/admin"),
        _noop_receive,
        collect_send,
    )

    start_msg = next((m for m in messages if m["type"] == "http.response.start"), None)
    assert start_msg is not None
    # RedirectResponse defaults to 307 in Starlette
    assert start_msg["status"] == 307, f"Expected 307, got {start_msg['status']}"


@pytest.mark.asyncio
async def test_skips_setup_path():
    """Setup path is always allowed through."""
    store = _Store(count=0)
    messages: list[dict[str, Any]] = []

    async def ok_app(scope: Any, receive: Any, send: Any) -> None:
        response = PlainTextResponse("setup page")
        await response(scope, receive, send)

    async def collect_send(message: dict[str, Any]) -> None:
        messages.append(message)

    middleware = SetupMiddleware(ok_app, store)
    await middleware(_make_scope(path="/setup"), _noop_receive, collect_send)

    start_msg = next((m for m in messages if m["type"] == "http.response.start"), None)
    assert start_msg is not None
    assert start_msg["status"] == 200
    body_msg = next((m for m in messages if m["type"] == "http.response.body"), None)
    assert body_msg is not None
    assert b"setup page" in body_msg.get("body", b"")
