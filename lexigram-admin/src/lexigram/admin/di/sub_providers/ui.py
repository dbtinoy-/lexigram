"""Admin UI sub-provider — rendering, component registry, forms, navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class AdminUISubProvider:
    """Manages admin UI infrastructure: rendering, components, forms, navigation.

    Registers UI services: renderer, component registry, form renderer, navigation.
    """

    def __init__(self, config: AdminConfig, **kwargs: object) -> None:
        self._config = config
        self._kwargs = kwargs
        self._initialized = False

    @property
    def config(self) -> AdminConfig:
        """Return current admin config."""
        return self._config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register UI services: component registry, form renderer, navigation, layout."""
        from lexigram.admin.layout.layout_manager import LayoutManager
        from lexigram.admin.navigation.assembler import NavigationAssembler
        from lexigram.admin.services.component_registry import ComponentRegistry
        from lexigram.admin.ui.observability import MetricsCollectorProtocol
        from lexigram.admin.ui.organisms.form_registry import FormFieldRegistry

        container.singleton(ComponentRegistry, ComponentRegistry())
        container.singleton(FormFieldRegistry, FormFieldRegistry())

        # Register navigation assembler (container will instantiate via DI)
        container.singleton(NavigationAssembler, NavigationAssembler)

        # Pre-construct LayoutManager to avoid the container trying to resolve
        # LayoutType (an enum, not a registered service) as a dependency.
        container.singleton(LayoutManager, LayoutManager())

        container.singleton(MetricsCollectorProtocol, MetricsCollectorProtocol)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot UI services: initialize component registry and navigation."""
        self._initialized = True

    async def shutdown(self) -> None:
        """Shut down UI services."""
        self._initialized = False

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return UI infrastructure health status."""
        return HealthCheckResult(
            component="admin_ui",
            status=HealthStatus.HEALTHY if self._initialized else HealthStatus.UNKNOWN,
            message="Admin UI operational"
            if self._initialized
            else "Not yet initialized",
        )


__all__ = ["AdminUISubProvider"]
