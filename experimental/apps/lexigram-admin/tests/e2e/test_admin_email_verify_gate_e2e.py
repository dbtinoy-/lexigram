"""E2E HTTP tests for admin email verification gate.

Uses mock protocol implementations at the contract boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime
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


def _auth_result(**overrides: object) -> AdminAuthResult:
    fields = {
        "session_id": "session-abc",
        "user_id": "user-001",
        "email": "admin@example.com",
        "roles": ["superadmin"],
        "expires_at": datetime(2099, 1, 1, tzinfo=UTC),
    }
    fields.update(overrides)
    return AdminAuthResult(**fields)


def _make_auth_service(
    *, verify_gate: bool = False, mfa_gate: bool = False, complete_ok: bool = True
) -> MagicMock:
    svc = MagicMock()
    if verify_gate:
        svc.authenticate = AsyncMock(
            return_value=Ok(_auth_result(session_id="", email_verification_required=True))
        )
    elif mfa_gate:
        svc.authenticate = AsyncMock(
            return_value=Ok(_auth_result(session_id="", mfa_required=True))
        )
    else:
        svc.authenticate = AsyncMock(return_value=Ok(_auth_result()))
    if complete_ok:
        svc.complete_mfa_login = AsyncMock(return_value=Ok(_auth_result()))
    else:
        from lexigram.admin.auth.errors import MfaVerificationFailedError

        svc.complete_mfa_login = AsyncMock(
            return_value=Err(MfaVerificationFailedError("Invalid verification code."))
        )
    svc.invalidate_session = AsyncMock(return_value=None)
    return svc


def _make_csrf_service(*, valid: bool = True) -> MagicMock:
    svc = MagicMock()
    svc.generate_token = MagicMock(return_value="csrf-test-token")
    svc.validate_token = MagicMock(return_value=valid)
    return svc


def _make_mfa_service(*, factor: str = "totp") -> MagicMock:
    svc = MagicMock()
    svc.get_factor = MagicMock(return_value=factor)
    svc.is_enabled = AsyncMock(return_value=factor == "totp")
    svc.start_setup = AsyncMock(
        return_value=Ok(("SECRET", "otpauth://totp/x", "<svg>qr</svg>"))
    )
    return svc


def _make_verification_service(
    *,
    send_err: bool = False,
    verify_ok: bool = True,
    email_verified: bool = True,
) -> MagicMock:
    svc = MagicMock()
    if send_err:
        from lexigram.admin.auth.errors import RateLimitExceededError

        svc.send_verification = AsyncMock(
            return_value=Err(
                RateLimitExceededError(
                    "Too many verification emails. Please try again later."
                )
            )
        )
    else:
        svc.send_verification = AsyncMock(return_value=Ok(None))
    if verify_ok:
        svc.verify_token = AsyncMock(return_value=Ok(True))
    else:
        from lexigram.admin.auth.errors import EmailVerificationTokenInvalidError

        svc.verify_token = AsyncMock(
            return_value=Err(EmailVerificationTokenInvalidError("Invalid or expired verification link."))
        )
    svc.is_verified = AsyncMock(return_value=email_verified)
    return svc


def _make_otp_service(*, send_err: bool = False, verify_ok: bool = True) -> MagicMock:
    svc = MagicMock()
    if send_err:
        from lexigram.admin.auth.errors import EmailOtpCooldownError

        svc.send_otp = AsyncMock(
            return_value=Err(EmailOtpCooldownError("Please wait before requesting another code."))
        )
    else:
        svc.send_otp = AsyncMock(return_value=Ok(None))
    svc.verify_otp = AsyncMock(return_value=Ok(verify_ok))
    return svc


class _DummyRenderer:
    def render_page(self, content, request=None, title=None, breadcrumbs=None):
        from starlette.responses import PlainTextResponse

        return PlainTextResponse(str(content))


def create_app(
    *,
    verify_gate: bool = False,
    mfa_gate: bool = False,
    factor: str = "totp",
    complete_ok: bool = True,
    send_err: bool = False,
    verify_ok: bool = True,
    otp_send_err: bool = False,
    otp_verify_ok: bool = True,
    email_verified: bool = True,
    csrf_valid: bool = True,
) -> Starlette:
    controller = AuthController(
        auth_service=_make_auth_service(
            verify_gate=verify_gate, mfa_gate=mfa_gate, complete_ok=complete_ok
        ),
        csrf_service=_make_csrf_service(valid=csrf_valid),
        renderer=_DummyRenderer(),
        mfa_service=_make_mfa_service(factor=factor),
        email_verification_service=_make_verification_service(
            send_err=send_err, verify_ok=verify_ok, email_verified=email_verified
        ),
        email_otp_service=_make_otp_service(
            send_err=otp_send_err, verify_ok=otp_verify_ok
        ),
    )

    async def login_form(request):
        return await controller.login_form(request)

    async def login_submit(request):
        return await controller.login_submit(request)

    async def verify_form(request):
        return await controller.verify_email_form(request)

    async def verify_resend(request):
        return await controller.verify_email_resend(request)

    async def verify_token(request):
        return await controller.verify_email_token(request)

    routes = [
        Route("/admin/login", login_form, methods=["GET"]),
        Route("/admin/login", login_submit, methods=["POST"]),
        Route("/admin/verify-email", verify_form, methods=["GET"]),
        Route("/admin/verify-email/resend", verify_resend, methods=["POST"]),
        Route("/admin/verify-email/{token}", verify_token, methods=["GET"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")
    return app


@pytest.mark.asyncio
async def test_login_gated_on_unverified_email_redirects_to_verify() -> None:
    app = create_app(verify_gate=True)
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
        assert r.headers["location"] == "/admin/verify-email"


@pytest.mark.asyncio
async def test_verify_email_page_renders_with_resend_form() -> None:
    app = create_app(verify_gate=True)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        await client.get("/admin/login")
        await client.post(
            "/admin/login",
            data={
                "email": "admin@example.com",
                "password": "x",
                "csrf_token": "csrf-test-token",
                "next": "/admin/",
            },
        )
        r = await client.get("/admin/verify-email")
        assert r.status_code == 200
        assert "Verify Your Email" in r.text
        assert "/admin/verify-email/resend" in r.text


@pytest.mark.asyncio
async def test_verify_email_resend_redirects_notice() -> None:
    app = create_app(verify_gate=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/login")
        await client.post(
            "/admin/login",
            data={"email": "a", "password": "b", "csrf_token": "csrf-test-token"},
        )
        r = await client.post(
            "/admin/verify-email/resend",
            data={
                "email": "admin@example.com",
                "csrf_token": "csrf-test-token",
                "next": "/admin/",
            },
        )
        assert r.status_code == 302
        assert "notice=" in r.headers["location"]


@pytest.mark.asyncio
async def test_verify_email_resend_rate_limited_shows_error() -> None:
    app = create_app(verify_gate=True, send_err=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/login")
        await client.post(
            "/admin/login",
            data={"email": "a", "password": "b", "csrf_token": "csrf-test-token"},
        )
        r = await client.post(
            "/admin/verify-email/resend",
            data={
                "email": "admin@example.com",
                "csrf_token": "csrf-test-token",
                "next": "/admin/",
            },
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


@pytest.mark.asyncio
async def test_verify_email_token_success_renders_confirmation() -> None:
    app = create_app(verify_gate=True)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/verify-email/valid-token-123")
        assert r.status_code == 200
        assert "Email Verified" in r.text


@pytest.mark.asyncio
async def test_verify_email_token_failure_renders_error_page() -> None:
    app = create_app(verify_gate=True, verify_ok=False)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/verify-email/stale-token")
        assert r.status_code == 200
        assert "Verification Failed" in r.text
