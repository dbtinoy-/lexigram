"""Tests for SchemaIsolationStrategy."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.errors import TenantProvisioningError
from lexigram.tenancy.isolation.schema import SchemaIsolationStrategy


@pytest.mark.asyncio
async def test_apply_isolation_sets_search_path() -> None:
    """apply_isolation() sets 'search_path' in the context dict."""
    from unittest.mock import AsyncMock, MagicMock

    db = MagicMock()
    strategy = SchemaIsolationStrategy(db_provider=db)
    ctx: dict = {}
    await strategy.apply_isolation("tenant_abc", ctx)
    assert ctx["search_path"] == "tenant_tenant_abc"


@pytest.mark.asyncio
async def test_provision_rejects_invalid_tenant_id() -> None:
    """provision_isolation() returns Err for tenant_id with special chars."""
    from unittest.mock import MagicMock

    db = MagicMock()
    strategy = SchemaIsolationStrategy(db_provider=db)
    result = await strategy.provision_isolation("bad-tenant/id")
    assert result.is_err()
    assert isinstance(result.unwrap_err(), TenantProvisioningError)


def test_name_is_schema() -> None:
    """Strategy name is 'schema'."""
    assert SchemaIsolationStrategy.name == "schema"
