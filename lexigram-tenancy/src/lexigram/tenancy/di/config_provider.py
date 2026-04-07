"""Config override sub-provider — config store and caching service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.tenancy.protocols import TenantConfigProviderProtocol
from lexigram.di.provider import Provider
from lexigram.tenancy.config import ConfigOverridesConfig
from lexigram.tenancy.config_overrides.cache import CachedTenantConfigProvider
from lexigram.tenancy.config_overrides.defaults import DEFAULT_CONFIG
from lexigram.tenancy.config_overrides.service import TenantConfigService
from lexigram.tenancy.stores.memory import InMemoryTenantProvider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )


class TenantConfigProvider(Provider):
    """Registers the config provider, caching wrapper, and config service."""

    name = "tenant_config"

    def __init__(self, config: ConfigOverridesConfig) -> None:
        """Initialise the provider.

        Args:
            config: Config overrides configuration.
        """
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the config provider binding.

        Reuses the ``InMemoryTenantProvider`` registered by
        :class:`~lexigram.tenancy.di.lifecycle_provider.TenantLifecycleProvider`
        since it implements both protocols.

        Args:
            container: The DI container registrar.
        """
        # Will be resolved in boot() once InMemoryTenantProvider is available.

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire the cached config provider and config service.

        Args:
            container: The DI container for boot phase.
        """
        # Attempt to reuse the shared store (InMemoryTenantProvider implements
        # TenantConfigProviderProtocol too).
        try:
            base_config_provider = await container.resolve(InMemoryTenantProvider)
        except Exception:
            # Fallback: create a fresh in-memory instance for config only
            base_config_provider = InMemoryTenantProvider()

        cached_provider = CachedTenantConfigProvider(
            inner=base_config_provider,
            ttl=self._config.cache_ttl,
        )
        container.singleton(TenantConfigProviderProtocol, cached_provider)
        container.singleton(CachedTenantConfigProvider, cached_provider)

        # Event bus is optional
        try:
            from lexigram.contracts.events import EventBusProtocol

            event_bus = await container.resolve(EventBusProtocol)
        except Exception:
            from lexigram.tenancy.di.lifecycle_provider import _NoOpEventBus

            event_bus = _NoOpEventBus()

        config_service = TenantConfigService(
            config_provider=cached_provider,
            defaults=dict(DEFAULT_CONFIG),
            event_bus=event_bus,
        )
        container.singleton(TenantConfigService, config_service)

    async def shutdown(self) -> None:
        """No-op shutdown."""


__all__ = ["TenantConfigProvider"]
