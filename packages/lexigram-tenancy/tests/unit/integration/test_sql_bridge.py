"""Tests for TenantSQLContextBridge."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.primitives.context import TENANT_ID, DEFAULT_KEYS, Context, ContextVarRegistry

def make_context() -> Context:
    registry = ContextVarRegistry()
    for key in DEFAULT_KEYS:
        registry.register_key(key)
    return Context(registry)


@pytest.mark.asyncio
async def test_bridge_passes_through_non_http_scope() -> None:
    """Bridge passes through non-HTTP scope types without any SQL interaction."""
    ctx = make_context()
    app_called = []

    async def app(scope: object, receive: object, send: object) -> None:
        app_called.append(True)

    try:
        from lexigram.tenancy.integration.sql_bridge import TenantSQLContextBridge

        bridge = TenantSQLContextBridge(app=app, ctx=ctx)  # type: ignore[arg-type]
        await bridge({"type": "lifespan"}, AsyncMock(), AsyncMock())
        assert len(app_called) == 1
    except ImportError:
        pytest.skip("lexigram-sql not installed")


@pytest.mark.asyncio
async def test_bridge_passes_through_http_without_tenant() -> None:
    """Bridge passes through HTTP requests when no TENANT_ID is in context."""
    ctx = make_context()
    # No TENANT_ID set
    app_called = []

    async def app(scope: object, receive: object, send: object) -> None:
        app_called.append(True)

    try:
        from lexigram.tenancy.integration.sql_bridge import TenantSQLContextBridge

        bridge = TenantSQLContextBridge(app=app, ctx=ctx)  # type: ignore[arg-type]
        scope: dict = {"type": "http", "path": "/", "headers": [], "state": {}}
        await bridge(scope, AsyncMock(), AsyncMock())
        assert len(app_called) == 1
    except ImportError:
        pytest.skip("lexigram-sql not installed")


@pytest.mark.asyncio
async def test_bridge_passes_through_http_with_tenant_no_db_ctx() -> None:
    """Bridge passes through when TENANT_ID is set but no db_ctx in scope state."""
    ctx = make_context()
    ctx.set(TENANT_ID, "tenant-abc")
    app_called = []

    async def app(scope: object, receive: object, send: object) -> None:
        app_called.append(True)

    try:
        from lexigram.tenancy.integration.sql_bridge import TenantSQLContextBridge

        bridge = TenantSQLContextBridge(app=app, ctx=ctx)  # type: ignore[arg-type]
        # No db_ctx in state — bridge should still pass through
        scope: dict = {"type": "http", "path": "/", "headers": [], "state": {}}
        await bridge(scope, AsyncMock(), AsyncMock())
        assert len(app_called) == 1
    except ImportError:
        pytest.skip("lexigram-sql not installed")


def test_bridge_importable_with_sql() -> None:
    """TenantSQLContextBridge is importable when lexigram-sql is installed."""
    try:
        from lexigram.tenancy.integration.sql_bridge import TenantSQLContextBridge

        assert TenantSQLContextBridge is not None
    except ImportError:
        pytest.skip("lexigram-sql not installed")


@pytest.mark.asyncio
async def test_bridge_propagates_tenant_to_real_db_context() -> None:
    """Bridge sets tenant_id on a real DbContext during the request and resets it after."""
    try:
        from lexigram.sql.context import create_db_context
        from lexigram.tenancy.integration.sql_bridge import TenantSQLContextBridge
    except ImportError:
        pytest.skip("lexigram-sql not installed")

    ctx = make_context()
    db_ctx = create_db_context()
    observed: list[str | None] = []

    async def app(scope: object, receive: object, send: object) -> None:
        observed.append(db_ctx.tenant_id)

    ctx.set(TENANT_ID, "tenant-abc")
    assert db_ctx.tenant_id is None

    bridge = TenantSQLContextBridge(app=app, ctx=ctx)  # type: ignore[arg-type]
    scope: dict = {
        "type": "http",
        "path": "/",
        "headers": [],
        "state": {"db_ctx": db_ctx},
    }
    await bridge(scope, AsyncMock(), AsyncMock())

    assert observed == ["tenant-abc"]
    assert db_ctx.tenant_id is None
