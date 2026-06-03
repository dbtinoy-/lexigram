"""Tests for the mandatory setup-token boot guard (F1: P0)."""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from lexigram.admin.config import AdminConfig


class _EverythingResolver:
    """Resolver that resolves every token to a SimpleNamespace."""

    async def resolve(
        self,
        token: object,
        *,
        bypass_visibility: bool = False,
    ) -> object:
        return SimpleNamespace()


def _provider(config: AdminConfig):
    from lexigram.admin.di.bundle_provider import AdminProvider

    return AdminProvider(config=config)


def _boot_config() -> AdminConfig:
    return AdminConfig.from_dict(
        {"auth": {"security": {"setup_token": "test-setup-token"}}}
    )


@pytest.mark.asyncio
async def test_boot_raises_without_token_and_without_optin() -> None:
    """Boot must fail loudly when no setup token is configured."""
    from lexigram.admin.di.bundle_provider import AdminProvider

    provider = AdminProvider()
    with pytest.raises(RuntimeError, match="(?i)setup token"):
        await provider.boot(_EverythingResolver())


@pytest.mark.asyncio
async def test_boot_succeeds_with_setup_token() -> None:
    """Boot must succeed when a setup token is configured."""
    provider = _provider(_boot_config())
    await provider.boot(_EverythingResolver())


@pytest.mark.asyncio
async def test_boot_succeeds_with_optin_unsafe_flag() -> None:
    """Boot must succeed with the explicit opt-out flag for local envs."""
    provider = _provider(
        AdminConfig.from_dict({"auth": {"security": {"setup_token_optin_unsafe": True}}})
    )
    await provider.boot(_EverythingResolver())


@pytest.mark.asyncio
async def test_boot_succeeds_with_legacy_env_var_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy ADMIN_SETUP_TOKEN env var must satisfy the boot guard."""
    monkeypatch.setenv("ADMIN_SETUP_TOKEN", "env-secret")
    provider = _provider(AdminConfig())
    await provider.boot(_EverythingResolver())
