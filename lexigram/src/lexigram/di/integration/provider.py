"""DI Provider for the di subsystem.

The ONLY file that registers di infrastructure into
the Lexigram DI container.
"""

from __future__ import annotations

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.di.provider import Provider, ProviderPriority


class DiProvider(Provider):
    """Dependency injection container, providers, and resolution engine DI provider."""

    name = "di"
    priority = ProviderPriority.INFRASTRUCTURE

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register di services into *container*.

        Binding ``ContainerResolverProtocol`` to the container instance itself allows
        other providers and modules to declare it as a constructor dependency
        and have it auto-injected — the canonical DI alternative to the
        Service Locator anti-pattern.
        """
        from lexigram.di.container import Container

        # The container IS the ContainerResolverProtocol — register it so that
        # CoreModule's declared export is satisfied.
        if isinstance(container, Container):
            container.singleton(ContainerResolverProtocol, container, validate=False)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Apply DiConfig settings (e.g. TypeHintResolverImpl cache size)."""
        from lexigram.di.config.models import DiConfig
        from lexigram.di.resolution.type_hints import TypeHintResolverImpl

        config: DiConfig = await container.resolve_optional(DiConfig) or DiConfig()
        TypeHintResolverImpl.configure(config.type_hint_cache_size)

    async def shutdown(self) -> None:
        """Shut down di services gracefully."""


__all__ = [
    "DiProvider",
]
