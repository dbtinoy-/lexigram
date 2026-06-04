"""E2E HTTP tests for admin MFA self-service (setup / disable flow).

Uses mock protocol implementations at the contract boundary.  The
authenticated-user state normally provided by AuthGuardMiddleware is
injected per-route, mirroring ``request.state.user``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route

from lexigram.admin.auth.types import AdminAuthResult
from lexigram.admin.controllers.auth import AuthController
from lexigram.result import Err, Ok

# ---------------------------------------------------------------------------
# Fakes / mocks at protocol boundary
# ---------------------------------------------------------------------------


def _make_auth_service() -> MagicMock:
    """Return a mock AdminAuthServiceProtocol (plain, no MFA)."""
    svc = MagicMock()
    auth_result = AdminAuthResult(
        session_id="session-abc",
        user_id="user-001",
        email="admin@example.com",
        roles=["superadmin"],
        expires_at=__import__("datetime").datetime(2099, 1, 1, tzinfo=__import__("datetime").timezone.utc),
    )
    svc.authenticate = AsyncMock(return_value=Ok(auth_result))
    svc.invalidate_session = AsyncMock(return_value=None)
    return svc


def _make_csrf_service(*, valid: bool = True) -> MagicMock:
    """Return a mock AdminCsrfServiceProtocol."""
    svc = MagicMock()
    svc.generate_token = MagicMock(return_value="csrf-test-token")
    svc.validate_token = MagicMock(return_value=valid)
    return svc


def _make_mfa_service(
    *, enabled: bool = False, confirm_ok: bool = True, disable_ok: bool = True
) -> MagicMock:
    """Return a mock AdminMfaServiceProtocol."""
    svc = MagicMock()
    svc.is_enabled = AsyncMock(return_value=enabled)
    svc.start_setup = AsyncMock(
        return_value=Ok(
            (
                "JBSWY3DPEHPK3PXP",
                "otpauth://totp/Lexigram%20Admin:admin%40example.com?secret=JBSWY3DPEHPK3PXP&issuer=Lexigram%20Admin",
                "<svg>qr</svg>",
            )
        )
    )
    if confirm_ok:
        svc.confirm_setup = AsyncMock(return_value=Ok(None))
    else:
        from lexigram.admin.auth.errors import MfaVerificationFailedError

        svc.confirm_setup = AsyncMock(
            return_value=Err(MfaVerificationFailedError("Invalid verification code."))
        )
    if disable_ok:
        svc.disable = AsyncMock(return_value=Ok(True))
    else:
        from lexigram.admin.auth.errors import MfaVerificationFailedError

        svc.disable = AsyncMock(
            return_value=Err(MfaVerificationFailedError("Invalid verification code."))
        )
    return svc


class _DummyRenderer:
    def render_page(self, content, request=None, title=None, breadcrumbs=None):
        from starlette.responses import PlainTextResponse

        return PlainTextResponse(str(content))


def _set_user(request) -> None:
    """Mirror AuthGuardMiddleware: populate request.state.user from session."""
    if request.session.get("admin_user_id"):
        request.state.user = SimpleNamespace(
            user_id=request.session["admin_user_id"],
            email=request.session.get("admin_user_email", ""),
            roles=[],
        )


def create_app(
    *,
    mfa_enabled: bool = False,
    confirm_ok: bool = True,
    disable_ok: bool = True,
    csrf_valid: bool = True,
) -> Starlette:
    controller = AuthController(
        auth_service=_make_auth_service(),
        csrf_service=_make_csrf_service(valid=csrf_valid),
        renderer=_DummyRenderer(),
        mfa_service=_make_mfa_service(
            enabled=mfa_enabled, confirm_ok=confirm_ok, disable_ok=disable_ok
        ),
    )

    async def login_form(request):
        return await controller.login_form(request)

    async def login_submit(request):
        return await controller.login_submit(request)

    async def profile_form(request):
        _set_user(request)
        return await controller.mfa_profile_form(request)

    async def setup_submit(request):
        _set_user(request)
        return await controller.mfa_setup_submit(request)

    async def disable_submit(request):
        _set_user(request)
        return await controller.mfa_disable_submit(request)

    routes = [
        Route("/admin/login", login_form, methods=["GET"]),
        Route("/admin/login", login_submit, methods=["POST"]),
        Route("/admin/profile/mfa", profile_form, methods=["GET"]),
        Route("/admin/profile/mfa/setup", setup_submit, methods=["POST"]),
        Route("/admin/profile/mfa/disable", disable_submit, methods=["POST"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")
    return app


async def _login(client: AsyncClient) -> None:
    """Establish an authenticated session via the plain login flow."""
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mfa_profile_shows_setup_qr_when_disabled() -> None:
    """GET /admin/profile/mfa with 2FA off shows QR code and confirm form."""
    app = create_app(mfa_enabled=False)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        await _login(client)
        r = await client.get("/admin/profile/mfa")
        assert r.status_code == 200
        assert "Enable 2FA" in r.text
        assert "svg" in r.text
        assert "JBSWY3DPEHPK3PXP" in r.text


@pytest.mark.asyncio
async def test_mfa_profile_shows_disable_form_when_enabled() -> None:
    """GET /admin/profile/mfa with 2FA on shows the disable form."""
    app = create_app(mfa_enabled=True)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        await _login(client)
        r = await client.get("/admin/profile/mfa")
        assert r.status_code == 200
        assert "Disable 2FA" in r.text
        assert "/admin/profile/mfa/disable" in r.text


@pytest.mark.asyncio
async def test_mfa_setup_confirm_redirects_notice() -> None:
    """A valid confirm code enables 2FA and redirects with a notice."""
    app = create_app(mfa_enabled=False, confirm_ok=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await _login(client)
        await client.get("/admin/profile/mfa")
        r = await client.post(
            "/admin/profile/mfa/setup",
            data={"code": "123456", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "notice=" in r.headers["location"]
        assert "/admin/profile/mfa" in r.headers["location"]


@pytest.mark.asyncio
async def test_mfa_setup_invalid_code_redirects_error() -> None:
    """An invalid confirm code does not enable 2FA and shows an error."""
    app = create_app(mfa_enabled=False, confirm_ok=False)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await _login(client)
        await client.get("/admin/profile/mfa")
        r = await client.post(
            "/admin/profile/mfa/setup",
            data={"code": "000000", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


@pytest.mark.asyncio
async def test_mfa_disable_redirects_notice() -> None:
    """A valid current code disables 2FA and redirects with a notice."""
    app = create_app(mfa_enabled=True, disable_ok=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await _login(client)
        r = await client.post(
            "/admin/profile/mfa/disable",
            data={"code": "123456", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "notice=" in r.headers["location"]


@pytest.mark.asyncio
async def test_mfa_disable_invalid_code_redirects_error() -> None:
    """An invalid code cannot disable 2FA."""
    app = create_app(mfa_enabled=True, disable_ok=False)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await _login(client)
        r = await client.post(
            "/admin/profile/mfa/disable",
            data={"code": "000000", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


@pytest.mark.asyncio
async def test_mfa_profile_redirects_login_when_unauthenticated() -> None:
    """The profile page without a session redirects to login."""
    app = create_app(mfa_enabled=False)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        r = await client.get("/admin/profile/mfa")
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/login?next=/admin/profile/mfa"
