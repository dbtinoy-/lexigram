"""Unit tests for IsolationStrategyRegistry per-tenant strategy extensions."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.errors import TenantError
from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy


class _DummyStrategy:
    name = "dummy"
    async def provision_isolation(self, tenant_id: str) -> None: ...
    async def deprovision_isolation(self, tenant_id: str) -> None: ...


class TestSetTenantStrategy:
    """Suite for set_tenant_strategy / get_tenant_strategy."""

    @pytest.fixture
    def registry(self) -> IsolationStrategyRegistry:
        reg = IsolationStrategyRegistry()
        reg.register(RowLevelIsolationStrategy())
        reg.register(_DummyStrategy())
        return reg

    async def test_get_tenant_strategy_returns_default_when_not_set(
        self, registry: IsolationStrategyRegistry
    ) -> None:
        assert registry.get_tenant_strategy("tenant-abc") is None

    async def test_get_tenant_strategy_custom_default(
        self, registry: IsolationStrategyRegistry
    ) -> None:
        assert registry.get_tenant_strategy("tenant-abc", default="row_level") == "row_level"

    async def test_set_then_get(
        self, registry: IsolationStrategyRegistry
    ) -> None:
        registry.set_tenant_strategy("tenant-abc", "dummy")
        assert registry.get_tenant_strategy("tenant-abc") == "dummy"

    async def test_set_overwrites_previous(
        self, registry: IsolationStrategyRegistry
    ) -> None:
        registry.set_tenant_strategy("tenant-abc", "dummy")
        registry.set_tenant_strategy("tenant-abc", "row_level")
        assert registry.get_tenant_strategy("tenant-abc") == "row_level"

    async def test_set_unknown_strategy_raises(
        self, registry: IsolationStrategyRegistry
    ) -> None:
        with pytest.raises(TenantError, match="Unknown isolation strategy"):
            registry.set_tenant_strategy("tenant-abc", "nonexistent")

    async def test_multiple_tenants_independent(
        self, registry: IsolationStrategyRegistry
    ) -> None:
        registry.set_tenant_strategy("tenant-a", "dummy")
        registry.set_tenant_strategy("tenant-b", "row_level")
        assert registry.get_tenant_strategy("tenant-a") == "dummy"
        assert registry.get_tenant_strategy("tenant-b") == "row_level"

    async def test_does_not_affect_global_registry(
        self, registry: IsolationStrategyRegistry
    ) -> None:
        registry.set_tenant_strategy("tenant-abc", "dummy")
        retrieved = registry.get("dummy")
        assert retrieved is not None
        assert retrieved.name == "dummy"
