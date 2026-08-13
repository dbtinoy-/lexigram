"""Unit tests for TenantMigrationService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.tenancy.errors import MigrationError
from lexigram.contracts.tenancy.migration import CopyResult
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.tenancy.config_overrides.service import TenantConfigService
from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy
from lexigram.tenancy.migration.service import TenantMigrationService
from lexigram.tenancy.migration.write_pause import WritePauseRegistry
from lexigram.workflow.checkpoint.store_memory import (
    InMemoryContentCheckpointStore,
)


class _SchemaStub:
    name = "schema"
    async def apply_isolation(self, tenant_id: str, context: dict) -> None: ...
    async def remove_isolation(self, tenant_id: str) -> None: ...
    async def provision_isolation(self, tenant_id: str):
        from lexigram.result import Ok
        return Ok(None)
    async def deprovision_isolation(self, tenant_id: str):
        from lexigram.result import Ok
        return Ok(None)


@pytest.fixture
def tenant_provider() -> MagicMock:
    p = MagicMock()
    p.get_tenant = AsyncMock(
        return_value=TenantInfo(
            tenant_id="tenant-abc",
            slug="acme",
            name="ACME Corp",
            status=TenantStatus.ACTIVE,
        )
    )
    return p


@pytest.fixture
def isolation_registry() -> IsolationStrategyRegistry:
    reg = IsolationStrategyRegistry()
    reg.register(RowLevelIsolationStrategy())
    reg.register(_SchemaStub())
    return reg


@pytest.fixture
def config_service() -> MagicMock:
    s = MagicMock()
    s.get = AsyncMock(return_value=None)
    s.set = AsyncMock()
    return s


@pytest.fixture
def write_pause() -> WritePauseRegistry:
    return WritePauseRegistry()


@pytest.fixture
def checkpoint_store() -> InMemoryContentCheckpointStore:
    return InMemoryContentCheckpointStore()


@pytest.fixture
def copy_strategy() -> MagicMock:
    s = MagicMock()
    s.validate = AsyncMock()
    s.copy = AsyncMock(
        return_value=CopyResult(records_copied=5, records_failed=0)
    )
    s.rollback = AsyncMock()
    return s


@pytest.fixture
def service(
    tenant_provider: MagicMock,
    isolation_registry: IsolationStrategyRegistry,
    config_service: MagicMock,
    write_pause: WritePauseRegistry,
    checkpoint_store: InMemoryContentCheckpointStore,
    copy_strategy: MagicMock,
) -> TenantMigrationService:
    return TenantMigrationService(
        tenant_provider=tenant_provider,
        isolation_registry=isolation_registry,
        config_service=config_service,
        write_pause_registry=write_pause,
        checkpoint_store=checkpoint_store,
        copy_strategy=copy_strategy,
        event_bus=None,
    )


class TestTenantMigrationService:
    """Suite for TenantMigrationService."""

    async def test_migrate_tier_success(
        self, service: TenantMigrationService
    ) -> None:
        result = await service.migrate_tier("tenant-abc", "m5")
        assert result.is_ok()
        migration_result = result.unwrap()
        assert migration_result.tenant_id == "tenant-abc"
        assert migration_result.target_tier == "m5"
        assert migration_result.success is True
        assert migration_result.error is None
        assert migration_result.duration_ms >= 0

    async def test_migrate_tier_unknown_target(
        self, service: TenantMigrationService
    ) -> None:
        result = await service.migrate_tier("tenant-abc", "m99")
        assert result.is_err()

    async def test_migrate_tier_unknown_tenant(
        self,
        service: TenantMigrationService,
        tenant_provider: MagicMock,
    ) -> None:
        tenant_provider.get_tenant = AsyncMock(return_value=None)
        result = await service.migrate_tier("nonexistent", "m5")
        assert result.is_err()

    async def test_migrate_tier_with_event_bus(
        self,
        tenant_provider: MagicMock,
        isolation_registry: IsolationStrategyRegistry,
        config_service: MagicMock,
        write_pause: WritePauseRegistry,
        checkpoint_store: InMemoryContentCheckpointStore,
        copy_strategy: MagicMock,
    ) -> None:
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        svc = TenantMigrationService(
            tenant_provider=tenant_provider,
            isolation_registry=isolation_registry,
            config_service=config_service,
            write_pause_registry=write_pause,
            checkpoint_store=checkpoint_store,
            copy_strategy=copy_strategy,
            event_bus=event_bus,
        )
        result = await svc.migrate_tier("tenant-abc", "m5")
        assert result.is_ok()
        assert event_bus.publish.await_count >= 2

    async def test_migrate_tier_failure_publishes_failed_event(
        self,
        tenant_provider: MagicMock,
        isolation_registry: IsolationStrategyRegistry,
        config_service: MagicMock,
        write_pause: WritePauseRegistry,
        checkpoint_store: InMemoryContentCheckpointStore,
        copy_strategy: MagicMock,
    ) -> None:
        copy_strategy.copy = AsyncMock(
            side_effect=RuntimeError("copy failed")
        )
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        svc = TenantMigrationService(
            tenant_provider=tenant_provider,
            isolation_registry=isolation_registry,
            config_service=config_service,
            write_pause_registry=write_pause,
            checkpoint_store=checkpoint_store,
            copy_strategy=copy_strategy,
            event_bus=event_bus,
        )
        result = await svc.migrate_tier("tenant-abc", "m5")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), MigrationError)
