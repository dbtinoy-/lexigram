"""Tests for AdminCsrfMiddleware.

The middleware delegates all token generation and validation to
AdminCsrfServiceProtocol.  Tests mock the service at the contract boundary.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.middleware.csrf import AdminCsrfMiddleware

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_csrf_service(*, valid: bool = True) -> MagicMock:
    """Return a mock AdminCsrfServiceProtocol."""
    svc = MagicMock()
    svc.validate_token = MagicMock(return_value=valid)
    svc.generate_token = MagicMock(return_value="test-csrf-token")
    return svc


def _make_scope(
    method: str = "GET",
    path: str = "/admin/",
    headers: dict[bytes, bytes] | None = None,
    session: dict | None = None,
) -> dict:
    raw_headers: list[tuple[bytes, bytes]] = []
    if headers:
        raw_headers.extend(headers.items())
    scope: dict = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": raw_headers,
    }
    # Starlette reads session from scope["session"] when SessionMiddleware is used.
    if session is not None:
        scope["session"] = session
    return scope


async def _collect_response(
    middleware: AdminCsrfMiddleware,
    scope: dict,
    body: bytes = b"",
) -> tuple[int, bytes]:
    """Run middleware and return (status_code, response_body)."""
    receive_called = False

    async def receive():
        nonlocal receive_called
        if not receive_called:
            receive_called = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    messages: list[dict] = []

    async def send(message: dict) -> None:
        messages.append(message)

    await middleware(scope, receive, send)

    start = next((m for m in messages if m["type"] == "http.response.start"), {})
    body_msg = next((m for m in messages if m["type"] == "http.response.body"), {})
    return start.get("status", 0), body_msg.get("body", b"")


# ---------------------------------------------------------------------------
# Safe methods pass through
# ---------------------------------------------------------------------------


class TestAdminCsrfMiddlewarePassThrough:
    @pytest.mark.asyncio
    async def test_get_passes_through(self) -> None:
        """GET requests bypass CSRF validation entirely."""

        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service())
        status, body = await _collect_response(mw, _make_scope("GET", "/admin/"))
        assert status == 200
        assert body == b"ok"

    @pytest.mark.asyncio
    async def test_head_passes_through(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service())
        status, _ = await _collect_response(mw, _make_scope("HEAD", "/admin/"))
        assert status == 200

    @pytest.mark.asyncio
    async def test_options_passes_through(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service())
        status, _ = await _collect_response(mw, _make_scope("OPTIONS", "/admin/"))
        assert status == 200

    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through(self) -> None:
        called = []

        async def inner_app(scope, receive, send):
            called.append(True)

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service())
        await mw({"type": "websocket", "path": "/ws"}, None, None)  # type: ignore[arg-type]
        assert called == [True]


# ---------------------------------------------------------------------------
# Bypass paths
# ---------------------------------------------------------------------------


class TestAdminCsrfBypassPaths:
    """POST to login/setup/health bypasses validation (pre-session forms)."""

    @pytest.mark.asyncio
    async def test_login_path_bypassed(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"login"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service(valid=False))
        status, body = await _collect_response(mw, _make_scope("POST", "/admin/login"))
        assert status == 200
        assert body == b"login"

    @pytest.mark.asyncio
    async def test_setup_path_bypassed(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"setup"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service(valid=False))
        status, _ = await _collect_response(mw, _make_scope("POST", "/admin/setup"))
        assert status == 200

    @pytest.mark.asyncio
    async def test_health_path_bypassed(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service(valid=False))
        status, _ = await _collect_response(mw, _make_scope("POST", "/health"))
        assert status == 200

    @pytest.mark.asyncio
    async def test_static_path_bypassed(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"file"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service(valid=False))
        status, _ = await _collect_response(mw, _make_scope("POST", "/static/app.js"))
        assert status == 200

    @pytest.mark.asyncio
    async def test_delete_suffix_not_bypassed(self) -> None:
        """Deletion endpoints must NOT bypass CSRF (blanket /delete bypass removed)."""

        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service(valid=False))
        status, _ = await _collect_response(
            mw, _make_scope("POST", "/admin/users/1/delete")
        )
        assert status == 403


# ---------------------------------------------------------------------------
# Enforcement — header token
# ---------------------------------------------------------------------------


class TestAdminCsrfEnforcementHeader:
    @pytest.mark.asyncio
    async def test_post_with_valid_header_token_passes(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"created"})

        svc = _make_csrf_service(valid=True)
        mw = AdminCsrfMiddleware(inner_app, svc)
        scope = _make_scope(
            "POST",
            "/admin/users/create",
            headers={b"x-csrf-token": b"valid-token"},
            session={},
        )
        status, _ = await _collect_response(mw, scope)
        assert status == 200
        svc.validate_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_without_token_returns_403(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service())
        # No X-CSRF-Token header and empty body (no form field)
        status, body = await _collect_response(
            mw, _make_scope("POST", "/admin/users/create", session={})
        )
        assert status == 403
        assert b"CSRF" in body

    @pytest.mark.asyncio
    async def test_post_with_invalid_token_returns_403(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        svc = _make_csrf_service(valid=False)
        mw = AdminCsrfMiddleware(inner_app, svc)
        scope = _make_scope(
            "POST",
            "/admin/users/create",
            headers={b"x-csrf-token": b"wrong-token"},
            session={},
        )
        status, _ = await _collect_response(mw, scope)
        assert status == 403

    @pytest.mark.asyncio
    async def test_delete_with_valid_token_passes(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service(valid=True))
        scope = _make_scope(
            "DELETE",
            "/admin/users/1",
            headers={b"x-csrf-token": b"valid-token"},
            session={},
        )
        status, _ = await _collect_response(mw, scope)
        assert status == 204

    @pytest.mark.asyncio
    async def test_put_without_token_returns_403(self) -> None:
        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service())
        status, _ = await _collect_response(
            mw, _make_scope("PUT", "/admin/users/1", session={})
        )
        assert status == 403


# ---------------------------------------------------------------------------
# Enforcement — form field token
# ---------------------------------------------------------------------------


class TestAdminCsrfEnforcementFormField:
    @pytest.mark.asyncio
    async def test_post_with_form_csrf_token_passes(self) -> None:
        """Token in form body (standard HTML form submission) is accepted."""

        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        svc = _make_csrf_service(valid=True)
        mw = AdminCsrfMiddleware(inner_app, svc)
        form_body = b"csrf_token=valid-token&name=test"
        scope = _make_scope("POST", "/admin/widgets/create", session={})
        scope["headers"] = [(b"content-type", b"application/x-www-form-urlencoded")]
        status, _ = await _collect_response(mw, scope, body=form_body)
        assert status == 200

    @pytest.mark.asyncio
    async def test_session_id_passed_to_service(self) -> None:
        """validate_token is called with the session_id from session."""

        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        svc = _make_csrf_service(valid=True)
        mw = AdminCsrfMiddleware(inner_app, svc)
        scope = _make_scope(
            "POST",
            "/admin/items/1",
            headers={b"x-csrf-token": b"tok"},
            session={"admin_user_id": "user-abc-123"},
        )
        await _collect_response(mw, scope)
        svc.validate_token.assert_called_once_with("user-abc-123", "tok")

    @pytest.mark.asyncio
    async def test_anonymous_session_id_used_when_no_session(self) -> None:
        """Falls back to 'anonymous' when session has no admin_user_id."""

        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        svc = _make_csrf_service(valid=True)
        mw = AdminCsrfMiddleware(inner_app, svc)
        scope = _make_scope(
            "POST",
            "/admin/items/1",
            headers={b"x-csrf-token": b"tok"},
            session={},  # Empty session — no admin_user_id → anonymous
        )
        await _collect_response(mw, scope)
        svc.validate_token.assert_called_once_with("anonymous", "tok")


class TestAdminCsrfViolationAudit:
    @pytest.mark.asyncio
    async def test_invalid_token_emits_csrf_violation(self) -> None:
        """Invalid tokens must be recorded as CSRF violations, best-effort."""
        from lexigram.admin.auth.types import AdminSecurityEventType

        audit_service = MagicMock()
        audit_service.log_event = MagicMock()
        mw = AdminCsrfMiddleware(
            MagicMock(),
            _make_csrf_service(valid=False),
            audit_service=audit_service,
        )
        scope = _make_scope(
            "POST",
            "/admin/users",
            headers={b"x-csrf-token": b"bad"},
            session={},
        )
        status, _ = await _collect_response(mw, scope, body=b"")
        assert status == 403
        audit_service.log_event.assert_called_once_with(
            event_type=AdminSecurityEventType.CSRF_VIOLATION,
            ip_address="unknown",
            user_agent="",
            success=False,
            metadata={"path": "/admin/users", "reason": "token_invalid"},
        )

    @pytest.mark.asyncio
    async def test_missing_token_emits_csrf_violation(self) -> None:
        """Missing tokens must be recorded with reason token_missing."""
        from lexigram.admin.auth.types import AdminSecurityEventType

        audit_service = MagicMock()
        mw = AdminCsrfMiddleware(
            MagicMock(),
            _make_csrf_service(valid=True),
            audit_service=audit_service,
        )
        await _collect_response(
            mw,
            _make_scope("POST", "/admin/users", session={}),
            body=b"",
        )
        metadata = audit_service.log_event.call_args.kwargs["metadata"]
        assert audit_service.log_event.call_args.kwargs["event_type"] == (
            AdminSecurityEventType.CSRF_VIOLATION
        )
        assert metadata["reason"] == "token_missing"

    @pytest.mark.asyncio
    async def test_valid_token_emits_no_violation(self) -> None:
        """Validated requests must not be audited as violations."""
        audit_service = MagicMock()

        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        mw = AdminCsrfMiddleware(inner_app, _make_csrf_service(valid=True), audit_service=audit_service)
        status, body = await _collect_response(
            mw,
            _make_scope(
                "POST",
                "/admin/users",
                headers={b"x-csrf-token": b"tok"},
                session={},
            ),
            body=b"",
        )
        assert status == 200
        assert body == b"ok"
        assert audit_service.log_event.call_count == 0
