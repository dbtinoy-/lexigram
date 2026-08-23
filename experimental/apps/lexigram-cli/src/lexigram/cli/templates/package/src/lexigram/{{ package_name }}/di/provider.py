"""{{ class_name }} provider for the Lexigram DI container."""
from __future__ import annotations

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.provider import Provider, ProviderPriority


class {{ class_name }}Provider(Provider):
    """Registers {{ package_name }} services into the application container.

    Add this provider to your application via ``application.add_provider()``.
    """

    name = "{{ package_name }}"
    priority = ProviderPriority.NORMAL

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register {{ package_name }} services.

        Args:
            container: The DI container registrar.
        """

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot {{ package_name }} services after all providers are registered.

        Args:
            container: The read-only container resolver.
        """

    async def shutdown(self) -> None:
        """Tear down {{ package_name }} services on application shutdown."""


__all__ = ["{{ class_name }}Provider"]
