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
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """No bindings at register time — all wiring happens in boot.

        Args:
            container: The DI container registrar.
        """

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire integration features.

        Args:
            container: The DI container for boot phase.
        """
        if self._config.cache_key_prefix:
            await self._boot_cache_decorator(container)

        if self._config.sql_context_bridge:
            await self._boot_sql_bridge(container)

    async def _boot_cache_decorator(self, container: BootContainerProtocol) -> None:
        """Register the tenant cache key decorator if lexigram-cache is installed.

        Args:
            container: The DI container for boot phase.
        """
        try:
            from lexigram.contracts.infra.cache import CacheBackendProtocol
            from lexigram.primitives.context import Context

            inner = await container.resolve(CacheBackendProtocol)
            ctx = await container.resolve(Context)
            decorator = TenantCacheKeyDecorator(inner=inner, ctx=ctx)
            container.singleton(TenantCacheKeyDecorator, decorator)
            logger.debug("tenant_cache_key_decorator_registered")
        except ImportError:
            logger.debug("lexigram_cache_not_installed_skipping_cache_decorator")
        except Exception as exc:
            logger.warning("tenant_cache_decorator_boot_failed", error=str(exc))

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
