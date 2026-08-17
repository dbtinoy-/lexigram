"""Tests for CSRF Content-Type validation and token-lifetime alignment (AUTH-07, AUTH-08)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.admin.auth.services.csrf_service import AdminCsrfService
from lexigram.admin.middleware.csrf import AdminCsrfMiddleware

# ---------------------------------------------------------------------------
# Token lifetime alignment (AUTH-08)
# ---------------------------------------------------------------------------


def test_csrf_token_lifetime_exposed() -> None:
    svc = AdminCsrfService(secret="test-secret", token_lifetime=1800)
    assert svc.token_lifetime_seconds == 1800


def test_csrf_token_lifetime_default() -> None:
    svc = AdminCsrfService(secret="test-secret")
    assert svc.token_lifetime_seconds == 3600


# ---------------------------------------------------------------------------
# Content-Type / token-location binding (AUTH-07)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_form_content_type_reads_token_from_body() -> None:
    """application/x-www-form-urlencoded must read token from form body."""
    csrf_service = MagicMock(spec=AdminCsrfService)
    csrf_service.validate_token = MagicMock(return_value=True)

    middleware = AdminCsrfMiddleware(app=MagicMock(), csrf_service=csrf_service)

    scope = _scope(
        method="POST",
        path="/admin/users",
        content_type="application/x-www-form-urlencoded",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    receive = _receive_with_body("csrf_token=valid-token")
    request = _make_request(scope)

    with patch.object(
        request, "form", AsyncMock(return_value={"csrf_token": "valid-token"})
    ):
        result = await middleware._validate_csrf(request)
        assert result is True
        csrf_service.validate_token.assert_called_once()


@pytest.mark.asyncio
async def test_json_content_type_reads_token_from_header() -> None:
    """application/json must read token from X-CSRF-Token header."""
    csrf_service = MagicMock(spec=AdminCsrfService)
    csrf_service.validate_token = MagicMock(return_value=True)

    middleware = AdminCsrfMiddleware(app=MagicMock(), csrf_service=csrf_service)
    scope = _scope(
        method="POST",
        path="/admin/users",
        content_type="application/json",
        headers={
            "content-type": "application/json",
            "X-CSRF-Token": "header-token",
        },
    )
    request = _make_request(scope)

    result = await middleware._validate_csrf(request)
    assert result is True
    csrf_service.validate_token.assert_called_once()


@pytest.mark.asyncio
async def test_json_body_with_form_token_rejected() -> None:
    """Form-style CSRF token in JSON body must be rejected."""
    csrf_service = MagicMock(spec=AdminCsrfService)
    csrf_service.validate_token = MagicMock()
    middleware = AdminCsrfMiddleware(app=MagicMock(), csrf_service=csrf_service)

    scope = _scope(
        method="POST",
        path="/admin/users",
        content_type="application/json",
        headers={"content-type": "application/json"},
    )
    request = _make_request(scope)

    result = await middleware._validate_csrf(request)
    assert result is False
    csrf_service.validate_token.assert_not_called()


@pytest.mark.asyncio
async def test_missing_token_returns_false() -> None:
    csrf_service = MagicMock(spec=AdminCsrfService)
    middleware = AdminCsrfMiddleware(app=MagicMock(), csrf_service=csrf_service)

    scope = _scope(
        method="POST",
        path="/admin/users",
        content_type="application/json",
        headers={"content-type": "application/json"},
    )
    request = _make_request(scope)

    result = await middleware._validate_csrf(request)
    assert result is False


# ---------------------------------------------------------------------------
# Stale pre-login csrf_session_id (AUTH regression)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticated_token_valid_after_login_clears_csrf_session_id() -> None:
    """After login (csrf_session_id cleared) a token bound to admin_user_id
    must validate (settings form 403 regression)."""
    svc = AdminCsrfService(secret="test-secret")
    middleware = AdminCsrfMiddleware(app=MagicMock(), csrf_service=svc)

    session = {"admin_user_id": "user-1"}
    scope = _scope(
        method="POST",
        path="/admin/settings/admin.branding",
        content_type="application/x-www-form-urlencoded",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    scope["session"] = session
    request = _make_request(scope)

    # SettingsController._get_csrf_token generates against admin_user_id.
    token = svc.generate_token(session["admin_user_id"])
    with patch.object(request, "form", AsyncMock(return_value={"csrf_token": token})):
        result = await middleware._validate_csrf(request)
        assert result is True


@pytest.mark.asyncio
async def test_pre_login_token_still_valid_when_scope_keyed() -> None:
    """Tokens bound to csrf_session_id (pre-session forms) keep working."""
    svc = AdminCsrfService(secret="test-secret")
    middleware = AdminCsrfMiddleware(app=MagicMock(), csrf_service=svc)

    session = {"csrf_session_id": "pre-login-scope"}
    scope = _scope(
        method="POST",
        path="/admin/password-reset",
        content_type="application/x-www-form-urlencoded",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    scope["session"] = session
    request = _make_request(scope)

    token = svc.generate_token(session["csrf_session_id"])
    with patch.object(request, "form", AsyncMock(return_value={"csrf_token": token})):
        result = await middleware._validate_csrf(request)
        assert result is True


@pytest.mark.asyncio
async def test_settings_form_token_accepted_with_both_session_keys() -> None:
    """Prod stale-session scenario: csrf_session_id AND admin_user_id present;
    a token generated by SettingsController must validate through the real
    middleware (settings 403 regression, end-to-end)."""
    from lexigram.admin.controllers.settings import SettingsController
    from lexigram.admin.settings.panel.registry import ConfigRegistry

    svc = AdminCsrfService(secret="test-secret")
    middleware = AdminCsrfMiddleware(app=MagicMock(), csrf_service=svc)
    session = {"csrf_session_id": "stale-pre-login", "admin_user_id": "user-1"}

    controller = SettingsController(
        renderer=MagicMock(),
        csrf_service=svc,
        registry=ConfigRegistry.with_defaults(),
    )
    token_req = MagicMock()
    token_req.session = session
    token = controller._get_csrf_token(token_req)
    assert token is not None

    scope = _scope(
        method="POST",
        path="/admin/settings/admin.branding",
        content_type="application/x-www-form-urlencoded",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    scope["session"] = session
    request = _make_request(scope)

    with patch.object(request, "form", AsyncMock(return_value={"csrf_token": token})):
        result = await middleware._validate_csrf(request)
        assert result is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scope(
    method: str = "GET",
    path: str = "/",
    content_type: str = "text/plain",
    headers: dict[str, str] | None = None,
) -> dict:
    hdrs = [(k.encode(), v.encode()) for k, v in (headers or {}).items()]
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": hdrs,
        "session": {"admin_user_id": "test-user"},
        "state": {},
        "query_string": b"",
    }


def _make_request(scope: dict) -> MagicMock:
    req = MagicMock()
    req.headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
    req.url.path = scope.get("path", "/")
    req.session = scope.get("session", {})
    return req


def _receive_with_body(body: str) -> MagicMock:
    async def receive():
        return {"type": "http.request", "body": body.encode()}

    return MagicMock(side_effect=receive)
