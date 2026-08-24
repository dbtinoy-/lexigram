"""E2E HTTP tests for admin auth — profile page flows.

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
from lexigram.admin.controllers.profile import ProfileController
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
    mfa_enabled: bool | None = None,
    state_user: object | None = None,
) -> Starlette:
    controller = AuthController(
        auth_service=_make_auth_service(),
        csrf_service=_make_csrf_service(),
        renderer=_DummyRenderer(),
    )

    profile_controller = ProfileController(
        renderer=_DummyRenderer(),
        csrf_service=_make_csrf_service(),
        mfa_service=MagicMock(),
    )
    profile_controller._mfa_service.is_enabled = AsyncMock(return_value=mfa_enabled)

    async def login_form(request):
        return await controller.login_form(request)

    async def login_submit(request):
        return await controller.login_submit(request)

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
        Route("/admin/", home, methods=["GET"]),
        Route("/admin/profile", profile, methods=["GET"]),
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
async def test_profile_page_renders_account_info() -> None:
    user = MagicMock()
    user.user_id = "user-001"
    user.name = "Ada Admin"
    user.email = "ada@example.com"
    user.roles = ["superadmin"]
    app = create_app(mfa_enabled=True, state_user=user)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/profile")
        assert r.status_code == 200
        assert "Ada Admin" in r.text
        assert "ada@example.com" in r.text
        assert "enabled" in r.text.lower()
        assert "/admin/profile/mfa" in r.text
        assert "/admin/profile/password" in r.text


@pytest.mark.asyncio
async def test_profile_page_redirects_guests_to_login() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        r = await client.get("/admin/profile")
        assert r.status_code == 302
        assert r.headers["location"].startswith("/admin/login")
