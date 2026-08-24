"""E2E HTTP tests for admin auth — open redirect hardening.

Uses mock protocol implementations at the contract boundary.
"""

from __future__ import annotations

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
    state_user: object | None = None,
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

    async def home(request):
        if request.session.get("admin_user_id"):
            from starlette.responses import PlainTextResponse

            return PlainTextResponse("home")
        from starlette.responses import RedirectResponse

        return RedirectResponse("/admin/login", status_code=302)

    routes = [
        Route("/admin/login", login_form, methods=["GET"]),
        Route("/admin/login", login_submit, methods=["POST"]),
        Route("/admin/", home, methods=["GET"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")

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
async def test_open_redirect_authenticated_visitor_gets_safe_location() -> None:
    user = MagicMock()
    user.user_id = "user-001"
    user.roles = ["superadmin"]
    app = create_app(state_user=user)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        r = await client.get("/admin/login?next=https://attacker.example/phish")
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/"


@pytest.mark.asyncio
async def test_open_redirect_post_login_rejects_scheme_relative_next() -> None:
    app = create_app(authenticated=True, csrf_valid=True)
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
                "next": "//attacker.example/phish",
            },
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/"


@pytest.mark.asyncio
async def test_open_redirect_post_login_keeps_legitimate_relative_next() -> None:
    app = create_app(authenticated=True, csrf_valid=True)
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
                "next": "/admin/profile/mfa",
            },
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/profile/mfa"


@pytest.mark.asyncio
async def test_open_redirect_mfa_sink_revalidates_poisoned_session() -> None:
    controller = AuthController(
        auth_service=_make_auth_service(authenticated=True, mfa_required=True),
        csrf_service=_make_csrf_service(valid=True),
        renderer=_DummyRenderer(),
    )

    async def login_form(request):
        return await controller.login_form(request)

    async def login_submit(request):
        return await controller.login_submit(request)

    async def poisoned_challenge_submit(request):
        request.session["mfa_pending_next"] = "//attacker.example/phish"
        return await controller.mfa_challenge_submit(request)

    app = Starlette(
        routes=[
            Route("/admin/login", login_form, methods=["GET"]),
            Route("/admin/login", login_submit, methods=["POST"]),
            Route("/admin/login/2fa", poisoned_challenge_submit, methods=["POST"]),
        ]
    )
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")
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
                "next": "/admin/profile/mfa",
            },
        )
        r = await client.post(
            "/admin/login/2fa",
            data={"code": "123456", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/"


@pytest.mark.asyncio
async def test_open_redirect_mfa_sink_keeps_legitimate_pending_next() -> None:
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
                "next": "/admin/profile/mfa",
            },
        )
        r = await client.post(
            "/admin/login/2fa",
            data={"code": "123456", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/profile/mfa"
