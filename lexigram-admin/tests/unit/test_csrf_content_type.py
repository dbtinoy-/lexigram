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

    with patch.object(request, "form", AsyncMock(return_value={"csrf_token": "valid-token"})):
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
