"""Unit tests for the admin email verification + email OTP config."""

from __future__ import annotations

import pytest

from lexigram.admin.config import (
    AdminAuthConfig,
    AdminConfig,
    AdminEmailOtpConfig,
    AdminEmailVerificationConfig,
    AdminMfaConfig,
)


def test_admin_mfa_config_factor_defaults_to_totp() -> None:
    cfg = AdminConfig()
    assert cfg.auth.mfa.factor == "totp"


def test_admin_mfa_config_factor_accepts_email() -> None:
    cfg = AdminConfig(
        auth=AdminAuthConfig(mfa=AdminMfaConfig(factor="email"))
    )
    assert cfg.auth.mfa.factor == "email"


def test_admin_email_otp_config_defaults() -> None:
    otp = AdminEmailOtpConfig()
    assert otp.enabled is True
    assert otp.ttl_minutes == 10
    assert otp.resend_cooldown_seconds == 60


def test_admin_email_otp_config_ttl_bounds() -> None:
    with pytest.raises(ValueError, match="ttl_minutes"):
        AdminEmailOtpConfig(ttl_minutes=0)
    with pytest.raises(ValueError, match="ttl_minutes"):
        AdminEmailOtpConfig(ttl_minutes=61)


def test_admin_email_otp_config_cooldown_bounds() -> None:
    with pytest.raises(ValueError, match="resend_cooldown_seconds"):
        AdminEmailOtpConfig(resend_cooldown_seconds=4)
    with pytest.raises(ValueError, match="resend_cooldown_seconds"):
        AdminEmailOtpConfig(resend_cooldown_seconds=601)


def test_admin_email_verification_config_defaults() -> None:
    verification = AdminEmailVerificationConfig()
    assert verification.enabled is True
    assert verification.enforcement is True
    assert verification.token_ttl_hours == 24


def test_admin_email_verification_config_ttl_bounds() -> None:
    with pytest.raises(ValueError, match="token_ttl_hours"):
        AdminEmailVerificationConfig(token_ttl_hours=0)
    with pytest.raises(ValueError, match="token_ttl_hours"):
        AdminEmailVerificationConfig(token_ttl_hours=169)


def test_admin_auth_config_nests_email_settings() -> None:
    cfg = AdminConfig()
    assert isinstance(cfg.auth.email_otp, AdminEmailOtpConfig)
    assert isinstance(cfg.auth.email_verification, AdminEmailVerificationConfig)


def test_admin_auth_config_email_override() -> None:
    cfg = AdminConfig(
        auth=AdminAuthConfig(
            email_otp=AdminEmailOtpConfig(ttl_minutes=5),
            email_verification=AdminEmailVerificationConfig(enforcement=False),
        )
    )
    assert cfg.auth.email_otp.ttl_minutes == 5
    assert cfg.auth.email_verification.enforcement is False
