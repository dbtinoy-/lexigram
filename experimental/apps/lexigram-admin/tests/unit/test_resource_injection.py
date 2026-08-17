"""Tests for AdminRegistry and AdminProvider DI pattern.

Verifies that AdminRegistry is standalone (no AdminProvider dependency).
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.protocols import (
    AdminCsrfServiceProtocol,
    AdminSessionServiceProtocol,
)
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.admin.core.registry import AdminRegistry
from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.admin.middleware.authorization import RequestAuthorizerProtocol
from lexigram.contracts.auth import AuthorizerProtocol
from lexigram.contracts.exceptions import UnresolvableDependencyError


def test_registry_standalone_no_required_args() -> None:
    """AdminRegistry can be instantiated without any arguments."""
    registry = AdminRegistry()
    assert registry._resources == {}
    assert registry._controllers == []


def test_registry_accepts_config() -> None:
    """AdminRegistry accepts an optional AdminConfig."""
    from lexigram.admin.config import AdminConfig

    config = AdminConfig(prefix="/admin")
    registry = AdminRegistry(config=config)
    assert registry._config is config


def test_registry_does_not_use_inject_decorator() -> None:
    """AdminRegistry must NOT use @inject decorator on __init__."""
    sig = inspect.signature(AdminRegistry.__init__)
    params = list(sig.parameters.keys())
    assert "provider" not in params, (
        "AdminRegistry.__init__ must NOT accept 'provider' parameter after refactor"
    )
    assert not hasattr(AdminRegistry.__init__, "__wrapped__"), (
        "AdminRegistry.__init__ should not be decorated with @inject"
    )


@pytest.mark.asyncio
async def test_registry_instantiation_without_di_container() -> None:
    """AdminRegistry should be instantiable directly without the container."""
    registry = AdminRegistry()
    assert registry is not None
    assert registry._resources == {}


def test_provider_accepts_resources_via_constructor() -> None:
    """AdminProvider accepts resources as constructor arguments."""

    class _FakeResource:
        pass

    provider = AdminProvider(resources=[_FakeResource])
    assert provider._resources == [_FakeResource]


@pytest.mark.asyncio
async def test_provider_register_runs_without_errors() -> None:
    """AdminProvider.register() should not raise with a mock container."""
    provider = AdminProvider()

    container = MagicMock()
    container.resolve = AsyncMock(side_effect=UnresolvableDependencyError("missing"))
    container.singleton = MagicMock()
    container.transient = MagicMock()

    await provider.register(container)
    container.singleton.assert_called()


@pytest.mark.asyncio
async def test_provider_boot_runs_without_errors() -> None:
    """AdminProvider.boot() should not raise with a mock container."""
    from lexigram.admin.config import AdminConfig

    provider = AdminProvider(
        config=AdminConfig.from_dict(
            {"auth": {"security": {"setup_token": "test-setup-token"}}}
        )
    )

    container = MagicMock()

    async def _resolve(spec, /, *args, **kwargs):
        if spec in (
            AdminCsrfServiceProtocol,
            AdminUserStoreProtocol,
            AdminSessionServiceProtocol,
            RequestAuthorizerProtocol,
            AuthorizerProtocol,
        ):
            return AsyncMock()
        raise UnresolvableDependencyError("missing")

    container.resolve = AsyncMock(side_effect=_resolve)
    container.singleton = MagicMock()

    await provider.register(container)
    await provider.boot(container)
