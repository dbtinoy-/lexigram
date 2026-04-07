"""E2E HTTP tests for admin auth controller (login / logout flow).

Uses mock protocol implementations at the contract boundary.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from lexigram.admin.auth.types import AdminAuthResult
from lexigram.admin.controllers.auth import AuthController
from lexigram.result import Ok

# ---------------------------------------------------------------------------
# Fakes / mocks at protocol boundary
# ---------------------------------------------------------------------------


def _make_auth_service(*, authenticated: bool = True) -> MagicMock:
    """Return a mock AdminAuthServiceProtocol."""
    svc = MagicMock()
    if authenticated:
        auth_result = AdminAuthResult(
            session_id="session-abc",
            user_id="user-001",
            email="admin@example.com",
            roles=["superadmin"],
            expires_at=__import__("datetime").datetime(2099, 1, 1, tzinfo=__import__("datetime").timezone.utc),
        )
        svc.authenticate = AsyncMock(return_value=Ok(auth_result))
    else:
        from lexigram.admin.auth.errors import InvalidCredentialsError
        from lexigram.result import Err

        svc.authenticate = AsyncMock(return_value=Err(InvalidCredentialsError()))
    svc.invalidate_session = AsyncMock(return_value=None)
    return svc


def _make_csrf_service(*, valid: bool = True) -> MagicMock:
    """Return a mock AdminCsrfServiceProtocol."""
    svc = MagicMock()
    svc.generate_token = MagicMock(return_value="csrf-test-token")
    svc.validate_token = MagicMock(return_value=valid)
    return svc


class _DummyRenderer:
    def render_page(self, content, request=None, title=None, breadcrumbs=None):
        return PlainTextResponse(str(content))


def create_app(*, authenticated: bool = True, csrf_valid: bool = True) -> Starlette:
    controller = AuthController(
        auth_service=_make_auth_service(authenticated=authenticated),
        csrf_service=_make_csrf_service(valid=csrf_valid),
        renderer=_DummyRenderer(),
    )

    async def login_form(request):
        return await controller.login_form(request)

    async def login_submit(request):
        return await controller.login_submit(request)

    async def logout(request):
        return await controller.logout(request)

    routes = [
        Route("/admin/login", login_form, methods=["GET"]),
        Route("/admin/login", login_submit, methods=["POST"]),
        Route("/admin/logout", logout, methods=["GET"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_login_form_returns_200() -> None:
    """GET /admin/login should return 200 with CSRF token embedded."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver", follow_redirects=False
    ) as client:
        r = await client.get("/admin/login")
        assert r.status_code == 200
        assert "csrf-test-token" in r.text


@pytest.mark.asyncio
async def test_login_logout_cycle() -> None:
    """Successful login sets session cookie; logout clears it."""
    app = create_app(authenticated=True, csrf_valid=True)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver", follow_redirects=False
    ) as client:
        # GET login page
        r = await client.get("/admin/login")
        assert r.status_code == 200

        # POST valid credentials with CSRF token
        r = await client.post(
            "/admin/login",
            data={
                "email": "admin@example.com",
                "password": "MyStr0ng!Pass@word",
                "csrf_token": "csrf-test-token",
                "next": "/admin/",
            },
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/"
        assert "session" in r.headers.get("set-cookie", "")

        # Logout
        r2 = await client.get("/admin/logout")
        assert r2.status_code == 302


@pytest.mark.asyncio
async def test_login_with_invalid_credentials_redirects_with_error() -> None:
    """Failed login redirects back to login with error param."""
    app = create_app(authenticated=False, csrf_valid=True)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver", follow_redirects=False
    ) as client:
        r = await client.post(
            "/admin/login",
            data={
                "email": "admin@example.com",
                "password": "wrong",
                "csrf_token": "csrf-test-token",
                "next": "/admin/",
            },
        )
        assert r.status_code == 302
        assert "error=" in r.headers.get("location", "")


@pytest.mark.asyncio
async def test_login_with_invalid_csrf_redirects_with_error() -> None:
    """Invalid CSRF token on POST /login redirects with error."""
    app = create_app(authenticated=True, csrf_valid=False)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver", follow_redirects=False
    ) as client:
        r = await client.post(
            "/admin/login",
            data={
                "email": "admin@example.com",
                "password": "MyStr0ng!Pass@word",
                "csrf_token": "bad-token",
                "next": "/admin/",
            },
        )
        assert r.status_code == 302
        assert "error=" in r.headers.get("location", "")
