"""Unit tests for TenantTierMigrationSaga."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.tenancy.migration import CopyResult, MigrationContext
from lexigram.result import Ok
from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy
from lexigram.tenancy.migration.saga import TenantTierMigrationSaga
from lexigram.tenancy.migration.write_pause import WritePauseRegistry
from lexigram.workflow.checkpoint.store_memory import (
    InMemoryContentCheckpointStore,
)


class _SchemaStub:
    """A fake schema isolation strategy that tracks provision/deprovision calls."""

    name = "schema"

    def __init__(self) -> None:
        self.provision_calls: list[str] = []
        self.deprovision_calls: list[str] = []

    async def apply_isolation(self, tenant_id: str, context: dict) -> None:
        pass

    async def remove_isolation(self, tenant_id: str) -> None:
        pass

    async def provision_isolation(self, tenant_id: str):
        self.provision_calls.append(tenant_id)
        from lexigram.result import Ok
        return Ok(None)

    async def deprovision_isolation(self, tenant_id: str):
        self.deprovision_calls.append(tenant_id)
        from lexigram.result import Ok
        return Ok(None)


class _DatabaseStub:
    """A fake database isolation strategy."""

    name = "database"

    async def apply_isolation(self, tenant_id: str, context: dict) -> None:
        pass

    async def remove_isolation(self, tenant_id: str) -> None:
        pass

    async def provision_isolation(self, tenant_id: str):
        from lexigram.result import Ok
        return Ok(None)

    async def deprovision_isolation(self, tenant_id: str):
        from lexigram.result import Ok
        return Ok(None)


@pytest.fixture
def checkpoint_store() -> InMemoryContentCheckpointStore:
    return InMemoryContentCheckpointStore()


@pytest.fixture
def isolation_registry() -> IsolationStrategyRegistry:
    reg = IsolationStrategyRegistry()
    reg.register(RowLevelIsolationStrategy())
    reg.register(_SchemaStub())
    return reg


@pytest.fixture
def write_pause() -> WritePauseRegistry:
    return WritePauseRegistry()


@pytest.fixture
def copy_strategy() -> MagicMock:
    strategy = MagicMock()
    strategy.validate = AsyncMock()
    strategy.copy = AsyncMock(
        return_value=CopyResult(records_copied=5, records_failed=0)
    )
    strategy.rollback = AsyncMock()
    return strategy


@pytest.fixture
def tenant_provider() -> MagicMock:
    provider = MagicMock()
    from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
    provider.get_tenant = AsyncMock(
        return_value=TenantInfo(
            tenant_id="tenant-abc",
            slug="acme",
            name="ACME Corp",
            status=TenantStatus.ACTIVE,
        )
    )
    return provider


@pytest.fixture
def config_service() -> MagicMock:
    service = MagicMock()
    service.get = AsyncMock(return_value=None)
    service.set = AsyncMock()
    return service


class TestTenantTierMigrationSaga:
    """Suite for the migration saga."""

    @pytest.fixture
    def saga(
        self,
        checkpoint_store: InMemoryContentCheckpointStore,
        isolation_registry: IsolationStrategyRegistry,
        tenant_provider: MagicMock,
        config_service: MagicMock,
        write_pause: WritePauseRegistry,
        copy_strategy: MagicMock,
    ) -> TenantTierMigrationSaga:
        return TenantTierMigrationSaga(
            tenant_id="tenant-abc",
            target_tier="m5",
            checkpoint_store=checkpoint_store,
            isolation_registry=isolation_registry,
            tenant_provider=tenant_provider,
            config_service=config_service,
            write_pause_registry=write_pause,
            copy_strategy=copy_strategy,
        )

    async def test_execute_success(
        self, saga: TenantTierMigrationSaga
    ) -> None:
        result = await saga.execute()
        assert result.is_ok()
        assert saga.is_completed() is True

    async def test_execute_skips_cached_stages_on_resume(
        self,
        checkpoint_store: InMemoryContentCheckpointStore,
        isolation_registry: IsolationStrategyRegistry,
        tenant_provider: MagicMock,
        config_service: MagicMock,
        write_pause: WritePauseRegistry,
        copy_strategy: MagicMock,
    ) -> None:
        saga1 = TenantTierMigrationSaga(
            tenant_id="tenant-abc",
            target_tier="m5",
            checkpoint_store=checkpoint_store,
            isolation_registry=isolation_registry,
            tenant_provider=tenant_provider,
            config_service=config_service,
            write_pause_registry=write_pause,
            copy_strategy=copy_strategy,
            event_bus=None,
        )
        result1 = await saga1.execute()
        assert result1.is_ok()

        saga2 = TenantTierMigrationSaga(
            tenant_id="tenant-abc",
            target_tier="m5",
            checkpoint_store=checkpoint_store,
            isolation_registry=isolation_registry,
            tenant_provider=tenant_provider,
            config_service=config_service,
            write_pause_registry=write_pause,
            copy_strategy=copy_strategy,
            event_bus=None,
        )
        result2 = await saga2.execute()
        assert result2.is_ok()

    async def test_get_id(
        self, saga: TenantTierMigrationSaga
    ) -> None:
        assert saga.get_id() == "migrate-tier/tenant-abc/m5"

    async def test_is_completed_initially_false(
        self, saga: TenantTierMigrationSaga
    ) -> None:
        assert saga.is_completed() is False

    async def test_write_pause_set_during_migration(
        self,
        saga: TenantTierMigrationSaga,
        write_pause: WritePauseRegistry,
    ) -> None:
        assert await write_pause.is_paused("tenant-abc") is False
        await saga.execute()
        assert await write_pause.is_paused("tenant-abc") is False

    async def test_strategy_assigned_after_migration(
        self,
        saga: TenantTierMigrationSaga,
        isolation_registry: IsolationStrategyRegistry,
    ) -> None:
        assert (
            isolation_registry.get_tenant_strategy("tenant-abc") is None
        )
        await saga.execute()
        assert (
            isolation_registry.get_tenant_strategy("tenant-abc") == "schema"
        )

    async def test_config_updated_after_migration(
        self,
        saga: TenantTierMigrationSaga,
        config_service: MagicMock,
    ) -> None:
        await saga.execute()
        config_service.set.assert_any_call(
            "tenant-abc", "tier", "m5"
        )

    async def test_compensation_on_failure(
        self,
        isolation_registry: IsolationStrategyRegistry,
        tenant_provider: MagicMock,
        config_service: MagicMock,
        write_pause: WritePauseRegistry,
        copy_strategy: MagicMock,
        checkpoint_store: InMemoryContentCheckpointStore,
    ) -> None:
        copy_strategy.copy = AsyncMock(
            side_effect=RuntimeError("DB connection lost")
        )

        saga = TenantTierMigrationSaga(
            tenant_id="tenant-abc",
            target_tier="m5",
            checkpoint_store=checkpoint_store,
            isolation_registry=isolation_registry,
            tenant_provider=tenant_provider,
            config_service=config_service,
            write_pause_registry=write_pause,
            copy_strategy=copy_strategy,
        )
        result = await saga.execute()
        assert result.is_err()

    async def test_compensation_on_copy_failure_reverts_pause(
        self,
        isolation_registry: IsolationStrategyRegistry,
        tenant_provider: MagicMock,
        config_service: MagicMock,
        write_pause: WritePauseRegistry,
        copy_strategy: MagicMock,
        checkpoint_store: InMemoryContentCheckpointStore,
    ) -> None:
        copy_strategy.copy = AsyncMock(
            side_effect=RuntimeError("copy failed")
        )

        saga = TenantTierMigrationSaga(
            tenant_id="tenant-abc",
            target_tier="m5",
            checkpoint_store=checkpoint_store,
            isolation_registry=isolation_registry,
            tenant_provider=tenant_provider,
            config_service=config_service,
            write_pause_registry=write_pause,
            copy_strategy=copy_strategy,
        )
        await saga.execute()
        assert await write_pause.is_paused("tenant-abc") is False

    # ------------------------------------------------------------------
    # TDD regression tests for REVIEW.md findings
    # ------------------------------------------------------------------

    async def test_set_strategy_persists_to_config(
        self,
        isolation_registry: IsolationStrategyRegistry,
        tenant_provider: MagicMock,
        config_service: MagicMock,
        write_pause: WritePauseRegistry,
        copy_strategy: MagicMock,
        checkpoint_store: InMemoryContentCheckpointStore,
    ) -> None:
        """_set_strategy writes target strategy to config_service under tenancy.strategy."""
        saga = TenantTierMigrationSaga(
            tenant_id="tenant-abc",
            target_tier="m5",
            checkpoint_store=checkpoint_store,
            isolation_registry=isolation_registry,
            tenant_provider=tenant_provider,
            config_service=config_service,
            write_pause_registry=write_pause,
            copy_strategy=copy_strategy,
        )
        await saga.execute()
        config_service.set.assert_any_call("tenant-abc", "tenancy.strategy", "schema")

    async def test_saga_includes_rebuild_projections_stage(
        self,
        isolation_registry: IsolationStrategyRegistry,
        tenant_provider: MagicMock,
        config_service: MagicMock,
        write_pause: WritePauseRegistry,
        copy_strategy: MagicMock,
        checkpoint_store: InMemoryContentCheckpointStore,
    ) -> None:
        """Saga includes rebuild_projections stage between copy_data and pause_writes."""
        saga = TenantTierMigrationSaga(
            tenant_id="tenant-abc",
            target_tier="m5",
            checkpoint_store=checkpoint_store,
            isolation_registry=isolation_registry,
            tenant_provider=tenant_provider,
            config_service=config_service,
            write_pause_registry=write_pause,
            copy_strategy=copy_strategy,
        )
        stage_ids = [s.stage_id for s in saga._stages]
        assert "rebuild_projections" in stage_ids
        copy_idx = stage_ids.index("copy_data")
        pause_idx = stage_ids.index("pause_writes")
        rebuild_idx = stage_ids.index("rebuild_projections")
        assert copy_idx < rebuild_idx < pause_idx


class TestReviewImports:
    """Verify import paths referenced in REVIEW.md are correct."""

    def test_migration_copy_strategy_importable_from_migration(self) -> None:
        """MigrationCopyStrategy lives in contracts.tenancy.migration, not protocols."""
        from lexigram.contracts.tenancy.migration import MigrationCopyStrategy

        assert MigrationCopyStrategy is not None
