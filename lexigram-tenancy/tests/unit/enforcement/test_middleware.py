"""Tests for TenantContextMiddleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.primitives.context import TENANT_ID, DEFAULT_KEYS, Context, ContextVarRegistry
from lexigram.tenancy.enforcement.middleware import TenantContextMiddleware

def make_context() -> Context:
    registry = ContextVarRegistry()
    for key in DEFAULT_KEYS:
        registry.register_key(key)
    return Context(registry)


def _make_scope(
    *,
    path: str = "/api/test",
    headers: list[tuple[bytes, bytes]] | None = None,
    host: str = "acme.app.com",
) -> dict:
    h = headers or [(b"host", host.encode())]
    return {"type": "http", "path": path, "headers": h}


def _make_active_tenant() -> TenantInfo:
    return TenantInfo(
        tenant_id="tenant-abc",
        slug="acme",
        name="ACME",
        status=TenantStatus.ACTIVE,
    )


@pytest.mark.asyncio
async def test_sets_tenant_id_in_context_when_resolved() -> None:
    """Middleware sets TENANT_ID in context when resolver returns a tenant_id."""
    resolver = MagicMock()
    resolver.resolve_with_source = AsyncMock(return_value=("jwt_claim", "tenant-abc"))
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=_make_active_tenant())
    validator.authorize = AsyncMock(return_value=True)
    ctx = make_context()

    called_with: list = []

    async def app(scope: object, receive: object, send: object) -> None:
        called_with.append(scope)
        assert ctx.get(TENANT_ID) == "tenant-abc"

    middleware = TenantContextMiddleware(app=app, resolver=resolver, validator=validator, ctx=ctx)
    scope = _make_scope()
    scope.setdefault("state", {})
    await middleware(scope, AsyncMock(), AsyncMock())

    assert scope["state"]["tenant"].tenant_id == "tenant-abc"


@pytest.mark.asyncio
async def test_does_not_set_context_when_resolver_returns_none() -> None:
    """Middleware does nothing when resolver returns None."""
    resolver = MagicMock()
    resolver.resolve_with_source = AsyncMock(return_value=None)
    validator = MagicMock()
    ctx = make_context()

    async def app(scope: object, receive: object, send: object) -> None:
        pass

    middleware = TenantContextMiddleware(app=app, resolver=resolver, validator=validator, ctx=ctx)
    scope = _make_scope()
    await middleware(scope, AsyncMock(), AsyncMock())

    assert ctx.get(TENANT_ID) is None


@pytest.mark.asyncio
async def test_passes_through_non_http_scopes() -> None:
    """Non-HTTP scope types are passed through without resolution."""
    resolver = MagicMock()
    resolver.resolve_with_source = AsyncMock()
    validator = MagicMock()
    ctx = make_context()
    app_called = []

    async def app(scope: object, receive: object, send: object) -> None:
        app_called.append(True)

    middleware = TenantContextMiddleware(app=app, resolver=resolver, validator=validator, ctx=ctx)
    await middleware({"type": "lifespan"}, AsyncMock(), AsyncMock())

    assert len(app_called) == 1
    resolver.resolve_with_source.assert_not_called()


@pytest.mark.asyncio
async def test_header_resolution_never_binds_without_membership() -> None:
    """Default-deny: client-controlled header tenant is not bound for anonymous callers."""
    resolver = MagicMock()
    resolver.resolve_with_source = AsyncMock(return_value=("header", "tenant-abc"))
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=_make_active_tenant())
    validator.authorize = AsyncMock(return_value=False)
    ctx = make_context()

    async def app(scope: object, receive: object, send: object) -> None:
        pass

    middleware = TenantContextMiddleware(app=app, resolver=resolver, validator=validator, ctx=ctx)
    scope = _make_scope()
    scope.setdefault("state", {})
    await middleware(scope, AsyncMock(), AsyncMock())

    assert ctx.get(TENANT_ID) is None
    assert "tenant" not in scope["state"]


@pytest.mark.asyncio
async def test_membership_grant_binds_header_tenant() -> None:
    """Membership grant binds a header-resolved tenant for the authenticated caller."""
    resolver = MagicMock()
    resolver.resolve_with_source = AsyncMock(return_value=("header", "tenant-abc"))
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=_make_active_tenant())
    validator.authorize = AsyncMock(return_value=True)
    ctx = make_context()

    async def app(scope: object, receive: object, send: object) -> None:
        assert ctx.get(TENANT_ID) == "tenant-abc"

    middleware = TenantContextMiddleware(app=app, resolver=resolver, validator=validator, ctx=ctx)
    scope = _make_scope()
    scope.setdefault("state", {})["user_id"] = "user-1"
    await middleware(scope, AsyncMock(), AsyncMock())

    assert scope["state"]["tenant"].tenant_id == "tenant-abc"


@pytest.mark.asyncio
async def test_context_token_reset_after_request() -> None:
    """TENANT_ID is reset to its prior value after the request completes."""
    resolver = MagicMock()
    resolver.resolve_with_source = AsyncMock(return_value=("jwt_claim", "tenant-abc"))
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=_make_active_tenant())
    validator.authorize = AsyncMock(return_value=True)
    ctx = make_context()

    async def app(scope: object, receive: object, send: object) -> None:
        assert ctx.get(TENANT_ID) == "tenant-abc"

    middleware = TenantContextMiddleware(app=app, resolver=resolver, validator=validator, ctx=ctx)
    scope = _make_scope()
    await middleware(scope, AsyncMock(), AsyncMock())

    assert ctx.get(TENANT_ID) is None


@pytest.mark.asyncio
async def test_no_token_leak_when_not_bound() -> None:
    """App is still called and no token is leaked when no tenant is bound."""
    resolver = MagicMock()
    resolver.resolve_with_source = AsyncMock(return_value=("header", "tenant-abc"))
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=None)  # inactive/unknown tenant
    validator.authorize = AsyncMock(return_value=False)
    ctx = make_context()
    app_called = []

    async def app(scope: object, receive: object, send: object) -> None:
        app_called.append(True)

    middleware = TenantContextMiddleware(app=app, resolver=resolver, validator=validator, ctx=ctx)
    await middleware(_make_scope(), AsyncMock(), AsyncMock())

    assert app_called == [True]
    assert ctx.get(TENANT_ID) is None
