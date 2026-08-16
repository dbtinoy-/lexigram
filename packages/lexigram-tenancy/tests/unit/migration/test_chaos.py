"""Chaos tests for TenantTierMigrationSaga — inject failure at every stage boundary."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.tenancy.migration import CopyResult
from lexigram.result import Err, Ok
from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy
from lexigram.tenancy.migration.saga import TenantTierMigrationSaga
from lexigram.tenancy.migration.write_pause import WritePauseRegistry
from lexigram.workflow.checkpoint.store_memory import (
    InMemoryContentCheckpointStore,
)


class _FailingStrategy:
    """A strategy whose provision_isolation always fails."""

    name = "schema"

    async def apply_isolation(self, tenant_id: str, context: dict) -> None:
        pass

    async def remove_isolation(self, tenant_id: str) -> None:
        pass

    async def provision_isolation(self, tenant_id: str):
        return Err(Exception("provision failed"))

    async def deprovision_isolation(self, tenant_id: str):
        return Ok(None)


class _OkStrategy:
    """A strategy whose every operation succeeds."""

    name = "schema"

    async def apply_isolation(self, tenant_id: str, context: dict) -> None:
        pass

    async def remove_isolation(self, tenant_id: str) -> None:
        pass

    async def provision_isolation(self, tenant_id: str):
        return Ok(None)

    async def deprovision_isolation(self, tenant_id: str):
        return Ok(None)


class _DeprovisionSourceFails:
    """Source strategy whose deprovision_isolation always fails."""

    name = "row_level"

    async def apply_isolation(self, tenant_id: str, context: dict) -> None:
        pass

    async def remove_isolation(self, tenant_id: str) -> None:
        pass

    async def provision_isolation(self, tenant_id: str):
        return Ok(None)

    async def deprovision_isolation(self, tenant_id: str):
        return Err(Exception("source deprovision failed"))


class _ChaosFixture:
    """Build a TenantTierMigrationSaga that fails at a specific stage."""

    def __init__(self) -> None:
        self.checkpoint_store = InMemoryContentCheckpointStore()
        self.isolation_registry = IsolationStrategyRegistry()
        self.isolation_registry.register(RowLevelIsolationStrategy())
        self.isolation_registry.register(_FailingStrategy())
        self.write_pause = WritePauseRegistry()

    def build_saga(
        self,
        copy_strategy_side_effect: Exception | None = None,
        config_get_side_effect: Exception | None = None,
    ) -> TenantTierMigrationSaga:
        tenant_provider = AsyncMock()
        from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus

        tenant_provider.get_tenant.return_value = TenantInfo(
            tenant_id="tenant-abc",
            slug="acme",
            name="ACME Corp",
            status=TenantStatus.ACTIVE,
        )

        config_service = AsyncMock()
        if config_get_side_effect is not None:
            config_service.get.side_effect = config_get_side_effect
        else:
            config_service.get.return_value = None
        config_service.set = AsyncMock()

        copy_strategy = AsyncMock()
        copy_strategy.validate = AsyncMock()
        if copy_strategy_side_effect is not None:
            copy_strategy.copy.side_effect = copy_strategy_side_effect
        else:
            copy_strategy.copy.return_value = CopyResult(
                records_copied=5, records_failed=0
            )
        copy_strategy.rollback = AsyncMock()

        return TenantTierMigrationSaga(
            tenant_id="tenant-abc",
            target_tier="m5",
            checkpoint_store=self.checkpoint_store,
            isolation_registry=self.isolation_registry,
            tenant_provider=tenant_provider,
            config_service=config_service,
            write_pause_registry=self.write_pause,
            copy_strategy=copy_strategy,
            event_bus=None,
        )


class TestChaosStages:
    """Verify correct compensation after failure at every stage boundary."""

    @pytest.mark.asyncio
    async def test_validate_failure_returns_err(self) -> None:
        """Stage 1 fails before any side effects — no compensation needed."""
        fx = _ChaosFixture()
        saga = fx.build_saga(config_get_side_effect=RuntimeError("config down"))
        result = await saga.execute()
        assert result.is_err()
        assert await fx.write_pause.is_paused("tenant-abc") is False

    @pytest.mark.asyncio
    async def test_provision_target_failure_compensates(self) -> None:
        """Stage 2 fails — deprovision_target compensation runs."""
        fx = _ChaosFixture()
        saga = fx.build_saga()
        result = await saga.execute()
        assert result.is_err()
        assert await fx.write_pause.is_paused("tenant-abc") is False

    @pytest.mark.asyncio
    async def test_copy_data_failure_compensates(self) -> None:
        """Stage 3 fails — copy rollback + unpause + strategy restore."""
        fx = _ChaosFixture()
        fx.isolation_registry.register(_OkStrategy())

        saga = fx.build_saga(
            copy_strategy_side_effect=RuntimeError("copy timeout")
        )
        result = await saga.execute()
        assert result.is_err()
        assert await fx.write_pause.is_paused("tenant-abc") is False
        assert fx.isolation_registry.get_tenant_strategy("tenant-abc") == "row_level"

    @pytest.mark.asyncio
    async def test_deprovision_source_failure_returns_err(self) -> None:
        """Stage 8 fails (no compensation — strategy already switched)."""
        fx = _ChaosFixture()
        fx.isolation_registry.register(_OkStrategy())
        fx.isolation_registry.register(_DeprovisionSourceFails())

        saga = fx.build_saga()
        result = await saga.execute()
        assert result.is_err()
        assert await fx.write_pause.is_paused("tenant-abc") is False

    @pytest.mark.asyncio
    async def test_resume_skips_completed_stages_after_crash(self) -> None:
        """Content-addressed checkpoint: resume after crash skips completed stages."""
        fx = _ChaosFixture()

        provision_call_count = 0

        class _TrackedStrategy:
            name = "schema"

            async def apply_isolation(self, tenant_id: str, context: dict) -> None:
                pass

            async def remove_isolation(self, tenant_id: str) -> None:
                pass

            async def provision_isolation(self, tenant_id: str):
                nonlocal provision_call_count
                provision_call_count += 1
                return Ok(None)

            async def deprovision_isolation(self, tenant_id: str):
                return Ok(None)

        fx.isolation_registry.register(_TrackedStrategy())

        saga1 = fx.build_saga(
            copy_strategy_side_effect=RuntimeError("crash at copy")
        )
        await saga1.execute()

        saga2 = fx.build_saga()
        result2 = await saga2.execute()
        assert result2.is_ok()
        assert provision_call_count == 1

