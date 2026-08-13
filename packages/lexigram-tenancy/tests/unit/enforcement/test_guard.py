"""Tests for TenantGuard."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.primitives.context import TENANT_ID, DEFAULT_KEYS, Context, ContextVarRegistry
from lexigram.tenancy.enforcement.guard import TenantGuard

def make_context() -> Context:
    registry = ContextVarRegistry()
    for key in DEFAULT_KEYS:
        registry.register_key(key)
    return Context(registry)


def _make_exec_ctx(tenant: TenantInfo | None) -> MagicMock:
    exec_ctx = MagicMock()
    exec_ctx.request.scope = {"state": {"tenant": tenant}} if tenant else {"state": {}}
    return exec_ctx


@pytest.mark.asyncio
async def test_allows_active_tenant() -> None:
    """Returns True when TENANT_ID is in context and tenant is active."""
    ctx = make_context()
    ctx.set(TENANT_ID, "tenant-abc")
    tenant = TenantInfo(
        tenant_id="tenant-abc", slug="acme", name="ACME", status=TenantStatus.ACTIVE
    )
    guard = TenantGuard(ctx)
    result = await guard.can_activate(_make_exec_ctx(tenant))
    assert result is True


@pytest.mark.asyncio
async def test_denies_when_no_tenant_in_context() -> None:
    """Returns False when TENANT_ID is not in context."""
    ctx = make_context()
    guard = TenantGuard(ctx)
    result = await guard.can_activate(_make_exec_ctx(None))
    assert result is False


@pytest.mark.asyncio
async def test_denies_when_tenant_is_inactive() -> None:
    """Returns False when the scope tenant is inactive."""
    ctx = make_context()
    ctx.set(TENANT_ID, "tenant-abc")
    tenant = TenantInfo(
        tenant_id="tenant-abc", slug="acme", name="ACME", status=TenantStatus.INACTIVE
    )
    guard = TenantGuard(ctx)
    result = await guard.can_activate(_make_exec_ctx(tenant))
    assert result is False


@pytest.mark.asyncio
async def test_denies_when_scope_has_no_tenant() -> None:
    """Returns False when TENANT_ID is set but no tenant in scope state."""
    ctx = make_context()
    ctx.set(TENANT_ID, "tenant-abc")
    guard = TenantGuard(ctx)
    # Execution context with no tenant in state
    exec_ctx = MagicMock()
    exec_ctx.request.scope = {"state": {}}
    result = await guard.can_activate(exec_ctx)
    assert result is False
