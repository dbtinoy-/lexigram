"""E2E HTTP tests for admin auth — MFA / 2FA challenge flows.

Uses mock protocol implementations at the contract boundary.
"""

from __future__ import annotations

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
from lexigram.result import Ok
from lexigram.serialization import loads

import base64


def _session_dict(set_cookie: str) -> dict:
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

    async def login_form(request):
        return await controller.login_form(request)

    async def login_submit(request):
        return await controller.login_submit(request)

    async def challenge_form(request):
        return await controller.mfa_challenge_form(request)

    async def challenge_submit(request):
        return await controller.mfa_challenge_submit(request)

    async def home(request):
        if request.session.get("admin_user_id"):
            from starlette.responses import PlainTextResponse

            return PlainTextResponse("home")
        from starlette.responses import RedirectResponse

        return RedirectResponse("/admin/login", status_code=302)

    routes = [
        Route("/admin/login", login_form, methods=["GET"]),
        Route("/admin/login", login_submit, methods=["POST"]),
        Route("/admin/login/2fa", challenge_form, methods=["GET"]),
        Route("/admin/login/2fa", challenge_submit, methods=["POST"]),
        Route("/admin/", home, methods=["GET"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")
    return app


@pytest.mark.asyncio
async def test_login_requires_2fa_challenge_when_mfa_enabled() -> None:
    app = create_app(authenticated=True, mfa_required=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/login")
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
        assert r.headers["location"] == "/admin/login/2fa"

        r2 = await client.get("/admin/")
        assert r2.status_code == 302

        r3 = await client.get("/admin/login/2fa")
        assert r3.status_code == 200
        assert "csrf-test-token" in r3.text


@pytest.mark.asyncio
async def test_complete_2fa_login_sets_session() -> None:
    app = create_app(authenticated=True, mfa_required=True, mfa_code_valid=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/login")
        await client.post(
            "/admin/login",
            data={
                "email": "admin@example.com",
                "password": "MyStr0ng!Pass@word",
                "csrf_token": "csrf-test-token",
                "next": "/admin/",
            },
        )
        r = await client.post(
            "/admin/login/2fa",
            data={"code": "123456", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/"

        session = _session_dict(r.headers["set-cookie"])
        assert (
            datetime.fromisoformat(session["admin_session_expires_at"]).tzinfo
            is not None
        )

        r2 = await client.get("/admin/")
        assert r2.status_code == 200
        assert r2.text == "home"

        r3 = await client.get("/admin/login/2fa")
        assert r3.status_code == 302
        assert r3.headers["location"] != "/admin/login/2fa"


@pytest.mark.asyncio
async def test_complete_2fa_login_invalid_code_redirects_error() -> None:
    app = create_app(authenticated=True, mfa_required=True, mfa_code_valid=False)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/login")
        await client.post(
            "/admin/login",
            data={
                "email": "admin@example.com",
                "password": "MyStr0ng!Pass@word",
                "csrf_token": "csrf-test-token",
                "next": "/admin/",
            },
        )
        r = await client.post(
            "/admin/login/2fa",
            data={"code": "000000", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "error=" in r.headers.get("location", "")

        r2 = await client.get("/admin/")
        assert r2.status_code == 302


@pytest.mark.asyncio
async def test_2fa_challenge_requires_pending_session() -> None:
    app = create_app(authenticated=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        r = await client.get("/admin/login/2fa")
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/login"
