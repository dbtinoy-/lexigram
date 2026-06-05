"""Unit tests for AdminEmailVerificationService."""

from __future__ import annotations

import hashlib
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.errors import EmailVerificationTokenInvalidError
from lexigram.admin.auth.services.email_verification_service import (
    AdminEmailVerificationService,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminEmailVerificationConfig


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_store(
    *,
    verified: bool = False,
    user_id_by_token: str | None = None,
    consume_ok: bool = True,
) -> MagicMock:
    store = MagicMock()
    store.is_verified = AsyncMock(return_value=verified)
    store.find_user_by_token_hash = AsyncMock(return_value=user_id_by_token)
    store.consume_token = AsyncMock(return_value=consume_ok)
    store.save_token = AsyncMock()
    store.clear_token = AsyncMock()
    return store


def _make_notifier() -> MagicMock:
    notifier = MagicMock()
    ok_result = MagicMock()
    ok_result.is_ok.return_value = True
    ok_result.is_err.return_value = False
    notifier.notify_email_verification = AsyncMock(return_value=ok_result)
    return notifier


def _make_audit() -> MagicMock:
    audit = MagicMock()
    audit.log_event = AsyncMock()
    return audit


@pytest.mark.asyncio
async def test_is_verified_delegates() -> None:
    store = _make_store(verified=True)
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(), store=store
    )

    assert await svc.is_verified("user-001") is True
    store.is_verified.assert_awaited_once_with("user-001")


@pytest.mark.asyncio
async def test_is_required_true_when_unverified_and_enforced() -> None:
    store = _make_store(verified=False)
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(), store=store
    )

    assert await svc.is_required("user-001") is True


@pytest.mark.asyncio
async def test_is_required_false_when_verified() -> None:
    store = _make_store(verified=True)
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(), store=store
    )

    assert await svc.is_required("user-001") is False


@pytest.mark.asyncio
async def test_is_required_false_when_enforcement_disabled() -> None:
    store = _make_store(verified=False)
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(enforcement=False), store=store
    )

    assert await svc.is_required("user-001") is False


@pytest.mark.asyncio
async def test_is_required_false_when_flow_disabled() -> None:
    store = _make_store(verified=False)
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(enabled=False), store=store
    )

    assert await svc.is_required("user-001") is False


@pytest.mark.asyncio
async def test_send_verification_noops_when_already_verified() -> None:
    store = _make_store(verified=True)
    notifier = _make_notifier()
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(),
        store=store,
        notification_service=notifier,
    )

    result = await svc.send_verification(
        "user-001", "admin@example.com", "Admin User"
    )

    assert result.is_ok()
    store.save_token.assert_not_awaited()
    notifier.notify_email_verification.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_verification_saves_token_and_notifies() -> None:
    store = _make_store(verified=False)
    notifier = _make_notifier()
    audit = _make_audit()
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(),
        store=store,
        notification_service=notifier,
        audit_service=audit,
    )

    result = await svc.send_verification(
        "user-001", "admin@example.com", "Admin User", base_url="http://panel"
    )

    assert result.is_ok()
    store.save_token.assert_awaited_once()
    user_id, token_hash, _expires = store.save_token.await_args.args
    assert user_id == "user-001"
    assert len(token_hash) == 64
    notifier.notify_email_verification.assert_awaited_once()
    kwargs = notifier.notify_email_verification.await_args.kwargs
    assert kwargs["user_email"] == "admin@example.com"
    verify_url = kwargs["verify_url"]
    assert verify_url.startswith("http://panel/admin/verify-email/")
    token = verify_url.rsplit("/", 1)[1]
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", token)
    assert _hash(token) == token_hash
    audit.log_event.assert_awaited_once()
    kwargs = audit.log_event.await_args.kwargs
    assert kwargs["event_type"] == AdminSecurityEventType.EMAIL_VERIFICATION_SENT
    assert kwargs["success"] is True
    assert kwargs["admin_user_id"] == "user-001"


@pytest.mark.asyncio
async def test_send_verification_fails_open_without_notifier() -> None:
    store = _make_store(verified=False)
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(), store=store
    )

    result = await svc.send_verification(
        "user-001", "admin@example.com", "Admin User"
    )

    assert result.is_ok()


@pytest.mark.asyncio
async def test_send_verification_noops_when_flow_disabled() -> None:
    store = _make_store(verified=False)
    notifier = _make_notifier()
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(enabled=False),
        store=store,
        notification_service=notifier,
    )

    result = await svc.send_verification(
        "user-001", "admin@example.com", "Admin User"
    )

    assert result.is_ok()
    store.save_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_token_invalid_returns_err() -> None:
    store = _make_store(user_id_by_token=None)
    audit = _make_audit()
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(), store=store, audit_service=audit
    )

    result = await svc.verify_token("bad-token")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), EmailVerificationTokenInvalidError)
    audit.log_event.assert_awaited_once()
    kwargs = audit.log_event.await_args.kwargs
    assert kwargs["event_type"] == AdminSecurityEventType.EMAIL_VERIFICATION_FAILED
    assert kwargs["success"] is False


@pytest.mark.asyncio
async def test_verify_token_expired_or_used_returns_err() -> None:
    store = _make_store(user_id_by_token="user-001", consume_ok=False)
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(), store=store
    )

    result = await svc.verify_token("stale-token")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), EmailVerificationTokenInvalidError)


@pytest.mark.asyncio
async def test_verify_token_valid_consumes_and_audits() -> None:
    store = _make_store(user_id_by_token="user-001", consume_ok=True)
    audit = _make_audit()
    svc = AdminEmailVerificationService(
        config=AdminEmailVerificationConfig(), store=store, audit_service=audit
    )

    result = await svc.verify_token("valid-token")

    assert result.is_ok()
    assert result.unwrap() is True
    store.consume_token.assert_awaited_once_with("user-001", _hash("valid-token"))
    audit.log_event.assert_awaited_once()
    kwargs = audit.log_event.await_args.kwargs
    assert kwargs["event_type"] == AdminSecurityEventType.EMAIL_VERIFIED
    assert kwargs["success"] is True
    assert kwargs["admin_user_id"] == "user-001"
