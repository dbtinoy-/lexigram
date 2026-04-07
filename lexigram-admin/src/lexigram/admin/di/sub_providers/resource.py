"""Admin resource sub-provider — resource registry, CRUD routing, handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class AdminResourceSubProvider:
    """Manages admin resource infrastructure: registry, CRUD routing, handlers.

    Handles resource registration, CRUD action dispatch, and resource discovery.
    Accepts a list of Resource classes to register on initialization.
    """

    def __init__(
        self,
        config: AdminConfig,
        resources: list[type] | None = None,
        **kwargs: object,
    ) -> None:
        self._config = config
        self._resources = resources or []
        self._kwargs = kwargs
        self._initialized = False

    @property
    def config(self) -> AdminConfig:
        """Return current admin config."""
        return self._config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register resource infrastructure: registry, manager, action handler registry."""
        from lexigram.admin.core.registry import AdminRegistry
        from lexigram.admin.resources.handler import ActionHandlerRegistry
        from lexigram.admin.services.resource_manager_factory import (
            ResourceManagerFactory,
        )

        # Register the class (container will instantiate via DI)
        container.singleton(ActionHandlerRegistry, ActionHandlerRegistry)
        container.singleton(ResourceManagerFactory, ResourceManagerFactory())
        # Register the class (container will instantiate via DI with provider argument)
        container.singleton(AdminRegistry, AdminRegistry)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot resource infrastructure: initialize registries and discovery."""
        self._initialized = True

    async def shutdown(self) -> None:
        """Shut down resource infrastructure."""
        self._initialized = False

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return resource infrastructure health status."""
        return HealthCheckResult(
            component="admin_resource",
            status=HealthStatus.HEALTHY if self._initialized else HealthStatus.UNKNOWN,
            message=f"Admin resources operational ({len(self._resources)} registered)"
            if self._initialized
            else "Not yet initialized",
        )


__all__ = ["AdminResourceSubProvider"]
