"""Unit tests for the admin MFA (TOTP 2FA) config."""

from __future__ import annotations

import pytest

from lexigram.admin.config import AdminAuthConfig, AdminConfig, AdminMfaConfig


def test_admin_mfa_config_defaults() -> None:
    cfg = AdminConfig()
    assert cfg.auth.mfa.enabled is True
    assert cfg.auth.mfa.issuer == "Lexigram Admin"
    assert cfg.auth.mfa.skew == 1


def test_admin_mfa_config_is_enabled_by_default() -> None:
    mfa = AdminMfaConfig()
    assert mfa.enabled is True


def test_admin_mfa_config_override() -> None:
    cfg = AdminConfig(
        auth=AdminAuthConfig(
            mfa=AdminMfaConfig(enabled=False, issuer="My App", skew=2)
        )
    )
    assert cfg.auth.mfa.enabled is False
    assert cfg.auth.mfa.issuer == "My App"
    assert cfg.auth.mfa.skew == 2


def test_admin_mfa_config_skew_bounds() -> None:
    with pytest.raises(ValueError, match="skew"):
        AdminMfaConfig(skew=-1)
    with pytest.raises(ValueError, match="skew"):
        AdminMfaConfig(skew=3)
