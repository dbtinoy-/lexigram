"""Admin core sub-provider — config, routing, Starlette sub-app, static files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class AdminCoreSubProvider:
    """Manages core admin infrastructure: config, routing, templates, ASGI mounting.

    This is a focused helper class, NOT a Provider subclass.
    It is orchestrated by AdminProvider.
    """

    def __init__(self, config: AdminConfig, **kwargs: object) -> None:
        self._config = config
        self._kwargs = kwargs
        self._mounted = False

    @property
    def config(self) -> AdminConfig:
        """Return current admin config."""
        return self._config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register core admin services: config, routing, rendering, feature flags."""
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.core.rendering import AdminRenderer
        from lexigram.admin.engine.renderer import AdminRenderer as EngineAdminRenderer
        from lexigram.admin.services.feature_flags import AdminFeatureFlagService
        from lexigram.admin.settings.panel.registry import ConfigRegistry
        from lexigram.admin.state.dependency_tracker import DependencyTracker

        container.singleton(AdminConfig, self._config)

        # AdminRouter is built in AdminProvider.mount_to_app() with the
        # resolved resource and controller instances — do NOT register as class here
        # (its constructor has resources/controllers that are not container-resolvable).

        # Register the engine AdminRenderer (all-optional deps) — this is what
        # AdminController subclasses use for rendering admin pages.
        from lexigram.admin.engine.renderer import AdminRendererConfig

        renderer_config = AdminRendererConfig(
            primary_color=self._config.ui.primary_color or "#6b7280",
        )
        container.singleton(EngineAdminRenderer, EngineAdminRenderer(renderer_config))

        # Register the core AdminRenderer as well (used internally)
        container.singleton(AdminRenderer, AdminRenderer)

        container.singleton(DependencyTracker, DependencyTracker)
        container.singleton(ConfigRegistry, ConfigRegistry.with_defaults)

        # Feature flags: register the admin service only.
        # The concrete FlagManagerProtocol implementation is expected to be
        # registered by the application's feature-flags provider.
        container.singleton(AdminFeatureFlagService, AdminFeatureFlagService)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Initialize Starlette sub-app and mount routes."""
        self._mounted = True

    async def shutdown(self) -> None:
        """Clean up core resources."""
        self._mounted = False

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return core health status."""
        return HealthCheckResult(
            component="admin_core",
            status=HealthStatus.HEALTHY if self._mounted else HealthStatus.UNKNOWN,
            message="Admin core operational" if self._mounted else "Not yet mounted",
        )


__all__ = ["AdminCoreSubProvider"]
