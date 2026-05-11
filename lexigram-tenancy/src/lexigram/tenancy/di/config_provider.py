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
    from lexigram.di.resolution.resolver import ServiceResolver


class TenantConfigProvider(Provider):
    """Registers the config provider, caching wrapper, and config service."""

    name = "tenant_config"

    def __init__(self, config: ConfigOverridesConfig) -> None:
        """Initialise the provider.

        Args:
            config: Config overrides configuration.
        """
        super().__init__()
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the config provider binding.

        Reuses the ``InMemoryTenantProvider`` registered by
        :class:`~lexigram.tenancy.di.lifecycle_provider.TenantLifecycleProvider`
        since it implements both protocols.

        Args:
            container: The DI container registrar.
        """
        # Reuses the ``InMemoryTenantProvider`` registered by
        # :class:`~lexigram.tenancy.di.lifecycle_provider.TenantLifecycleProvider`
        # since it implements both protocols.

        async def _cached_provider_factory(
            resolver: ServiceResolver,
        ) -> CachedTenantConfigProvider:
            try:
                base_config_provider = await resolver.resolve(InMemoryTenantProvider)
            except Exception:
                # Fallback: create a fresh in-memory instance for config only
                base_config_provider = InMemoryTenantProvider()

            provider: CachedTenantConfigProvider = CachedTenantConfigProvider(
                inner=base_config_provider,
                ttl=self._config.cache_ttl,
            )
            return provider

        container.singleton(
            TenantConfigProviderProtocol, factory=_cached_provider_factory
        )

        async def _cached_impl_factory(
            resolver: ServiceResolver,
        ) -> CachedTenantConfigProvider:
            impl: CachedTenantConfigProvider = await resolver.resolve(
                TenantConfigProviderProtocol
            )
            return impl

        container.singleton(
            CachedTenantConfigProvider,
            factory=_cached_impl_factory,
        )

        async def _config_service_factory(
            resolver: ServiceResolver,
        ) -> TenantConfigService:
            cached_provider = await resolver.resolve(TenantConfigProviderProtocol)

            # Event bus is optional
            try:
                from lexigram.contracts.events import EventBusProtocol

                event_bus = await resolver.resolve(EventBusProtocol)
            except Exception:
                from lexigram.tenancy.di.lifecycle_provider import _NoOpEventBus

                event_bus = _NoOpEventBus()

            return TenantConfigService(
                config_provider=cached_provider,
                defaults=dict(DEFAULT_CONFIG),
                event_bus=event_bus,
            )

        container.singleton(TenantConfigService, factory=_config_service_factory)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire the cached config provider and config service.

        Args:
            container: The DI container for boot phase.
        """

    async def shutdown(self) -> None:
        """No-op shutdown."""


__all__ = ["TenantConfigProvider"]
