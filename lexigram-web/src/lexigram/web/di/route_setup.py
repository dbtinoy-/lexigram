"""Route registration helper for the Lexigram web layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from starlette.applications import Starlette

    from lexigram.contracts.core.di import ContainerResolverProtocol
    from lexigram.web.config import WebConfig, WebProviderConfig
    from lexigram.web.routing.manager import WebRouterManager

logger = get_logger(__name__)

__all__ = ["RouteSetup"]


class RouteSetup:
    """Encapsulates route and mount registration for the Lexigram web layer.

    Extracted from ``WebProvider`` to keep the provider focused on DI lifecycle
    (register/boot/shutdown) rather than application routing configuration.

    Args:
        web_config: Web configuration; drives debug routes, static files, etc.
        provider_config: Provider-level configuration.
        router_manager: The router manager that discovers and mounts controllers.
    """

    def __init__(
        self,
        web_config: WebConfig,
        provider_config: WebProviderConfig,
        router_manager: WebRouterManager,
    ) -> None:
        self._web_config = web_config
        self._provider_config = provider_config
        self._router_manager = router_manager

    async def configure(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
        provider_context: Any = None,
    ) -> None:
        """Register all routes and ASGI mounts on the application.

        Phases:

        1. Debug routes (guarded by ``web.enable_debug_routes_env_gate`` config).
        2. Prometheus ``/metrics`` ASGI app (when ``MonitoringProvider`` is active).
        3. Web contributor mounts (admin panels, sub-apps, etc.).
        4. Static file directory (when ``web_config.static`` is configured).
        5. Main controller discovery via :class:`~lexigram.web.routing.manager.WebRouterManager`.
        6. Register the Starlette app as the ASGI handler on the ``Application`` instance.

        Args:
            app: The Starlette application to configure.
            container: The resolved DI container.
            provider_context: Optional reference to the parent ``WebProvider``
                instance; forwarded to integrations that need provider-level
                state (e.g. ``DebugIntegration`` for Redis client caching).
        """
        await self._register_debug_routes(app, container, provider_context)
        await self._mount_metrics(app, container)
        await self._mount_contributors(app, container, provider_context)
        self._mount_static(app)
        await self._router_manager.register_routes(app, container)
        await self._register_asgi_handler(app, container)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _register_debug_routes(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
        provider_context: Any,
    ) -> None:
        """Register debug routes when enabled and gate allows registration."""
        from lexigram.web.integrations.debug import DebugIntegration

        debug_enabled = self._web_config.debug_routes or getattr(
            self._provider_config,
            "debug_routes",
            False,
        )
        if not debug_enabled:
            return

        if not getattr(self._web_config, "enable_debug_routes_env_gate", False):
            logger.warning(
                "debug_routes_gate_disabled",
                message="debug_routes=True in config but "
                "enable_debug_routes_env_gate=False. Debug routes will not be registered.",
            )
            return

        await DebugIntegration.configure(app, cast("Any", container), provider_context)

    async def _mount_metrics(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
    ) -> None:
        """Mount Prometheus /metrics ASGI app when ``MonitoringProvider`` is active."""
        try:
            metrics_asgi_app: Any = await container.resolve(
                cast("Any", "prometheus_metrics_app"),
                bypass_visibility=True,
            )
            if metrics_asgi_app is not None:
                metrics_path = getattr(self._web_config, "metrics_path", "/metrics")
                app.mount(metrics_path, metrics_asgi_app)
                logger.info("web.metrics_endpoint_mounted", path=metrics_path)
        except (UnresolvableDependencyError, RuntimeError, AttributeError, TypeError):
            pass

    async def _mount_contributors(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
        provider_context: Any,
    ) -> None:
        """Mount web contributor sub-apps generically.

        Iterates all registered web contributors and calls their mount_to_app
        hook. Failures are isolated and logged; they do not block other
        contributors or route setup.

        Args:
            app: The Starlette application.
            container: The DI container.
            provider_context: The WebProvider instance (for registry access).
        """
        if provider_context is None or not hasattr(
            provider_context, "contributor_registry"
        ):
            return

        registry = provider_context.contributor_registry
        for contributor in registry.get_all():
            try:
                await contributor.mount_to_app(app, container)
                logger.debug(
                    "web.contributor_mount_ok",
                    contributor_id=contributor.contributor_id,
                )
            except Exception as mount_exc:
                logger.error(
                    "web.contributor_mount_failed",
                    contributor_id=contributor.contributor_id,
                    error=str(mount_exc),
                    exc_type=type(mount_exc).__name__,
                )

    def _mount_static(self, app: Starlette) -> None:
        """Mount static file directory when configured."""
        static_config = getattr(self._web_config, "static", None)
        if static_config is None or not getattr(static_config, "enabled", False):
            return

        from starlette.staticfiles import StaticFiles

        try:
            app.mount(
                static_config.prefix,
                StaticFiles(
                    directory=static_config.directory,
                    html=getattr(static_config, "html", False),
                ),
                name="static",
            )
            logger.info(
                "web.static_files_mounted",
                prefix=static_config.prefix,
                directory=static_config.directory,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning(
                "web.static_files_mount_failed",
                directory=static_config.directory,
                error=str(exc),
            )

    async def _register_asgi_handler(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
    ) -> None:
        """Register the Starlette app as the ASGI handler on the Application."""
        from lexigram.app.base import Application

        lex_app = None
        try:
            lex_app = await container.resolve(
                Application,
                bypass_visibility=True,
            )
        except (AttributeError, UnresolvableDependencyError) as exc:
            logger.warning("app_resolution_failed", error=str(exc))

        if lex_app:
            if hasattr(lex_app, "set_asgi_handler"):
                lex_app.set_asgi_handler(app)
            else:
                lex_app._asgi_handler = app  # type: ignore[attr-defined]
