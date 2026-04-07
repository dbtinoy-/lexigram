"""Lifecycle sub-provider — tenant store, lifecycle service, and provisioner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
from lexigram.di.provider import Provider
from lexigram.tenancy.config import LifecycleConfig
from lexigram.tenancy.enforcement.validator import TenantValidator
from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
from lexigram.tenancy.lifecycle.provisioner import TenantProvisioner
from lexigram.tenancy.lifecycle.service import TenantLifecycleService
from lexigram.tenancy.stores.memory import InMemoryTenantProvider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )


class TenantLifecycleProvider(Provider):
    """Registers the tenant store, isolation registry, provisioner, and lifecycle service."""

    name = "tenant_lifecycle"

    def __init__(self, config: LifecycleConfig) -> None:
        """Initialise the provider.

        Args:
            config: Lifecycle configuration.
        """
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register lifecycle bindings.

        Args:
            container: The DI container registrar.
        """
        # Default to in-memory; applications override by binding SQLTenantProvider
        # before this provider runs.
        store = InMemoryTenantProvider()
        container.singleton(TenantProviderProtocol, store)
        container.singleton(InMemoryTenantProvider, store)

        isolation_registry = IsolationStrategyRegistry.with_defaults()
        container.singleton(IsolationStrategyRegistry, isolation_registry)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire provisioner and lifecycle service.

        Args:
            container: The DI container for boot phase.
        """
        isolation_registry = await container.resolve(IsolationStrategyRegistry)
        strategy = isolation_registry.get(self._config.isolation_strategy)
        provisioner = TenantProvisioner(
            strategy=strategy,
            auto_provision=self._config.auto_provision_isolation,
        )
        container.singleton(TenantProvisioner, provisioner)

        provider = await container.resolve(TenantProviderProtocol)
        validator = await container.resolve(TenantValidator)

        # Event bus is optional — provide a no-op if not registered
        try:
            from lexigram.contracts.events import EventBusProtocol

            event_bus = await container.resolve(EventBusProtocol)
        except Exception:
            event_bus = _NoOpEventBus()

        lifecycle_service = TenantLifecycleService(
            provider=provider,
            provisioner=provisioner,
            event_bus=event_bus,
            validator=validator,
        )
        container.singleton(TenantLifecycleService, lifecycle_service)

    async def shutdown(self) -> None:
        """No-op shutdown."""


class _NoOpEventBus:
    """Fallback no-op event bus when lexigram-events is not registered."""

    async def publish(self, event: object) -> None:
        """Silently discard the event.

        Args:
            event: Any domain event (ignored).
        """


__all__ = ["TenantLifecycleProvider"]
