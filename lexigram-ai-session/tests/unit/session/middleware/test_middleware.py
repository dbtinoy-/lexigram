"""Unit tests for ASGI SessionMiddleware."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lexigram.ai.session.config import SessionConfig
from lexigram.ai.session.context import SessionContext
from lexigram.ai.session.middleware.session_middleware import (
    SessionMiddleware,
    _CookieInjectSend,
)


def _build_scope(
    scope_type: str = "http",
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
) -> dict[str, Any]:
    return {
        "type": scope_type,
        "headers": headers or [],
        "query_string": query_string,
    }


def _make_manager(session_id: str | None = None) -> MagicMock:
    """Build a mock SessionManagerImpl that returns a fake SessionState."""
    sid = session_id or str(uuid4())
    state = MagicMock()
    state.session_id = sid
    mgr = MagicMock()
    mgr.get_state = AsyncMock(return_value=state)
    mgr.create = AsyncMock(return_value=state)
    return mgr, state


class TestSessionMiddlewareExtraction:
    """Test session ID extraction from headers, query params, and cookies."""

    async def test_session_id_extracted_from_header(self) -> None:
        session_id = str(uuid4())
        mgr, state = _make_manager(session_id)
        cfg = SessionConfig(header_name="X-Session-ID", auto_checkpoint_interval=None)
        mw = SessionMiddleware(session_manager=mgr, config=cfg)

        scope = _build_scope(headers=[(b"x-session-id", session_id.encode())])
        await mw(scope, AsyncMock(), AsyncMock())

        mgr.get_state.assert_awaited_once_with(session_id)
        assert scope["session"] is not None

    async def test_session_id_extracted_from_query_param(self) -> None:
        session_id = str(uuid4())
        mgr, state = _make_manager(session_id)
        cfg = SessionConfig(auto_checkpoint_interval=None)
        mw = SessionMiddleware(session_manager=mgr, config=cfg)

        scope = _build_scope(query_string=f"session_id={session_id}".encode())
        await mw(scope, AsyncMock(), AsyncMock())

        mgr.get_state.assert_awaited_once_with(session_id)

    async def test_session_id_extracted_from_cookie(self) -> None:
        session_id = str(uuid4())
        mgr, state = _make_manager(session_id)
        cfg = SessionConfig(cookie_name="lexsession", auto_checkpoint_interval=None)
        mw = SessionMiddleware(session_manager=mgr, config=cfg)

        cookie_header = f"lexsession={session_id}".encode()
        scope = _build_scope(headers=[(b"cookie", cookie_header)])
        await mw(scope, AsyncMock(), AsyncMock())

        mgr.get_state.assert_awaited_once_with(session_id)

    async def test_auto_creates_session_when_no_id_provided(self) -> None:
        mgr, state = _make_manager()
        cfg = SessionConfig(auto_checkpoint_interval=None)
        mw = SessionMiddleware(session_manager=mgr, config=cfg)

        scope = _build_scope()
        await mw(scope, AsyncMock(), AsyncMock())

        mgr.create.assert_awaited_once()
        assert scope["session"] is not None

    async def test_scope_session_is_session_context(self) -> None:
        mgr, state = _make_manager()
        cfg = SessionConfig(auto_checkpoint_interval=None)
        mw = SessionMiddleware(session_manager=mgr, config=cfg)

        scope = _build_scope()
        await mw(scope, AsyncMock(), AsyncMock())

        ctx = scope["session"]
        assert isinstance(ctx, SessionContext)

    async def test_non_http_scope_is_ignored(self) -> None:
        mgr, _ = _make_manager()
        cfg = SessionConfig(auto_checkpoint_interval=None)
        mw = SessionMiddleware(session_manager=mgr, config=cfg)

        scope = _build_scope(scope_type="lifespan")
        await mw(scope, AsyncMock(), AsyncMock())

        mgr.create.assert_not_called()
        mgr.get_state.assert_not_called()
        assert "session" not in scope

    async def test_auto_create_falls_back_when_session_not_found(self) -> None:
        """When get_state returns None, a new session is created."""
        new_session_id = str(uuid4())
        new_state = MagicMock()
        new_state.session_id = new_session_id
        mgr = MagicMock()
        mgr.get_state = AsyncMock(return_value=None)
        mgr.create = AsyncMock(return_value=new_state)

        cfg = SessionConfig(auto_checkpoint_interval=None)
        mw = SessionMiddleware(session_manager=mgr, config=cfg)

        scope = _build_scope(headers=[(b"x-session-id", b"stale-id")])
        await mw(scope, AsyncMock(), AsyncMock())

        mgr.create.assert_awaited_once()


class TestCookieInjectSend:
    """Tests for the _CookieInjectSend ASGI send wrapper."""

    async def test_injects_set_cookie_on_response_start(self) -> None:
        received_messages: list[dict] = []

        async def mock_send(msg: dict) -> None:
            received_messages.append(msg)

        wrapper = _CookieInjectSend(
            mock_send,
            cookie_name="lexsession",
            session_id="abc123",
            ttl=3600,
        )

        await wrapper({"type": "http.response.start", "status": 200, "headers": []})

        assert len(received_messages) == 1
        headers = dict(received_messages[0]["headers"])
        assert b"set-cookie" in headers
        cookie_val = headers[b"set-cookie"].decode()
        assert "lexsession=abc123" in cookie_val
        assert "Max-Age=3600" in cookie_val
        assert "HttpOnly" in cookie_val

    async def test_does_not_inject_cookie_twice(self) -> None:
        calls: list[dict] = []

        async def mock_send(msg: dict) -> None:
            calls.append(msg)

        wrapper = _CookieInjectSend(
            mock_send,
            cookie_name="s",
            session_id="id1",
            ttl=60,
        )

        start_msg = {"type": "http.response.start", "status": 200, "headers": []}
        await wrapper(start_msg)
        await wrapper(start_msg)

        # First call injects set-cookie; second does not
        first_headers = dict(calls[0]["headers"])
        second_headers = dict(calls[1]["headers"])
        assert b"set-cookie" in first_headers
        assert b"set-cookie" not in second_headers

    async def test_passes_through_non_response_start_messages(self) -> None:
        calls: list[dict] = []

        async def mock_send(msg: dict) -> None:
            calls.append(msg)

        wrapper = _CookieInjectSend(
            mock_send, cookie_name="s", session_id="x", ttl=60
        )
        body_msg = {"type": "http.response.body", "body": b"hello"}
        await wrapper(body_msg)
        assert calls[0] is body_msg
