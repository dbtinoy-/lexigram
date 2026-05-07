"""Integration sub-provider — cache decorator and SQL context bridge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.tenancy.config import IntegrationConfig
from lexigram.tenancy.integration.cache_decorator import TenantCacheKeyDecorator

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )
    from lexigram.di.resolution.resolver import ServiceResolver

logger = get_logger(__name__)


class TenantIntegrationProvider(Provider):
    """Registers cross-package integration features.

    Both features degrade gracefully when the dependent package is absent:
    - Cache key decoration: skipped if ``lexigram-cache`` is not installed.
    - SQL context bridge: skipped if ``lexigram-sql`` is not installed.
    """

    name = "tenant_integration"

    def __init__(self, config: IntegrationConfig) -> None:
        """Initialise the provider.

        Args:
            config: Integration feature configuration.
        """
        super().__init__()
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register integration feature bindings.

        Args:
            container: The DI container registrar.
        """
        if self._config.cache_key_prefix:
            from lexigram.contracts.infra.cache import CacheBackendProtocol
            from lexigram.primitives.context import Context

            if container.has(CacheBackendProtocol) and container.has(Context):

                async def _cache_decorator_factory(
                    resolver: ServiceResolver,
                ) -> TenantCacheKeyDecorator:
                    inner = await resolver.resolve(CacheBackendProtocol)
                    ctx = await resolver.resolve(Context)
                    return TenantCacheKeyDecorator(inner=inner, ctx=ctx)

                container.singleton(
                    TenantCacheKeyDecorator,
                    factory=_cache_decorator_factory,
                )
                logger.debug("tenant_cache_key_decorator_registered")

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire integration features.

        Args:
            container: The DI container for boot phase.
        """
        if not self._config.sql_context_bridge:
            return

        await self._boot_sql_bridge(container)

    async def _boot_sql_bridge(self, container: BootContainerProtocol) -> None:
        """Register the SQL context bridge ASGI middleware if available.

        Args:
            container: The DI container for boot phase.
        """
        from lexigram.contracts.web.middleware import MiddlewareRegistryProtocol
        from lexigram.primitives.context import Context
        from lexigram.tenancy.integration.sql_bridge import TenantSQLContextBridge

        resolve_optional = getattr(container, "resolve_optional", None)
        if not resolve_optional:
            logger.debug(
                "container_does_not_support_resolve_optional_skipping_sql_bridge"
            )
            return

        try:
            middleware_registry = await resolve_optional(MiddlewareRegistryProtocol)
        except Exception:
            middleware_registry = None

        if middleware_registry is None:
            logger.debug("middleware_registry_not_available_skipping_sql_bridge")
            return

        try:
            ctx = await container.resolve(Context)

            def _bridge_factory(app: object) -> TenantSQLContextBridge:
                return TenantSQLContextBridge(
                    app=app,  # type: ignore[arg-type]
                    ctx=ctx,
                )

            middleware_registry.register_middleware(_bridge_factory)
            logger.debug("tenant_sql_context_bridge_registered")
        except Exception as exc:
            logger.warning("tenant_sql_bridge_boot_failed", error=str(exc))

    async def shutdown(self) -> None:
        """No-op shutdown."""


__all__ = ["TenantIntegrationProvider"]
