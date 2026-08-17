"""Unit tests for AdminAuthService email verification gate + factor dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.errors import MfaNotEnabledError, MfaVerificationFailedError
from lexigram.admin.auth.services.auth_service import AdminAuthService
from lexigram.admin.auth.types import AdminAuthResult, AdminSecurityEventType
from lexigram.result import Err, Ok


def _make_user() -> MagicMock:
    user = MagicMock()
    user.user_id = "user-001"
    user.email = "admin@example.com"
    user.roles = ["superadmin"]
    return user


def _make_services(
    *,
    verified: bool = True,
    enforcement: bool = True,
    mfa_enabled: bool = False,
    factor: str = "totp",
    otp_verify_ok: bool | None = None,
    otp_verify_err: bool = False,
) -> tuple[
    MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, AdminAuthService
]:
    user = _make_user()
    user_store = MagicMock()
    user_store.authenticate = AsyncMock(return_value=user)

    attempt = MagicMock()
    attempt.check_ip_rate_limit = AsyncMock()
    attempt.check_account_lockout = AsyncMock()
    attempt.record_attempt = AsyncMock()
    attempt.clear_lockout = AsyncMock()

    audit = MagicMock()
    audit.log_event = AsyncMock()

    session = MagicMock()
    session.create_session = AsyncMock(return_value="session-abc")

    mfa = MagicMock()
    mfa.is_enabled = AsyncMock(return_value=mfa_enabled)
    mfa.verify_code = AsyncMock(return_value=Ok(True))

    verification = MagicMock()
    from lexigram.admin.auth.errors import (
        EmailVerificationTokenInvalidError,
    )

    verification.is_required = AsyncMock(
        return_value=(not verified and enforcement)
    )
    verification.is_verified = AsyncMock(return_value=verified)
    verification.verify_token = AsyncMock(
        return_value=Err(EmailVerificationTokenInvalidError("bad"))
    )

    otp = MagicMock()
    otp.send_otp = AsyncMock(return_value=Ok(None))
    if otp_verify_err:
        otp.verify_otp = AsyncMock(
            return_value=Err(MfaVerificationFailedError("Invalid verification code."))
        )
    elif otp_verify_ok is None:
        otp.verify_otp = AsyncMock(return_value=Ok(False))
    else:
        otp.verify_otp = AsyncMock(return_value=Ok(otp_verify_ok))

    svc = AdminAuthService(
        user_store=user_store,
        attempt_service=attempt,
        audit_service=audit,
        session_service=session,
        mfa_service=mfa,
        email_verification_service=verification,
        email_otp_service=otp,
        mfa_factor=factor,
    )
    return user_store, attempt, audit, session, mfa, otp, svc


@pytest.mark.asyncio
async def test_authenticate_returns_verification_required_when_unverified() -> None:
    _, attempt, audit, session, mfa, _, svc = _make_services(
        verified=False, enforcement=True
    )

    result = await svc.authenticate("admin@example.com", "pw", "1.2.3.4", "ua")

    assert result.is_ok()
    auth_result = result.unwrap()
    assert isinstance(auth_result, AdminAuthResult)
    assert auth_result.email_verification_required is True
    assert auth_result.session_id == ""
    attempt.record_attempt.assert_not_awaited()
    session.create_session.assert_not_awaited()
    mfa.is_enabled.assert_not_awaited()
    audit.log_event.assert_awaited_once()
    kwargs = audit.log_event.await_args.kwargs
    assert kwargs["event_type"] == AdminSecurityEventType.EMAIL_VERIFICATION_SENT
    assert kwargs["success"] is True


@pytest.mark.asyncio
async def test_authenticate_ignores_gate_when_verified() -> None:
    _, attempt, _, session, _, _, svc = _make_services(
        verified=True, enforcement=True
    )

    result = await svc.authenticate("admin@example.com", "pw", "1.2.3.4", "ua")

    assert result.is_ok()
    assert result.unwrap().email_verification_required is False
    assert result.unwrap().session_id == "session-abc"
    attempt.record_attempt.assert_awaited()
    session.create_session.assert_awaited()


@pytest.mark.asyncio
async def test_authenticate_email_factor_issues_challenge() -> None:
    _, attempt, audit, session, mfa, _, svc = _make_services(
        verified=True, factor="email", mfa_enabled=False
    )

    result = await svc.authenticate("admin@example.com", "pw", "1.2.3.4", "ua")

    assert result.is_ok()
    auth_result = result.unwrap()
    assert auth_result.mfa_required is True
    assert auth_result.session_id == ""
    mfa.is_enabled.assert_not_awaited()
    attempt.record_attempt.assert_not_awaited()
    session.create_session.assert_not_awaited()
    audit.log_event.assert_awaited_once()
    kwargs = audit.log_event.await_args.kwargs
    assert kwargs["event_type"] == AdminSecurityEventType.MFA_CHALLENGE_ISSUED


@pytest.mark.asyncio
async def test_authenticate_totp_factor_unchanged() -> None:
    _, attempt, _, session, mfa, _, svc = _make_services(
        verified=True, factor="totp", mfa_enabled=True
    )

    result = await svc.authenticate("admin@example.com", "pw", "1.2.3.4", "ua")

    assert result.is_ok()
    assert result.unwrap().mfa_required is True
    mfa.is_enabled.assert_awaited_once()
    attempt.record_attempt.assert_not_awaited()
    session.create_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_mfa_login_email_factor_valid_code() -> None:
    _, attempt, _, session, _, otp, svc = _make_services(
        verified=True, factor="email", otp_verify_ok=True
    )

    result = await svc.complete_mfa_login(
        "user-001", "admin@example.com", ["superadmin"], "123456", "1.2.3.4", "ua"
    )

    assert result.is_ok()
    auth_result = result.unwrap()
    assert auth_result.session_id == "session-abc"
    otp.verify_otp.assert_awaited_once_with("user-001", "123456")
    attempt.record_attempt.assert_awaited()
    assert attempt.record_attempt.await_args.kwargs["success"] is True
    session.create_session.assert_awaited()


@pytest.mark.asyncio
async def test_complete_mfa_login_email_factor_invalid_code() -> None:
    _, attempt, audit, session, _, otp, svc = _make_services(
        verified=True, factor="email", otp_verify_ok=False
    )

    result = await svc.complete_mfa_login(
        "user-001", "admin@example.com", ["superadmin"], "000000", "1.2.3.4", "ua"
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaVerificationFailedError)
    otp.verify_otp.assert_awaited_once()
    attempt.record_attempt.assert_awaited()
    assert attempt.record_attempt.await_args.kwargs["failure_reason"] == "invalid_mfa_code"
    assert attempt.record_attempt.await_args.kwargs["success"] is False
    session.create_session.assert_not_awaited()
    audit.log_event.assert_awaited()
    events = [c.kwargs["event_type"] for c in audit.log_event.await_args_list]
    assert AdminSecurityEventType.MFA_CHALLENGE_FAILED in events


@pytest.mark.asyncio
async def test_complete_mfa_login_email_factor_verify_err_propagates() -> None:
    _, attempt, _, session, _, _, svc = _make_services(
        verified=True, factor="email", otp_verify_err=True
    )

    result = await svc.complete_mfa_login(
        "user-001", "admin@example.com", ["superadmin"], "123456", "1.2.3.4", "ua"
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaVerificationFailedError)
    attempt.record_attempt.assert_not_awaited()
    session.create_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_mfa_login_no_mfa_services_returns_err() -> None:
    user_store = MagicMock()
    user_store.authenticate = AsyncMock(return_value=_make_user())
    attempt = MagicMock()
    attempt.check_ip_rate_limit = AsyncMock()
    attempt.check_account_lockout = AsyncMock()
    audit = MagicMock()
    audit.log_event = AsyncMock()
    session = MagicMock()
    session.create_session = AsyncMock(return_value="session-abc")
    svc = AdminAuthService(
        user_store=user_store,
        attempt_service=attempt,
        audit_service=audit,
        session_service=session,
        mfa_factor="totp",
    )

    result = await svc.complete_mfa_login(
        "user-001", "admin@example.com", ["superadmin"], "123456", "1.2.3.4", "ua"
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaNotEnabledError)


@pytest.mark.asyncio
async def test_complete_mfa_login_totp_factor_unaffected() -> None:
    _, attempt, _, _, mfa, _, svc = _make_services(
        verified=True, factor="totp", mfa_enabled=True
    )

    result = await svc.complete_mfa_login(
        "user-001", "admin@example.com", ["superadmin"], "123456", "1.2.3.4", "ua"
    )

    assert result.is_ok()
    mfa.verify_code.assert_awaited_once_with("user-001", "123456")
    assert result.unwrap().session_id == "session-abc"
    attempt.record_attempt.assert_awaited()
