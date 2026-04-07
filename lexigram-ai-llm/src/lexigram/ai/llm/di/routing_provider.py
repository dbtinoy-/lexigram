"""LLM Routing Provider for Lexigram Framework dependency injection.

Registers the multi-provider LLMRouter and its dependencies
(quota backend, inference logger, and routing clients) with the
DI container so the router is injectable throughout the application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.routing import (
    InferenceLoggerProtocol,
    LLMRouterProtocol,
    QuotaBackendProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.decorators import inject
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.llm.selection.core import ModelSelector
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.data import DatabaseProviderProtocol

from lexigram.ai.llm.routing import (
    DatabaseInferenceLogger,
    DatabaseQuotaBackend,
    InMemoryInferenceLogger,
    InMemoryQuotaBackend,
    LLMConfig,
    LLMRouter,
)
from lexigram.ai.llm.routing.di_factories import create_routing_clients

logger = get_logger(__name__)

__all__ = ["LLMRoutingProvider"]


@inject
class LLMRoutingProvider(Provider):
    """Provider that registers the multi-provider LLM router with the DI container.

    Builds the :class:`~lexigram.ai.llm.routing.LLMRouter` from a
    :class:`~lexigram.ai.llm.routing.LLMConfig`, chooses the appropriate
    quota backend and inference logger, and registers everything as singletons.

    Example:
        >>> from lexigram.ai.llm.module import LLMModule
        >>> from lexigram.ai.llm.routing import LLMConfig
        >>>
        >>> app.use(LLMModule.configure(routing=LLMConfig.from_env()))
        >>>
        >>> # LLMRouterProtocol is now injectable:
        >>> class MyService:
        ...     def __init__(self, router: LLMRouterProtocol) -> None:
        ...         self.router = router
    """

    name = "llm_routing"
    priority = ProviderPriority.DOMAIN

    def __init__(
        self,
        config: LLMConfig | None = None,
        database_provider: DatabaseProviderProtocol | None = None,
        model_selector: ModelSelector | None = None,
    ) -> None:
        """Initialise the LLM routing provider.

        Args:
            config: Routing configuration; defaults to ``LLMConfig.from_env()``.
            database_provider: Injected DB provider used when ``quota.backend``
                or ``logging.backend`` is ``database``.
            model_selector: Optional model selector for capability-based
                routing.  When provided, ``required_capabilities`` in route
                kwargs will filter providers whose models lack the requested
                capabilities.
        """
        super().__init__(name="llm_routing")
        self.config = config or LLMConfig.from_env()
        self.database_provider = database_provider
        self._model_selector = model_selector
        self._router: LLMRouter | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Build and register the LLMRouter with the DI container.

        Args:
            container: The Lexigram DI container registrar.
        """
        logger.info("llm.routing: registering multi-provider router")

        clients = create_routing_clients(self.config)

        quota_backend: QuotaBackendProtocol
        if self.config.quota.backend == "database" and self.database_provider:
            quota_backend = DatabaseQuotaBackend(db=self.database_provider)
            logger.info("llm.routing: using database quota backend")
        else:
            quota_backend = InMemoryQuotaBackend()
            logger.info("llm.routing: using in-memory quota backend")

        inference_logger: InferenceLoggerProtocol
        if self.config.logging.backend == "database" and self.database_provider:
            inference_logger = DatabaseInferenceLogger(db=self.database_provider)
            logger.info("llm.routing: using database inference logger")
        else:
            inference_logger = InMemoryInferenceLogger(
                max_size=self.config.logging.max_entries,
            )
            logger.info("llm.routing: using in-memory inference logger")

        router = LLMRouter(
            config=self.config,
            clients=clients,
            quota_backend=quota_backend,
            inference_logger=inference_logger,
            model_selector=self._model_selector,
        )
        self._router = router

        container.singleton(LLMRouterProtocol, lambda: router)
        container.singleton("llm_router", lambda: router)
        container.singleton(InferenceLoggerProtocol, lambda: inference_logger)
        logger.info(
            "llm.routing: router registered with %d providers",
            len(self.config.providers),
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot phase — no-op for this provider.

        Args:
            container: The DI container resolver.
        """

    async def shutdown(self) -> None:
        """Close all routing clients on application shutdown."""
        if self._router is not None:
            try:
                await self._router.close()
            except (ConnectionError, TimeoutError, OSError) as exc:
                logger.warning("llm.routing: error during shutdown", error=str(exc))
            self._router = None
        logger.info("llm.routing: provider shutdown complete")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return basic health information for the router.

        Args:
            timeout: Unused; retained for interface compatibility.

        Returns:
            A dict with ``status`` and ``providers`` keys.
        """
        providers = [p.name for p in self.config.providers]
        return HealthCheckResult(
            component="llm_routing",
            status=(
                HealthStatus.HEALTHY
                if self._router is not None
                else HealthStatus.DEGRADED
            ),
            details={"providers": providers},
        )
