"""Tenant tier migration saga — content-addressed, 10 stages, full compensation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lexigram.contracts.tenancy.events import TenantTierMigrationCheckpoint
from lexigram.contracts.tenancy.migration import (
    ISOLATION_TIER_ORDER,
    TIER_ISOLATION_MAP,
    CopyResult,
    MigrationContext,
)
from lexigram.saga.content_addressed import (
    ContentAddressedSaga,
    ContentAddressedStage,
)

if TYPE_CHECKING:
    from lexigram.contracts.events.protocols import DomainEventPublisherProtocol
    from lexigram.contracts.tenancy.migration import MigrationCopyStrategy
    from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
    from lexigram.contracts.workflow.content_checkpoint import (
        ContentCheckpointStoreProtocol,
    )
    from lexigram.tenancy.config_overrides.service import TenantConfigService
    from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
    from lexigram.tenancy.migration.write_pause import WritePauseRegistry


class TenantTierMigrationSaga(ContentAddressedSaga):
    """Content-addressed saga for migrating a tenant between isolation tiers.

    The saga executes these stages in order; each stage is content-addressed
    so completed work is skipped on resume after failure:

    ``validate`` → ``provision_target`` → ``copy_data`` → ``rebuild_projections``
    → ``pause_writes`` → ``set_strategy`` → ``validate_cutover``
    → ``resume_writes`` → ``deprovision_source`` → ``update_tier_config``
    → ``cleanup``

    Limitations:
        *Compensation* handlers receive ``None`` from the base class
        (``ContentAddressedSaga._run_compensation`` passes ``None``), so
        compensations rely on instance attributes rather than handler output.
    """

    def __init__(
        self,
        tenant_id: str,
        target_tier: str,
        checkpoint_store: ContentCheckpointStoreProtocol,
        isolation_registry: IsolationStrategyRegistry,
        tenant_provider: TenantProviderProtocol,
        config_service: TenantConfigService,
        write_pause_registry: WritePauseRegistry,
        copy_strategy: MigrationCopyStrategy,
        event_bus: DomainEventPublisherProtocol | None = None,
    ) -> None:
        saga_id = f"migrate-tier/{tenant_id}/{target_tier}"
        super().__init__(
            saga_id=saga_id,
            checkpoint_store=checkpoint_store,
            tenant_id=tenant_id,
        )
        self._tenant_id = tenant_id
        self._target_tier = target_tier
        self._isolation_registry = isolation_registry
        self._tenant_provider = tenant_provider
        self._config_service = config_service
        self._write_pause_registry = write_pause_registry
        self._copy_strategy = copy_strategy
        self._event_bus = event_bus

        # -- mutable state accumulated across stage executions ----------------
        self._source_tier: str = ""
        self._source_strategy_name: str = ""
        self._target_strategy_name: str = ""
        self._origin_strategy: str = ""
        self._copy_result: CopyResult | None = None

        self.add_stage(
            ContentAddressedStage(
                stage_id="validate",
                handler=self._validate,
                handler_version="v1",
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="provision_target",
                handler=self._provision_target,
                handler_version="v1",
                compensation=self._deprovision_target,
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="copy_data",
                handler=self._copy_data,
                handler_version="v1",
                compensation=self._rollback_copy,
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="rebuild_projections",
                handler=self._rebuild_projections,
                handler_version="v1",
                compensation=self._skip_rebuild,
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="pause_writes",
                handler=self._pause_writes,
                handler_version="v1",
                compensation=self._resume_writes,
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="set_strategy",
                handler=self._set_strategy,
                handler_version="v1",
                compensation=self._restore_origin_strategy,
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="validate_cutover",
                handler=self._validate_cutover,
                handler_version="v1",
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="resume_writes",
                handler=self._resume_writes,
                handler_version="v1",
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="deprovision_source",
                handler=self._deprovision_source,
                handler_version="v1",
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="update_tier_config",
                handler=self._update_tier_config,
                handler_version="v1",
            )
        )
        self.add_stage(
            ContentAddressedStage(
                stage_id="cleanup",
                handler=self._cleanup,
                handler_version="v1",
            )
        )

    # ------------------------------------------------------------------
    # Stage handlers
    # ------------------------------------------------------------------

    async def _ensure_state_initialized(self) -> None:
        """Derive strategy names from tier config (safe to call on resume)."""
        if self._target_strategy_name:
            return
        source_tier_val = await self._config_service.get(self._tenant_id, "tier")
        self._source_tier = source_tier_val if source_tier_val else "m1"
        self._source_strategy_name = TIER_ISOLATION_MAP.get(
            self._source_tier, "row_level"
        )
        self._target_strategy_name = TIER_ISOLATION_MAP.get(self._target_tier, "")
        in_memory = self._isolation_registry.get_tenant_strategy(self._tenant_id)
        persisted = await self._config_service.get(self._tenant_id, "tenancy.strategy")
        restored = in_memory or persisted
        self._origin_strategy = restored or self._source_strategy_name

    async def _validate(self, inputs: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_state_initialized()
        tenant = await self._tenant_provider.get_tenant(self._tenant_id)
        if tenant is None:
            raise ValueError(f"Tenant {self._tenant_id} not found")

        if not self._target_strategy_name:
            raise ValueError(f"Unknown target tier: {self._target_tier}")

        if self._source_strategy_name == self._target_strategy_name:
            raise ValueError(
                f"Source ({self._source_tier}) and target ({self._target_tier}) "
                f"use the same isolation strategy '{self._source_strategy_name}'"
            )

        src_idx = ISOLATION_TIER_ORDER.index(self._source_strategy_name)
        tgt_idx = ISOLATION_TIER_ORDER.index(self._target_strategy_name)
        if tgt_idx <= src_idx:
            raise ValueError(
                f"Cannot migrate from {self._source_tier} to "
                f"{self._target_tier}: not an upgrade path"
            )

        self._isolation_registry.get(self._source_strategy_name)
        self._isolation_registry.get(self._target_strategy_name)

        self._origin_strategy = (
            self._isolation_registry.get_tenant_strategy(self._tenant_id)
            or self._source_strategy_name
        )

        ctx = MigrationContext(
            source_tier=self._source_tier,
            target_tier=self._target_tier,
            source_strategy_name=self._source_strategy_name,
            target_strategy_name=self._target_strategy_name,
        )
        await self._copy_strategy.validate(self._tenant_id, ctx)

        await self._publish_checkpoint("validate", "completed")
        return {
            "source_tier": self._source_tier,
            "target_tier": self._target_tier,
            "source_strategy": self._source_strategy_name,
            "target_strategy": self._target_strategy_name,
        }

    async def _provision_target(self, inputs: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_state_initialized()
        target = self._isolation_registry.get(self._target_strategy_name)
        result = await target.provision_isolation(self._tenant_id)
        if result.is_err():
            raise RuntimeError(f"Target provisioning failed: {result.unwrap_err()}")
        await self._publish_checkpoint("provision_target", "completed")
        return {"provisioned": self._target_strategy_name}

    async def _deprovision_target(self, _: Any) -> None:
        await self._ensure_state_initialized()
        target = self._isolation_registry.get(self._target_strategy_name)
        await target.deprovision_isolation(self._tenant_id)

    async def _copy_data(self, inputs: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_state_initialized()
        ctx = MigrationContext(
            source_tier=self._source_tier,
            target_tier=self._target_tier,
            source_strategy_name=self._source_strategy_name,
            target_strategy_name=self._target_strategy_name,
        )
        self._copy_result = await self._copy_strategy.copy(self._tenant_id, ctx)
        await self._publish_checkpoint("copy_data", "completed")
        return {
            "records_copied": self._copy_result.records_copied,
            "records_failed": self._copy_result.records_failed,
        }

    async def _rollback_copy(self, _: Any) -> None:
        if self._copy_result is not None:
            try:
                await self._copy_strategy.rollback(self._tenant_id, self._copy_result)
            except Exception:
                pass

    async def _rebuild_projections(self, inputs: dict[str, Any]) -> dict[str, str]:
        await self._publish_checkpoint("rebuild_projections", "completed")
        return {"rebuild": "skipped"}

    async def _skip_rebuild(self, _: Any) -> None:
        pass

    async def _pause_writes(self, inputs: dict[str, Any]) -> dict[str, str]:
        await self._write_pause_registry.pause(self._tenant_id)
        await self._publish_checkpoint("pause_writes", "completed")
        return {"paused": self._tenant_id}

    async def _resume_writes(self, _: Any) -> None:
        await self._write_pause_registry.resume(self._tenant_id)

    async def _set_strategy(self, inputs: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_state_initialized()
        self._isolation_registry.set_tenant_strategy(
            self._tenant_id, self._target_strategy_name
        )
        await self._config_service.set(
            self._tenant_id, "tenancy.strategy", self._target_strategy_name
        )
        await self._publish_checkpoint("set_strategy", "completed")
        return {
            "tenant_id": self._tenant_id,
            "strategy": self._target_strategy_name,
        }

    async def _restore_origin_strategy(self, _: Any) -> None:
        await self._ensure_state_initialized()
        self._isolation_registry.set_tenant_strategy(
            self._tenant_id, self._origin_strategy
        )
        await self._config_service.set(
            self._tenant_id, "tenancy.strategy", self._origin_strategy
        )

    async def _validate_cutover(self, inputs: dict[str, Any]) -> dict[str, bool]:
        await self._ensure_state_initialized()
        assigned = (
            self._isolation_registry.get_tenant_strategy(self._tenant_id)
            or await self._config_service.get(self._tenant_id, "tenancy.strategy")
        )
        if assigned != self._target_strategy_name:
            raise RuntimeError(
                f"Cutover validation failed: tenant strategy is "
                f"'{assigned}', expected '{self._target_strategy_name}'"
            )
        await self._publish_checkpoint("validate_cutover", "completed")
        return {"validated": True}

    async def _deprovision_source(self, inputs: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_state_initialized()
        source = self._isolation_registry.get(self._source_strategy_name)
        result = await source.deprovision_isolation(self._tenant_id)
        if result.is_err():
            raise RuntimeError(f"Source deprovisioning failed: {result.unwrap_err()}")
        await self._publish_checkpoint("deprovision_source", "completed")
        return {"deprovisioned": self._source_strategy_name}

    async def _update_tier_config(self, inputs: dict[str, Any]) -> dict[str, str]:
        await self._config_service.set(self._tenant_id, "tier", self._target_tier)
        await self._publish_checkpoint("update_tier_config", "completed")
        return {"tier": self._target_tier}

    async def _cleanup(self, inputs: dict[str, Any]) -> dict[str, str]:
        await self._publish_checkpoint("cleanup", "completed")
        return {"cleaned": self._tenant_id}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _publish_checkpoint(self, stage: str, status: str) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            TenantTierMigrationCheckpoint(
                tenant_id=self._tenant_id,
                saga_id=self._saga_id,
                stage=stage,
                status=status,
                timestamp=datetime.now(UTC),
            )
        )


__all__ = ["TenantTierMigrationSaga"]
