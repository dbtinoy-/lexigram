"""E2E HTTP tests for admin auth — login flows.

Uses mock protocol implementations at the contract boundary.
"""

from __future__ import annotations

import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from lexigram.admin.auth.types import AdminAuthResult
from lexigram.admin.controllers.auth import AuthController
from lexigram.admin.controllers.profile import ProfileController
from lexigram.result import Ok
from lexigram.serialization import loads


def _session_dict(set_cookie: str) -> dict:
    """Decode the Starlette signed-but-unencrypted session cookie."""
    raw = set_cookie.split("session=", 1)[1].split(";", 1)[0]
    data = raw.split(".", 1)[0]
    padded = data + "=" * (-len(data) % 4)
    return loads(base64.urlsafe_b64decode(padded))


def _make_auth_service(
    *,
    authenticated: bool = True,
    mfa_required: bool = False,
    mfa_code_valid: bool = True,
) -> MagicMock:
    svc = MagicMock()
    if authenticated:
        auth_result = AdminAuthResult(
            session_id="" if mfa_required else "session-abc",
            user_id="user-001",
            email="admin@example.com",
            roles=["superadmin"],
            expires_at=__import__("datetime").datetime(
                2099, 1, 1, tzinfo=__import__("datetime").timezone.utc
            ),
            mfa_required=mfa_required,
        )
        svc.authenticate = AsyncMock(return_value=Ok(auth_result))
        if mfa_required:
            full_result = AdminAuthResult(
                session_id="session-mfa",
                user_id="user-001",
                email="admin@example.com",
                roles=["superadmin"],
                expires_at=__import__("datetime").datetime(
                    2099, 1, 1, tzinfo=__import__("datetime").timezone.utc
                ),
            )
            if mfa_code_valid:
                svc.complete_mfa_login = AsyncMock(return_value=Ok(full_result))
            else:
                from lexigram.admin.auth.errors import MfaVerificationFailedError
                from lexigram.result import Err

                svc.complete_mfa_login = AsyncMock(
                    return_value=Err(
                        MfaVerificationFailedError("Invalid verification code.")
                    )
                )
    else:
        from lexigram.admin.auth.errors import InvalidCredentialsError
        from lexigram.result import Err

        svc.authenticate = AsyncMock(return_value=Err(InvalidCredentialsError()))
    svc.invalidate_session = AsyncMock(return_value=None)
    return svc


def _make_csrf_service(*, valid: bool = True) -> MagicMock:
    svc = MagicMock()
    svc.generate_token = MagicMock(return_value="csrf-test-token")
    svc.validate_token = MagicMock(return_value=valid)
    return svc


class _DummyRenderer:
    def render_page(self, content, request=None, title=None, breadcrumbs=None):
        return PlainTextResponse(str(content))


def create_app(
    *,
    authenticated: bool = True,
    csrf_valid: bool = True,
    mfa_required: bool = False,
    mfa_code_valid: bool = True,
    registration_enabled: bool = False,
    mfa_enabled: bool | None = None,
    state_user: object | None = None,
    user_routes: bool = False,
) -> Starlette:
    controller = AuthController(
        auth_service=_make_auth_service(
            authenticated=authenticated,
            mfa_required=mfa_required,
            mfa_code_valid=mfa_code_valid,
        ),
        csrf_service=_make_csrf_service(valid=csrf_valid),
        renderer=_DummyRenderer(),
    )
    controller._registration_enabled = registration_enabled
    if mfa_enabled is not None:
        mfa_service = MagicMock()
        mfa_service.is_enabled = AsyncMock(return_value=mfa_enabled)
        controller._mfa_service = mfa_service

    profile_controller = ProfileController(
        renderer=_DummyRenderer(),
        csrf_service=_make_csrf_service(valid=csrf_valid),
        mfa_service=MagicMock(),
    )
    profile_controller._mfa_service.is_enabled = AsyncMock(return_value=mfa_enabled)

    async def login_form(request):
        return await controller.login_form(request)

    async def login_submit(request):
        return await controller.login_submit(request)

    async def logout(request):
        return await controller.logout(request)

    async def profile(request):
        return await profile_controller.profile_page(request)

    async def home(request):
        if request.session.get("admin_user_id"):
            from starlette.responses import PlainTextResponse

            return PlainTextResponse("home")
        from starlette.responses import RedirectResponse

        return RedirectResponse("/admin/login", status_code=302)

    routes = [
        Route("/admin/login", login_form, methods=["GET"]),
        Route("/admin/login", login_submit, methods=["POST"]),
        Route("/admin/logout", logout, methods=["GET"]),
        Route("/admin/", home, methods=["GET"]),
    ]
    if user_routes:
        routes.append(Route("/admin/profile", profile, methods=["GET"]))

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")

    if user_routes:

        class _StateUserMiddleware:
            def __init__(self, inner):
                self.inner = inner

            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":
                    scope.setdefault("state", {})["user"] = state_user
                await self.inner(scope, receive, send)

        if state_user is not None:
            app.add_middleware(_StateUserMiddleware)
    return app


@pytest.mark.asyncio
async def test_get_login_form_returns_200() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        r = await client.get("/admin/login")
        assert r.status_code == 200
        assert "csrf-test-token" in r.text


@pytest.mark.asyncio
async def test_login_logout_cycle() -> None:
    app = create_app(authenticated=True, csrf_valid=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        r = await client.get("/admin/login")
        assert r.status_code == 200

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

        session = _session_dict(r.headers["set-cookie"])
        assert session["admin_user_id"] == "user-001"
        expires_at = session["admin_session_expires_at"]
        assert datetime.fromisoformat(expires_at).tzinfo is not None

        assert "csrf_session_id" not in session

        r2 = await client.get("/admin/logout")
        assert r2.status_code == 302


@pytest.mark.asyncio
async def test_login_with_invalid_credentials_redirects_with_error() -> None:
    app = create_app(authenticated=False, csrf_valid=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
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
    app = create_app(authenticated=True, csrf_valid=False)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
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


@pytest.mark.asyncio
async def test_login_page_shows_password_reset_link() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/login")
        assert r.status_code == 200
        assert "/admin/password-reset" in r.text


@pytest.mark.asyncio
async def test_login_page_hides_register_link_when_disabled() -> None:
    app = create_app(registration_enabled=False)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/login")
        assert "/admin/register" not in r.text


@pytest.mark.asyncio
async def test_login_page_shows_register_link_when_enabled() -> None:
    app = create_app(registration_enabled=True)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/login")
        assert r.status_code == 200
        assert "/admin/register" in r.text
