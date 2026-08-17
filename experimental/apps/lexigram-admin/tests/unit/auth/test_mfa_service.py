"""Unit tests for AdminMfaService (TOTP lifecycle)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pyotp
import pytest

from lexigram.admin.auth.errors import MfaNotEnabledError, MfaVerificationFailedError
from lexigram.admin.auth.services.mfa_service import AdminMfaService
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminMfaConfig
from lexigram.result import Err


def _make_service(
    *,
    enabled: bool = True,
    secret: str | None = None,
) -> tuple[AdminMfaService, MagicMock, MagicMock]:
    """Build an AdminMfaService with a mocked store and audit service.

    Returns:
        Tuple of (service, store mock, audit mock).
    """
    store = MagicMock()
    store.is_enabled = AsyncMock(return_value=secret is not None)
    store.get_secret = AsyncMock(return_value=secret)
    store.save_secret = AsyncMock(return_value=None)
    store.disable = AsyncMock(return_value=None)
    audit = MagicMock()
    audit.log_event = AsyncMock(return_value=None)
    service = AdminMfaService(
        config=AdminMfaConfig(enabled=enabled, issuer="Lexigram Admin", skew=2),
        store=store,
        audit_service=audit,
    )
    return service, store, audit


@pytest.mark.asyncio
async def test_start_setup_returns_secret_uri_svg() -> None:
    service, store, _ = _make_service()

    result = await service.start_setup("user-001", "admin@example.com")

    assert result.is_ok()
    secret, uri, svg = result.unwrap()
    assert len(secret) == 32
    assert "otpauth://totp/" in uri
    assert "issuer=Lexigram" in uri
    assert svg.startswith("<svg")
    store.get_secret.assert_not_awaited()
    store.save_secret.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_setup_errors_when_config_disabled() -> None:
    service, _, _ = _make_service(enabled=False)

    result = await service.start_setup("user-001", "admin@example.com")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaNotEnabledError)


@pytest.mark.asyncio
async def test_confirm_setup_rejects_invalid_code() -> None:
    service, store, _ = _make_service()
    secret = pyotp.random_base32()

    result = await service.confirm_setup("user-001", secret, "000000")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaVerificationFailedError)
    store.save_secret.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_setup_persists_and_audits() -> None:
    service, store, audit = _make_service()
    secret = pyotp.random_base32()
    code = pyotp.TOTP(secret).now()

    result = await service.confirm_setup("user-001", secret, code)

    assert result.is_ok()
    store.save_secret.assert_awaited_once_with("user-001", secret)
    audit.log_event.assert_awaited_once_with(
        event_type=AdminSecurityEventType.MFA_ENABLED,
        ip_address="",
        user_agent="",
        success=True,
        admin_user_id="user-001",
        metadata={},
    )


@pytest.mark.asyncio
async def test_confirm_setup_errors_when_config_disabled() -> None:
    service, store, _ = _make_service(enabled=False)

    result = await service.confirm_setup("user-001", "SECRET", "000000")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaNotEnabledError)
    store.save_secret.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_code_errors_when_not_enabled() -> None:
    service, _, _ = _make_service(secret=None)

    result = await service.verify_code("user-001", "000000")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaNotEnabledError)


@pytest.mark.asyncio
async def test_verify_code_accepts_live_code() -> None:
    secret = pyotp.random_base32()
    service, _, _ = _make_service(secret=secret)
    code = pyotp.TOTP(secret).now()

    result = await service.verify_code("user-001", code)

    assert result.is_ok()
    assert result.unwrap() is True


@pytest.mark.asyncio
async def test_verify_code_accepts_lexigram_auth_generated_code() -> None:
    """Parity: codes produced by lexigram-auth's own TOTP engine verify."""
    from lexigram.auth.authn.mfa import generate_totp_code, generate_totp_secret

    secret = generate_totp_secret()
    service, _, _ = _make_service(secret=secret)
    code = generate_totp_code(secret)

    result = await service.verify_code("user-001", code)

    assert result.is_ok()
    assert result.unwrap() is True


@pytest.mark.asyncio
async def test_verify_code_rejects_random_code() -> None:
    service, _, _ = _make_service(secret=pyotp.random_base32())

    result = await service.verify_code("user-001", "000000")

    assert result.is_ok()
    assert result.unwrap() is False


@pytest.mark.asyncio
async def test_disable_requires_valid_code() -> None:
    secret = pyotp.random_base32()
    service, store, _ = _make_service(secret=secret)

    result = await service.disable("user-001", "000000")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MfaVerificationFailedError)
    store.disable.assert_not_awaited()


@pytest.mark.asyncio
async def test_disable_with_valid_code_removes_and_audits() -> None:
    secret = pyotp.random_base32()
    service, store, audit = _make_service(secret=secret)
    code = pyotp.TOTP(secret).now()

    result = await service.disable("user-001", code)

    assert result.is_ok()
    assert result.unwrap() is True
    store.disable.assert_awaited_once_with("user-001")
    audit.log_event.assert_awaited_once_with(
        event_type=AdminSecurityEventType.MFA_DISABLED,
        ip_address="",
        user_agent="",
        success=True,
        admin_user_id="user-001",
        metadata={},
    )


@pytest.mark.asyncio
async def test_disable_propagates_not_enabled_error() -> None:
    service, _, _ = _make_service(secret=None)

    direct = await service.disable("user-001", "000000")
    assert isinstance(direct, Err)
    assert isinstance(direct.unwrap_err(), MfaNotEnabledError)
