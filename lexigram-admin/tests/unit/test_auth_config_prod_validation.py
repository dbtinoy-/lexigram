"""Tests for production config validation."""

from __future__ import annotations

import structlog.testing

import pytest


def test_production_auth_requires_strong_session_secret() -> None:
    from lexigram.admin.config import AdminAuthConfig

    with pytest.raises(ValueError, match="session_secret"):
        AdminAuthConfig(env="production", session_secret="change-me-in-production")


def test_production_auth_rejects_oauth_without_providers() -> None:
    from lexigram.admin.config import AdminAuthConfig

    with pytest.raises(ValueError, match="oauth_providers"):
        AdminAuthConfig(
            env="production",
            session_secret="x" * 64,
            oauth_enabled=True,
            oauth_providers=[],
        )


def test_production_warns_when_strict_resource_resolution_disabled() -> None:
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminProvider

    config = AdminConfig(
        auth={"env": "production", "session_secret": "x" * 64},
        strict_resource_resolution=False,
    )
    with structlog.testing.capture_logs() as captured:
        AdminProvider(config=config)

    assert any(
        "strict_resource_resolution=False in production"
        in str(log.get("message", ""))
        for log in captured
        if log.get("event") == "admin.strict_resource_resolution_disabled_in_production"
    )
