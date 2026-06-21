"""E2E HTTP tests for the password reset flow (request + confirm pages)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from lexigram.admin.controllers.auth import AuthController
from lexigram.result import Err, Ok


def _make_reset_service(*, ok: bool = True, rate_limited: bool = False) -> MagicMock:
    svc = MagicMock()
    if rate_limited:
        from lexigram.admin.auth.errors import RateLimitExceededError

        svc.request_reset = AsyncMock(
            return_value=Err(RateLimitExceededError("Too many requests."))
        )
        svc.confirm_reset = AsyncMock(return_value=Ok(None))
    elif ok:
        svc.request_reset = AsyncMock(return_value=Ok(None))
        svc.confirm_reset = AsyncMock(return_value=Ok(None))
    else:
        from lexigram.admin.auth.errors import PasswordResetTokenInvalidError

        svc.request_reset = AsyncMock(return_value=Ok(None))
        svc.confirm_reset = AsyncMock(
            return_value=Err(PasswordResetTokenInvalidError())
        )
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
    *, reset_ok: bool = True, csrf_valid: bool = True, rate_limited: bool = False
) -> Starlette:
    controller = AuthController(
        auth_service=MagicMock(),
        csrf_service=_make_csrf_service(valid=csrf_valid),
        renderer=_DummyRenderer(),
        password_reset_service=_make_reset_service(
            ok=reset_ok, rate_limited=rate_limited
        ),
    )

    async def request_form(request):
        return await controller.password_reset_request_form(request)

    async def request_submit(request):
        return await controller.password_reset_request_submit(request)

    async def confirm_form(request):
        return await controller.password_reset_confirm_form(request)

    async def confirm_submit(request):
        return await controller.password_reset_confirm_submit(request)

    routes = [
        Route("/admin/password-reset", request_form, methods=["GET"]),
        Route("/admin/password-reset", request_submit, methods=["POST"]),
        Route("/admin/password-reset/{token}", confirm_form, methods=["GET"]),
        Route("/admin/password-reset/{token}", confirm_submit, methods=["POST"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")
    return app


@pytest.mark.asyncio
async def test_get_request_form_returns_200() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        r = await client.get("/admin/password-reset")
        assert r.status_code == 200
        assert "csrf-test-token" in r.text


@pytest.mark.asyncio
async def test_post_request_redirects_to_sent_notice() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/password-reset")  # establishes csrf session
        r = await client.post(
            "/admin/password-reset",
            data={"email": "admin@example.com", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "sent=1" in r.headers["location"]


@pytest.mark.asyncio
async def test_post_request_invalid_csrf_redirects_with_error() -> None:
    app = create_app(csrf_valid=False)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/password-reset")
        r = await client.post(
            "/admin/password-reset",
            data={"email": "admin@example.com", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


@pytest.mark.asyncio
async def test_post_request_rate_limited_redirects_with_error() -> None:
    app = create_app(rate_limited=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/password-reset")
        r = await client.post(
            "/admin/password-reset",
            data={"email": "admin@example.com", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "sent=1" not in r.headers["location"]
        assert "error=" in r.headers["location"]


@pytest.mark.asyncio
async def test_get_confirm_form_returns_200_with_token() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        r = await client.get("/admin/password-reset/abc-token-123")
        assert r.status_code == 200
        assert "abc-token-123" in r.text
        assert "csrf-test-token" in r.text


@pytest.mark.asyncio
async def test_post_confirm_redirects_to_login_with_notice() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/password-reset/abc-token-123")
        r = await client.post(
            "/admin/password-reset/abc-token-123",
            data={
                "password": "New-Str0ng-Passw0rd!",
                "password_confirmation": "New-Str0ng-Passw0rd!",
                "csrf_token": "csrf-test-token",
            },
        )
        assert r.status_code == 302
        assert "/admin/login" in r.headers["location"]
        assert "notice=" in r.headers["location"]


@pytest.mark.asyncio
async def test_post_confirm_failure_redirects_back_with_error() -> None:
    app = create_app(reset_ok=False)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/password-reset/abc-token-123")
        r = await client.post(
            "/admin/password-reset/abc-token-123",
            data={
                "password": "New-Str0ng-Passw0rd!",
                "password_confirmation": "New-Str0ng-Passw0rd!",
                "csrf_token": "csrf-test-token",
            },
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


@pytest.mark.asyncio
async def test_post_confirm_password_mismatch_redirects_with_error() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/password-reset/abc-token-123")
        r = await client.post(
            "/admin/password-reset/abc-token-123",
            data={
                "password": "New-Str0ng-Passw0rd!",
                "password_confirmation": "Different-Passw0rd!",
                "csrf_token": "csrf-test-token",
            },
        )
        assert r.status_code == 302
        assert "confirmation_err=" in r.headers["location"]
