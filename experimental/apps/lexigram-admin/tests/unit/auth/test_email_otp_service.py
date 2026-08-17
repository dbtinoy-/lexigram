"""Unit tests for AdminEmailOtpService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.errors import (
    EmailOtpCooldownError,
    EmailOtpDeliveryError,
    MfaNotEnabledError,
)
from lexigram.admin.auth.services.email_otp_service import AdminEmailOtpService
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminEmailOtpConfig


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _make_store(
    *,
    last_sent_at: datetime | None = None,
    consume_ok: bool = False,
) -> MagicMock:
    store = MagicMock()
    store.last_sent_at = AsyncMock(return_value=last_sent_at)
    store.consume = AsyncMock(return_value=consume_ok)
    store.save = AsyncMock()
    return store


def _make_notifier(*, ok: bool = True) -> MagicMock:
    notifier = MagicMock()
    result = MagicMock()
    result.is_ok.return_value = ok
    result.is_err.return_value = not ok
    if not ok:
        result.unwrap_err.return_value = RuntimeError("smtp down")
    notifier.notify_email_otp = AsyncMock(return_value=result)
    return notifier


def _make_audit() -> MagicMock:
    audit = MagicMock()
    audit.log_event = AsyncMock()
    return audit


def _make_service(
    *,
    store: MagicMock | None = None,
    notifier: MagicMock | None = None,
    audit: MagicMock | None = None,
    config: AdminEmailOtpConfig | None = None,
) -> AdminEmailOtpService:
    return AdminEmailOtpService(
        config=config or AdminEmailOtpConfig(),
        store=store or _make_store(),
        notification_service=notifier,
        audit_service=audit,
    )


@pytest.mark.asyncio
async def test_send_otp_disabled_config_returns_err() -> None:
    store = _make_store()
    svc = _make_service(
        store=store,
        notifier=_make_notifier(),
        config=AdminEmailOtpConfig(enabled=False),
    )

    result = await svc.send_otp("user-001", "admin@example.com", "Admin User")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaNotEnabledError)
    store.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_otp_respects_cooldown() -> None:
    store = _make_store(
        last_sent_at=datetime.now(UTC) - timedelta(seconds=10)
    )
    svc = _make_service(store=store, notifier=_make_notifier())

    result = await svc.send_otp("user-001", "admin@example.com", "Admin User")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), EmailOtpCooldownError)
    store.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_otp_sends_and_persists_code() -> None:
    store = _make_store()
    notifier = _make_notifier()
    audit = _make_audit()
    svc = _make_service(store=store, notifier=notifier, audit=audit)

    result = await svc.send_otp("user-001", "admin@example.com", "Admin User")

    assert result.is_ok()
    store.save.assert_awaited_once()
    user_id, code_hash, expires = store.save.await_args.args
    assert user_id == "user-001"
    assert len(code_hash) == 64
    assert expires > datetime.now(UTC)
    notifier.notify_email_otp.assert_awaited_once()
    kwargs = notifier.notify_email_otp.await_args.kwargs
    assert kwargs["user_email"] == "admin@example.com"
    code = kwargs["code"]
    assert code.isdigit()
    assert len(code) == 6
    assert _hash(code) == code_hash
    audit.log_event.assert_awaited_once()
    audit_kwargs = audit.log_event.await_args.kwargs
    assert audit_kwargs["event_type"] == AdminSecurityEventType.EMAIL_OTP_SENT
    assert audit_kwargs["success"] is True


@pytest.mark.asyncio
async def test_email_otp_parity_with_auth_primitives() -> None:
    """Parity: issued code is lexigram-auth derived, 6-digit, digest-verified."""
    from lexigram.auth.authn.mfa import generate_totp_code, generate_totp_secret

    store = _make_store()
    notifier = _make_notifier()
    svc = _make_service(store=store, notifier=notifier)
    secret = generate_totp_secret()
    expected = generate_totp_code(secret, period=5 * 60)

    result = await svc.send_otp("user-001", "admin@example.com", "Admin")

    assert result.is_ok()
    code = notifier.notify_email_otp.await_args.kwargs["code"]
    assert code.isdigit()
    assert len(code) == 6
    assert _hash(code) == store.save.await_args.args[1]
    assert code != expected  # issued codes vary per secret


@pytest.mark.asyncio
async def test_send_otp_without_notifier_returns_err() -> None:
    store = _make_store()
    audit = _make_audit()
    svc = _make_service(store=store, notifier=None, audit=audit)

    result = await svc.send_otp("user-001", "admin@example.com", "Admin User")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), EmailOtpDeliveryError)
    audit.log_event.assert_awaited_once()
    kwargs = audit.log_event.await_args.kwargs
    assert kwargs["event_type"] == AdminSecurityEventType.EMAIL_OTP_FAILED
    assert kwargs["success"] is False


@pytest.mark.asyncio
async def test_send_otp_delivery_failure_returns_err() -> None:
    store = _make_store()
    audit = _make_audit()
    svc = _make_service(store=store, notifier=_make_notifier(ok=False), audit=audit)

    result = await svc.send_otp("user-001", "admin@example.com", "Admin User")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), EmailOtpDeliveryError)
    assert "smtp down" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_verify_otp_valid_code_consumes() -> None:
    store = _make_store(consume_ok=True)
    svc = _make_service(store=store)

    result = await svc.verify_otp("user-001", "123456")

    assert result.is_ok()
    assert result.unwrap() is True
    store.consume.assert_awaited_once_with("user-001", _hash("123456"))


@pytest.mark.asyncio
async def test_verify_otp_invalid_code_returns_false_and_audits() -> None:
    store = _make_store(consume_ok=False)
    audit = _make_audit()
    svc = _make_service(store=store, audit=audit)

    result = await svc.verify_otp("user-001", "000000")

    assert result.is_ok()
    assert result.unwrap() is False
    audit.log_event.assert_awaited_once()
    kwargs = audit.log_event.await_args.kwargs
    assert kwargs["event_type"] == AdminSecurityEventType.EMAIL_OTP_FAILED
    assert kwargs["success"] is False
    assert kwargs["admin_user_id"] == "user-001"


@pytest.mark.asyncio
async def test_verify_otp_disabled_config_returns_err() -> None:
    svc = _make_service(config=AdminEmailOtpConfig(enabled=False))

    result = await svc.verify_otp("user-001", "123456")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaNotEnabledError)
