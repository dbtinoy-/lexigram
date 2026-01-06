"""Migration sub-provider — registers the migration service and its dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.di.provider import Provider
from lexigram.tenancy.migration import TenantMigrationService
from lexigram.tenancy.migration.copy import RowToSchemaCopy
from lexigram.tenancy.migration.write_pause import WritePauseRegistry

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )


class TenantMigrationProvider(Provider):
    """Registers the tenant migration service and write-pause registry.

    Expects the following dependencies to already be bound in the container:

    - ``TenantProviderProtocol``
    - ``IsolationStrategyRegistry``
    - ``TenantConfigService``
    - ``ContentCheckpointStoreProtocol``
    - ``DomainEventPublisherProtocol`` (optional)
    - ``DatabaseProviderProtocol`` (optional)

    Usage::

        from lexigram.tenancy.di.migration_provider import TenantMigrationProvider

        provider = TenantMigrationProvider()
    """

    name = "tenant_migration"

    def __init__(self) -> None:
        from lexigram.contracts.core.provider import ProviderPriority

        self.priority = ProviderPriority.APPLICATION

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register write-pause registry and migration service.

        Args:
            container: The DI container registrar.
        """
        write_pause = WritePauseRegistry()
        container.singleton(WritePauseRegistry, write_pause)

        copy_strategy = RowToSchemaCopy()
        container.singleton(RowToSchemaCopy, copy_strategy)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire the migration service.

        Args:
            container: The DI container for boot phase.
        """
        from lexigram.contracts.tenancy.protocols import (
            TenantProviderProtocol,
        )
        from lexigram.contracts.workflow.content_checkpoint import (
            ContentCheckpointStoreProtocol,
        )
        from lexigram.tenancy.config_overrides.service import (
            TenantConfigService,
        )
        from lexigram.tenancy.isolation.registry import (
            IsolationStrategyRegistry,
        )
        from lexigram.tenancy.migration.copy import RowToSchemaCopy

        tenant_provider = await container.resolve(TenantProviderProtocol)
        isolation_registry = await container.resolve(IsolationStrategyRegistry)
        config_service = await container.resolve(TenantConfigService)
        write_pause = await container.resolve(WritePauseRegistry)
        copy_strategy = await container.resolve(RowToSchemaCopy)

        checkpoint_store = await container.resolve(ContentCheckpointStoreProtocol)

        try:
            from lexigram.contracts.events import EventBusProtocol

            event_bus = await container.resolve(EventBusProtocol)
        except Exception:
            event_bus = None

        service = TenantMigrationService(
            tenant_provider=tenant_provider,
            isolation_registry=isolation_registry,
            config_service=config_service,
            write_pause_registry=write_pause,
            checkpoint_store=checkpoint_store,
            copy_strategy=copy_strategy,
            event_bus=event_bus,
        )
        container.singleton(TenantMigrationService, service)

    async def shutdown(self) -> None:
        """No-op shutdown."""


__all__ = ["TenantMigrationProvider"]
