from __future__ import annotations

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import get_logger

logger = get_logger(__name__)


class CoreInfrastructureProvider(Provider):
    """Provider for **shared low-level Lexigram infrastructure**.

    This is a *leaf* provider (no sub-providers) that registers the primitive
    cross-cutting services needed by every other provider:

    * ``Context`` / ``ContextVarRegistry`` — request-scoped context propagation
    * ``Registry`` — a named-object registry for ad-hoc service look-up

    **Do NOT confuse with** :class:`~lexigram.app.di.provider.CoreProvider`:

    +-----------------------------------+----------------------------------------------------+
    | ``CoreInfrastructureProvider``    | ``CoreProvider``                                   |
    +===================================+====================================================+
    | Leaf provider, no sub-providers   | Aggregating provider, no direct registrations      |
    +-----------------------------------+----------------------------------------------------+
    | Registers concrete primitives     | Delegates to sub-providers via orchestrator        |
    +-----------------------------------+----------------------------------------------------+
    | Used inside the framework         | Used by application bootstrap (``LexigramApp``)    |
    +-----------------------------------+----------------------------------------------------+
    | ``name = "common"``               | ``name = "core"``                                  |
    +-----------------------------------+----------------------------------------------------+
    """

    name = "common"
    priority = ProviderPriority.INFRASTRUCTURE

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register common utilities with the container."""
        from lexigram.contracts.core.context import RequestContextProtocol
        from lexigram.primitives.context import (
            Context,
            ContextVarRegistry,
            RequestContext,
            create_default_context,
            get_request_context,
        )
        from lexigram.primitives.registry import Registry

        context = create_default_context()
        container.singleton(Context, instance=context)
        container.singleton(ContextVarRegistry, instance=context.registry)
        container.scoped(
            RequestContext,
            lambda: get_request_context(context.registry),
            validate=False,
        )
        # Bind protocol to implementation
        container.scoped(
            RequestContextProtocol,  # type: ignore[type-abstract]
            lambda: get_request_context(context.registry),
            validate=False,
        )
        container.singleton(Registry, Registry())

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Initialize common services."""
        logger.info("Lexigram Common infrastructure starting up")

    async def shutdown(self) -> None:
        """Clean up common resources."""
        logger.info("Lexigram Common infrastructure shutting down")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check health of shared infrastructure."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={
                "managers": ["Context", "Registry"],
                "package": "lexigram",
            },
        )


__all__ = ["CoreInfrastructureProvider"]
