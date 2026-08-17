"""Tests for boot-time fail-closed resolution of admin middleware dependencies.

Covers spec §29 D1/D2 (AdminAuthMiddleware + AdminAuthorizationMiddleware
dependencies resolved in ``AdminProvider.boot()``) and D3 (guard middleware
degrade keeps its behavior, but logs at error when auth was explicitly
required).
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import ANY, MagicMock

import pytest

from lexigram.admin.config import AdminConfig


class _SelectiveResolver:
    """Resolves every token to a MagicMock unless it is in ``_fail_on``."""

    def __init__(self, fail_on: set[Any]) -> None:
        self._fail_on = fail_on

    async def resolve(self, key: Any, **kwargs: Any) -> Any:
        if key in self._fail_on:
            raise RuntimeError("dependency unavailable")
        return MagicMock()

    def singleton(self, key: Any, value: Any = None, **kwargs: Any) -> None:
        pass


def _boot_config(**overrides: Any) -> AdminConfig:
    data: dict[str, Any] = {"auth": {"security": {"setup_token": "test-token"}}}
    data.update(overrides)
    return AdminConfig.from_dict(data)


def _provider(config: AdminConfig):
    from lexigram.admin.di.bundle_provider import AdminProvider

    return AdminProvider(config=config)


@pytest.mark.asyncio
async def test_boot_raises_when_user_store_unresolvable() -> None:
    """Boot fails loudly when the auth middleware's user store is missing."""
    from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
    from lexigram.admin.di.bundle_provider import AdminProvider

    provider = AdminProvider(config=_boot_config())
    resolver = _SelectiveResolver(fail_on={AdminUserStoreProtocol})
    with pytest.raises(RuntimeError, match="(?i)session validation"):
        await provider.boot(resolver)


@pytest.mark.asyncio
async def test_boot_raises_when_session_service_unresolvable() -> None:
    """Boot fails loudly when the auth middleware's session service is missing."""
    from lexigram.admin.auth.protocols import AdminSessionServiceProtocol
    from lexigram.admin.di.bundle_provider import AdminProvider

    provider = AdminProvider(config=_boot_config())
    resolver = _SelectiveResolver(fail_on={AdminSessionServiceProtocol})
    with pytest.raises(RuntimeError, match="(?i)session validation"):
        await provider.boot(resolver)


@pytest.mark.asyncio
async def test_boot_raises_when_authorizer_unresolvable() -> None:
    """Boot fails loudly when the authorization middleware's authorizer is missing."""
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.admin.middleware.authorization import (
        RequestAuthorizerProtocol,
    )

    provider = AdminProvider(config=_boot_config())
    resolver = _SelectiveResolver(fail_on={RequestAuthorizerProtocol})
    with pytest.raises(RuntimeError, match="(?i)RBAC enforcement"):
        await provider.boot(resolver)


@pytest.mark.asyncio
async def test_boot_and_mount_succeed_when_dependencies_resolve() -> None:
    """Clean boot + mount with all middleware dependencies resolvable."""
    provider = _provider(_boot_config())
    resolver = _SelectiveResolver(fail_on=set())
    await provider.boot(resolver)
    app = MagicMock()
    await provider.mount_to_app(app, resolver)


@pytest.mark.asyncio
async def test_auth_guard_skip_logs_error_when_auth_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard degrade is non-fatal but logs at error when require_auth=True."""
    from lexigram.admin.di import bundle_provider

    monkeypatch.setitem(
        sys.modules,
        "lexigram.admin.middleware.auth_guard",
        None,  # type: ignore[arg-type]
    )
    log_mock = MagicMock()
    monkeypatch.setattr(bundle_provider, "_log", log_mock)

    provider = _provider(_boot_config(require_auth=True))
    resolver = _SelectiveResolver(fail_on=set())
    await provider.boot(resolver)
    app = MagicMock()
    await provider.mount_to_app(app, resolver)

    log_mock.error.assert_any_call(
        "admin.auth_guard_middleware_skipped", reason=ANY
    )
    for call in log_mock.warning.call_args_list:
        assert call.args[0] != "admin.auth_guard_middleware_skipped"


@pytest.mark.asyncio
async def test_auth_guard_unset_keeps_debug_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With require_auth unset the guard is skipped with a debug note only."""
    from lexigram.admin.di import bundle_provider

    log_mock = MagicMock()
    monkeypatch.setattr(bundle_provider, "_log", log_mock)

    provider = _provider(_boot_config(require_auth=False))
    resolver = _SelectiveResolver(fail_on=set())
    await provider.boot(resolver)
    app = MagicMock()
    await provider.mount_to_app(app, resolver)

    log_mock.debug.assert_any_call(
        "admin.auth_guard_middleware_skipped_require_auth_unset"
    )
    for call in log_mock.error.call_args_list:
        assert call.args[0] != "admin.auth_guard_middleware_skipped"