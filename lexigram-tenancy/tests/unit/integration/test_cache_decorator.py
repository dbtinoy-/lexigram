"""Tests for TenantCacheKeyDecorator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.primitives.context import TENANT_ID, DEFAULT_KEYS, Context, ContextVarRegistry
from lexigram.tenancy.integration.cache_decorator import TenantCacheKeyDecorator

def make_context() -> Context:
    registry = ContextVarRegistry()
    for key in DEFAULT_KEYS:
        registry.register_key(key)
    return Context(registry)


def _make_decorator(tenant_id: str | None = None) -> tuple[TenantCacheKeyDecorator, MagicMock]:
    inner = MagicMock()
    inner.get = AsyncMock(return_value=None)
    inner.set = AsyncMock()
    inner.delete = AsyncMock()
    inner.exists = AsyncMock(return_value=False)
    ctx = make_context()
    if tenant_id is not None:
        ctx.set(TENANT_ID, tenant_id)
    decorator = TenantCacheKeyDecorator(inner=inner, ctx=ctx)
    return decorator, inner


@pytest.mark.asyncio
async def test_prefixes_key_with_tenant_id() -> None:
    """get() forwards a prefixed key when a tenant is in context."""
    decorator, inner = _make_decorator(tenant_id="acme")
    await decorator.get("my_key")
    inner.get.assert_called_once_with("t:acme:my_key")


@pytest.mark.asyncio
async def test_uses_original_key_without_tenant() -> None:
    """get() uses the original key when no tenant is in context."""
    decorator, inner = _make_decorator(tenant_id=None)
    await decorator.get("my_key")
    inner.get.assert_called_once_with("my_key")


@pytest.mark.asyncio
async def test_set_uses_prefixed_key() -> None:
    """set() stores under the prefixed key."""
    decorator, inner = _make_decorator(tenant_id="beta")
    await decorator.set("k", b"v", ttl=30)
    inner.set.assert_called_once_with("t:beta:k", b"v", 30)


@pytest.mark.asyncio
async def test_delete_uses_prefixed_key() -> None:
    """delete() deletes the prefixed key."""
    decorator, inner = _make_decorator(tenant_id="gamma")
    await decorator.delete("k")
    inner.delete.assert_called_once_with("t:gamma:k")
