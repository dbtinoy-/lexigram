"""Tests for RowLevelIsolationStrategy."""

from __future__ import annotations

import pytest

from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy


@pytest.mark.asyncio
async def test_provision_returns_ok() -> None:
    """provision_isolation() is a no-op that returns Ok."""
    strategy = RowLevelIsolationStrategy()
    result = await strategy.provision_isolation("tenant-abc")
    assert result.is_ok()
    assert result.unwrap() is None


@pytest.mark.asyncio
async def test_deprovision_returns_ok() -> None:
    """deprovision_isolation() is a no-op that returns Ok."""
    strategy = RowLevelIsolationStrategy()
    result = await strategy.deprovision_isolation("tenant-abc")
    assert result.is_ok()


@pytest.mark.asyncio
async def test_apply_isolation_does_not_modify_context() -> None:
    """apply_isolation() leaves the context unchanged."""
    strategy = RowLevelIsolationStrategy()
    ctx: dict = {}
    await strategy.apply_isolation("tenant-abc", ctx)
    assert ctx == {}


@pytest.mark.asyncio
async def test_apply_isolation_does_not_modify_existing_context() -> None:
    """apply_isolation() doesn't modify existing context keys."""
    strategy = RowLevelIsolationStrategy()
    ctx = {"existing_key": "value", "another": 123}
    await strategy.apply_isolation("tenant-abc", ctx)
    assert ctx == {"existing_key": "value", "another": 123}


@pytest.mark.asyncio
async def test_apply_isolation_handles_nested_context() -> None:
    """apply_isolation() doesn't modify nested structures."""
    strategy = RowLevelIsolationStrategy()
    ctx = {"nested": {"deep": {"value": 1}}, "list": [1, 2, 3]}
    await strategy.apply_isolation("tenant-abc", ctx)
    assert ctx["nested"]["deep"]["value"] == 1
    assert ctx["list"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_remove_isolation_does_nothing() -> None:
    """remove_isolation() is a no-op."""
    strategy = RowLevelIsolationStrategy()
    await strategy.remove_isolation("tenant-abc")


@pytest.mark.asyncio
async def test_remove_isolation_does_not_clear_context() -> None:
    """remove_isolation() doesn't clear any context."""
    strategy = RowLevelIsolationStrategy()
    ctx = {"some_data": "value"}
    await strategy.remove_isolation("tenant-abc")
    assert "some_data" in ctx


@pytest.mark.asyncio
async def test_provision_with_various_tenant_ids() -> None:
    """Works with various tenant ID formats."""
    strategy = RowLevelIsolationStrategy()
    tenant_ids = ["acme", "acme-corp", "tenant_123", "TEnAnT-UPPER", "a"]
    for tenant_id in tenant_ids:
        result = await strategy.provision_isolation(tenant_id)
        assert result.is_ok()


@pytest.mark.asyncio
async def test_deprovision_with_various_tenant_ids() -> None:
    """Works with various tenant IDs."""
    strategy = RowLevelIsolationStrategy()
    tenant_ids = ["acme", "acme-corp", "tenant_123", "TEnAnT-UPPER", "a"]
    for tenant_id in tenant_ids:
        result = await strategy.deprovision_isolation(tenant_id)
        assert result.is_ok()


def test_name_is_row_level() -> None:
    """Strategy name is 'row_level'."""
    assert RowLevelIsolationStrategy.name == "row_level"
