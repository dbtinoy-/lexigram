"""Tests for CSRF fail-closed boot behavior (P0: F2)."""

from __future__ import annotations

import pytest


class _NoCsrfResolver:
    """Resolver that can resolve everything except the CSRF service."""

    async def resolve(
        self,
        token: object,
        *,
        bypass_visibility: bool = False,
    ) -> object:
        token_name = getattr(token, "__name__", token.__class__.__name__)
        if token_name == "AdminCsrfServiceProtocol":
            raise RuntimeError("csrf service not registered")
        from types import SimpleNamespace

        return SimpleNamespace()


@pytest.mark.asyncio
async def test_boot_raises_when_csrf_service_unresolvable() -> None:
    """Admin boot must fail when the CSRF service cannot be resolved."""
    from lexigram.admin.di.bundle_provider import AdminProvider

    provider = AdminProvider()
    with pytest.raises(RuntimeError, match="(?i)csrf"):
        await provider.boot(_NoCsrfResolver())
