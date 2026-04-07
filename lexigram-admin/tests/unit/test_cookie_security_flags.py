"""Tests for session cookie security flags (AUTH-01, AUTH-04)."""

from __future__ import annotations

import pytest

from lexigram.admin.auth.services._cookie_config import build_session_cookie_kwargs
from lexigram.admin.config import AdminAuthConfig


def test_production_cookie_is_secure_httponly_strict() -> None:
    cfg = AdminAuthConfig(env="production", session_secret="x" * 64)
    kwargs = build_session_cookie_kwargs(cfg)
    assert kwargs["https_only"] is True
    assert kwargs["same_site"] == "strict"
    assert kwargs["max_age"] == cfg.session_lifetime


def test_development_cookie_relaxes_https_only_but_keeps_samesite() -> None:
    cfg = AdminAuthConfig(env="development", session_secret="x" * 64)
    kwargs = build_session_cookie_kwargs(cfg)
    assert kwargs["https_only"] is False
    assert kwargs["same_site"] == "lax"


def test_production_with_default_secret_refuses_to_build() -> None:
    with pytest.raises(ValueError, match="session_secret"):
        AdminAuthConfig(env="production", session_secret="change-me-in-production")
