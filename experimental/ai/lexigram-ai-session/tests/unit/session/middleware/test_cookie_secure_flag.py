"""Secure-flag + delivery tests for the AI session cookie (round-5 finding).

Two round-5 issues are covered here:

1. The session cookie previously shipped with ``Max-Age``/``HttpOnly``/
   ``SameSite=Lax`` but no ``Secure`` flag, so over an HTTPS deployment
   the session ID would still be transmitted on plain HTTP requests.
   The flag is now set when the request scope's scheme is https.

2. The cookie was never actually delivered: the middleware wrapped the
   ASGI ``send`` callable but never called it (there was no inner app),
   so ``Set-Cookie`` was dead code and cookie-based session continuity
   silently never worked.  The middleware is now a composing ASGI
   middleware (Starlette ``Middleware(SessionMiddleware, ...)``-compatible)
   that calls the inner app with the wrapped send.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from lexigram.ai.session.config import SessionConfig
from lexigram.ai.session.middleware.session_middleware import SessionMiddleware


def _scope(scheme: str) -> dict[str, Any]:
    return {
        "type": "http",
        "scheme": scheme,
        "headers": [],
        "query_string": b"",
    }


def _manager() -> Any:
    """Minimal stub implementing SessionManagerProtocol."""
    from unittest.mock import AsyncMock, MagicMock

    mgr = MagicMock()
    state = MagicMock(session_id=str(uuid4()))
    mgr.create = AsyncMock(return_value=state)
    mgr.get_state = AsyncMock(return_value=None)  # noqa: return None, not Mock
    mgr.validate_session = AsyncMock(return_value=None)
    return mgr


async def _deliver_response(scheme: str, config: SessionConfig) -> str:
    """Run the middleware around a stub inner app and capture the cookie."""
    mgr = _manager()

    sent: dict[str, Any] = {}

    async def inner_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})

    async def outer_send(message: dict[str, Any]) -> None:
        sent.update(message)

    mw = SessionMiddleware(inner_app, session_manager=mgr, config=config)
    await mw(_scope(scheme), AsyncMock(), outer_send)

    headers = sent.get("headers", [])
    return dict(headers).get(b"set-cookie", b"").decode()


from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_cookie_delivered_with_secure_flag_on_https() -> None:
    cfg = SessionConfig(cookie_name="lexsession", auto_checkpoint_interval=None)
    cookie = await _deliver_response("https", cfg)
    assert "lexsession=" in cookie
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Max-Age=" in cookie


@pytest.mark.asyncio
async def test_cookie_delivered_without_secure_flag_on_http() -> None:
    cfg = SessionConfig(cookie_name="lexsession", auto_checkpoint_interval=None)
    cookie = await _deliver_response("http", cfg)
    assert "lexsession=" in cookie
    assert "Secure" not in cookie
    assert "HttpOnly" in cookie


@pytest.mark.asyncio
async def test_no_cookie_when_cookie_name_unset() -> None:
    cfg = SessionConfig(cookie_name=None, auto_checkpoint_interval=None)
    cookie = await _deliver_response("https", cfg)
    assert cookie == ""


@pytest.mark.asyncio
async def test_inner_app_still_called_when_scope_not_http() -> None:
    mgr = _manager()
    cfg = SessionConfig(cookie_name="lexsession", auto_checkpoint_interval=None)
    called = False

    async def inner_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        nonlocal called
        called = True

    mw = SessionMiddleware(inner_app, session_manager=mgr, config=cfg)
    await mw({"type": "websocket", "scheme": "wss"}, AsyncMock(), AsyncMock())
    assert called is True
