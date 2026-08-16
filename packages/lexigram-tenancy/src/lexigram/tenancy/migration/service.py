"""Tenant migration service — public API for tier migration operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import time
from typing import TYPE_CHECKING

from lexigram.contracts.tenancy.errors import MigrationError, TenantError
from lexigram.contracts.tenancy.events import (
    TenantTierMigrationFailed,
    TenantTierMigrationStarted,
    TenantTierMigrationSucceeded,
)
from lexigram.contracts.tenancy.migration import (
    TIER_ISOLATION_MAP,
)
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.tenancy.migration.saga import TenantTierMigrationSaga

if TYPE_CHECKING:
    from lexigram.contracts.events.protocols import DomainEventPublisherProtocol
    from lexigram.contracts.tenancy.migration import (
        MigrationCopyStrategy,
    )
    from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
    from lexigram.contracts.workflow.content_checkpoint import (
        ContentCheckpointStoreProtocol,
    )
    from lexigram.tenancy.config_overrides.service import TenantConfigService
    from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
    from lexigram.tenancy.migration.write_pause import WritePauseRegistry

logger = get_logger(__name__)


@dataclass
class MigrationServiceConfig:
    """Configuration for :class:`TenantMigrationService`."""

    default_copy_strategy_name: str = "row_to_schema"
    pause_writes_enabled: bool = True


@dataclass
class MigrationResult:
    """Outcome of a completed migration."""

    tenant_id: str
    source_tier: str
    target_tier: str
    duration_ms: int
    success: bool
    error: str | None = None


class TenantMigrationService:
    """Public API for tenant tier migrations.

    Builds and executes :class:`TenantTierMigrationSaga` instances,
    publishes lifecycle events, and returns structured results.

    Usage::

        result = await migration_service.migrate_tier(
            tenant_id="tenant-abc",
            target_tier="m5",
        )
        if result.is_ok():
            print(result.unwrap())
    """

    def __init__(
        self,
        tenant_provider: TenantProviderProtocol,
        isolation_registry: IsolationStrategyRegistry,
        config_service: TenantConfigService,
        write_pause_registry: WritePauseRegistry,
        checkpoint_store: ContentCheckpointStoreProtocol,
        copy_strategy: MigrationCopyStrategy,
        event_bus: DomainEventPublisherProtocol | None = None,
        config: MigrationServiceConfig | None = None,
    ) -> None:
        """Initialise the service.

        Args:
            tenant_provider: Tenant storage backend.
            isolation_registry: Registry of isolation strategies.
            config_service: Per-tenant config overrides.
            write_pause_registry: Write-pause coordination.
            checkpoint_store: Content-addressed checkpoint backend.
            copy_strategy: Strategy for copying tenant data.
            event_bus: Optional event bus for lifecycle events.
            config: Optional service configuration.
        """
        self._tenant_provider = tenant_provider
        self._isolation_registry = isolation_registry
        self._config_service = config_service
        self._write_pause_registry = write_pause_registry
        self._checkpoint_store = checkpoint_store
        self._copy_strategy = copy_strategy
        self._event_bus = event_bus
        self._config = config or MigrationServiceConfig()

    async def migrate_tier(
        self,
        tenant_id: str,
        target_tier: str,
        *,
        actor_id: str | None = None,
    ) -> Result[MigrationResult, TenantError]:
        """Migrate a tenant to a new isolation tier.

        This is the main entry point.  It validates the request, builds a
        :class:`TenantTierMigrationSaga`, executes it, and publishes lifecycle
        events.

        Args:
            tenant_id: The tenant to migrate.
            target_tier: Target tier name (e.g. ``"m5"``, ``"m6"``).
            actor_id: Optional identifier of the user / system that triggered
                the migration.

        Returns:
            ``Ok(MigrationResult)`` on success,
            ``Err(MigrationError)`` on failure.
        """
        # -- Validate tenant exists and target tier is known --------------
        tenant = await self._tenant_provider.get_tenant(tenant_id)
        if tenant is None:
            return Err(TenantError(f"Tenant not found: {tenant_id}"))

        target_tier = target_tier.lower()
        if target_tier not in TIER_ISOLATION_MAP:
            return Err(TenantError(f"Unknown tier: {target_tier}"))

        source_tier_val = await self._config_service.get(tenant_id, "tier")
        source_tier: str = source_tier_val if source_tier_val else "m1"

        saga_id = f"migrate-tier/{tenant_id}/{target_tier}"

        await self._publish_event(
            TenantTierMigrationStarted(
                tenant_id=tenant_id,
                source_tier=source_tier,
                target_tier=target_tier,
                saga_id=saga_id,
                timestamp=datetime.now(UTC),
            )
        )

        start = time.monotonic()

        saga = TenantTierMigrationSaga(
            tenant_id=tenant_id,
            target_tier=target_tier,
            checkpoint_store=self._checkpoint_store,
            isolation_registry=self._isolation_registry,
            tenant_provider=self._tenant_provider,
            config_service=self._config_service,
            write_pause_registry=self._write_pause_registry,
            copy_strategy=self._copy_strategy,
            event_bus=self._event_bus,
        )

        result = await saga.execute()
        duration_ms = int((time.monotonic() - start) * 1000)

        if result.is_ok():
            logger.info(
                "tier_migration_succeeded",
                tenant_id=tenant_id,
                source_tier=source_tier,
                target_tier=target_tier,
                duration_ms=duration_ms,
            )
            await self._publish_event(
                TenantTierMigrationSucceeded(
                    tenant_id=tenant_id,
                    source_tier=source_tier,
                    target_tier=target_tier,
                    saga_id=saga_id,
                    duration_ms=duration_ms,
                    timestamp=datetime.now(UTC),
                )
            )
            return Ok(
                MigrationResult(
                    tenant_id=tenant_id,
                    source_tier=source_tier,
                    target_tier=target_tier,
                    duration_ms=duration_ms,
                    success=True,
                )
            )

        err = result.unwrap_err()
        logger.error(
            "tier_migration_failed",
            tenant_id=tenant_id,
            source_tier=source_tier,
            target_tier=target_tier,
            error=str(err),
            duration_ms=duration_ms,
        )
        await self._publish_event(
            TenantTierMigrationFailed(
                tenant_id=tenant_id,
                source_tier=source_tier,
                target_tier=target_tier,
                saga_id=saga_id,
                error=str(err),
                timestamp=datetime.now(UTC),
            )
        )
        return Err(MigrationError(str(err)))

    async def _publish_event(self, event: object) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event)


__all__ = [
    "MigrationResult",
    "MigrationServiceConfig",
    "TenantMigrationService",
]
