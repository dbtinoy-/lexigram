"""Intelligence Provider for Lexigram Framework dependency injection.

This module defines the main provider class that integrates Lexigram AI
with the Lexigram Framework's dependency injection system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.config import AIConfig
from lexigram.contracts import (
    CacheBackendProtocol,
    HealthCheckResult,
    HealthStatus,
    ProviderPriority,
)
from lexigram.contracts.ai import AIProviderProtocol
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.ai.llm.config import ClientConfig
    from lexigram.ai.observability.metrics import AIMetrics
    from lexigram.vector.config import VectorConfig

logger = get_logger(__name__)


class AIProvider(Provider, AIProviderProtocol):
    """Provider for registering Intelligence services with Lexigram DI container.

    This provider orchestrates sub-providers (LLMProvider, VectorProvider,
    RAGProvider) and is solely responsible for monitoring,
    governance, and AIProvider-specific services (RAGCache).

    Example:
        >>> from lexigram.app import Application
        >>> from lexigram.ai import AIModule
        >>>
        >>> app = Application()
        >>> app.add_module(AIModule.configure(...))
        >>>
        >>> # LLMClientProtocol is now available for injection
        >>> @Controller("/chat")
        >>> class ChatController:
        ...     def __init__(self, llm: LLMClientProtocol):
        ...         self.llm = llm
    """

    name = "ai"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "ai"
    config_model: type | None = AIConfig
    optional_dependencies: tuple[str, ...] = ("db", "cache")

    def __init__(
        self,
        config: AIConfig | None = None,
        llm_config: ClientConfig | None = None,
        vector_config: VectorConfig | None = None,
        name: str = "ai",
    ) -> None:
        """Initialize the Intelligence Provider.

        Args:
            config: Initial AI configuration (optional; can be set by orchestrator)
            llm_config: LLM-specific configuration (overrides config.llm)
            vector_config: Vector-specific configuration (overrides config.vector)
            name: Provider name
        """
        super().__init__(name=name)
        self._config_override = config

        # Configuration overrides
        self._llm_config_override = llm_config
        self._vector_config_override = vector_config

        # Sub-provider references — populated in register()
        self._llm_sub: Any | None = None  # LLMProvider
        self._vector_sub: Any | None = None  # VectorProvider
        self._rag_sub: Any | None = None  # RAGProvider

        # AIProvider-specific instances — populated in boot()
        self._rag_cache: Any | None = None
        self._metrics: AIMetrics | None = None
        self._governance: Any | None = None

        # Resolved optional dependencies
        self._database_provider: DatabaseProviderProtocol | None = None
        self._cache_backend: CacheBackendProtocol | None = None

    @property
    def intelligence_config(self) -> AIConfig:
        """Get the current AI configuration (from override or container-provided config)."""
        cfg = self._config_override or self.config or AIConfig()
        # Apply config overrides
        if self._llm_config_override:
            cfg.llm = self._llm_config_override
        if self._vector_config_override:
            cfg.vector = self._vector_config_override
        return cfg

    @property
    def database_provider(self) -> DatabaseProviderProtocol | None:
        """Get the resolved database provider (set during boot)."""
        return self._database_provider

    @property
    def cache_backend(self) -> CacheBackendProtocol | None:
        """Get the resolved cache backend (set during boot)."""
        return self._cache_backend

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register services with the DI container.

        Registers monitoring and config singletons directly; governance is
        registered by the GovernanceProvider discovered via the
        "lexigram.ai.subsystems" entry point. Delegates LLM, Vector, and
        RAG service registration to the respective sub-providers.

        Args:
            container: The Lexigram DI container
        """
        logger.info("Registering Lexigram AI services with container")

        # Resolve AIConfig from container (set by orchestrator) or use default
        intelligence_config = self.config or AIConfig()

        # Apply config overrides if provided
        if self._llm_config_override:
            intelligence_config.llm = self._llm_config_override
        if self._vector_config_override:
            intelligence_config.vector = self._vector_config_override

        # Register config first so sub-services can inject it
        container.singleton(AIConfig, lambda: intelligence_config)

        # Monitoring — always registered; AIProvider is the observability orchestrator
        from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl
        from lexigram.ai.observability.health import AIHealthMonitor
        from lexigram.ai.observability.metrics import AIMetrics
        from lexigram.ai.observability.tracing import AITracer
        from lexigram.contracts.ai.callbacks import CallbackManagerProtocol

        container.singleton(AIHealthMonitor)
        container.singleton(AIMetrics)
        container.singleton("ai_metrics", AIMetrics)
        container.singleton(AITracer)
        container.singleton("ai_tracer", AITracer)
        container.singleton(CallbackManagerProtocol, CallbackManagerImpl)
        container.singleton("callback_manager", CallbackManagerImpl)

        # LLM — delegate to LLMProvider
        if intelligence_config.llm:
            from lexigram.ai.llm.di.provider import LLMProvider

            self._llm_sub = LLMProvider(
                intelligence_config.llm,
                cache_backend=self._cache_backend,
            )
            await self._llm_sub.register(container)

            # Vector — delegate to VectorProvider
        if intelligence_config.vector:
            from lexigram.vector.di.provider import VectorProvider

            self._vector_sub = VectorProvider(intelligence_config.vector)
            await self._vector_sub.register(container)

        # RAG — delegate to RAGProvider
        if intelligence_config.rag:
            from lexigram.ai.rag.di.provider import RAGProvider

            self._rag_sub = RAGProvider(intelligence_config.rag)
            await self._rag_sub.register(container)

        # RAG cache — AIProvider-specific (wraps injected CacheBackendProtocol)
        if self._cache_backend:
            from lexigram.ai.rag.cache.manager import RAGCache

            container.singleton(RAGCache, lambda: self._rag_cache)
            container.singleton("rag_cache", lambda: self._rag_cache)

        # ------------------------------------------------------------------
        # Entry-point discovery for additional AI sub-packages.
        # Packages that declare the "lexigram.ai.subsystems" entry-point
        # group are loaded here without any hardcoded imports.
        # The three core subsystems (llm, vector, rag) are intentionally
        # skipped as they are wired above with explicit config injection.
        # ------------------------------------------------------------------
        _SUBSYSTEM_CONFIGS: dict[str, Any] = {
            "llm": intelligence_config.llm,
            "vector": intelligence_config.vector,
            "rag": intelligence_config.rag,
            "governance": intelligence_config.governance,
            "observability": intelligence_config.observability,
        }
        try:
            from importlib.metadata import entry_points as _entry_points

            for _ep in _entry_points(group="lexigram.ai.subsystems"):
                config_arg = _SUBSYSTEM_CONFIGS.get(_ep.name)
                _provider_cls = _ep.load()
                _sub_provider = (
                    _provider_cls(config=config_arg)
                    if config_arg is not None
                    else _provider_cls()
                )
                await _sub_provider.register(container)
                logger.info(
                    "Registered AI subsystem via entry-point",
                    subsystem=_ep.name,
                    provider=_ep.value,
                )
        except ImportError:
            logger.debug(
                "importlib.metadata unavailable; skipping AI subsystem discovery"
            )

        logger.info("Lexigram AI services registered successfully")

    async def chat(
        self,
        messages: list[Any],
        tools: list[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Chat with optional tool calling. Delegates to LLM sub-provider's client."""
        if not self._llm_sub or not self._llm_sub._llm_client:
            raise RuntimeError("LLM client not configured. Cannot perform chat.")
        return await self._llm_sub._llm_client.complete(messages, tools=tools, **kwargs)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Start the intelligence provider.

        Performs async I/O only for AIProvider-specific services: RAGCache.
        Sub-providers handle their own async initialization during register().

        Args:
            container: The DI container
        """
        logger.info("Starting Lexigram AI provider")

        # Resolve optional dependencies from container
        try:
            self._database_provider = await container.resolve(DatabaseProviderProtocol)
        except (ValueError, KeyError, TypeError):
            logger.debug(
                "DatabaseProviderProtocol not available; governance persistence disabled"
            )

        try:
            self._cache_backend = await container.resolve(CacheBackendProtocol)
        except (ValueError, KeyError, TypeError):
            logger.debug(
                "CacheBackendProtocol not available; RAG cache and governance caching disabled"
            )

        # RAG cache (wraps platform CacheBackendProtocol)
        if self._cache_backend:
            from lexigram.ai.rag.cache.manager import RAGCache

            self._rag_cache = RAGCache(backend=self._cache_backend)
            logger.info("Initialized RAGCache")

        logger.info("Lexigram AI provider started successfully")

    async def shutdown(self) -> None:
        """Clean up resources on application shutdown."""
        logger.info("Shutting down Lexigram AI provider")

        # Shutdown sub-providers
        for sub in (self._llm_sub, self._vector_sub, self._rag_sub):
            if sub is not None:
                try:
                    await sub.shutdown()
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as exc:
                    logger.warning("Error shutting down sub-provider: %s", exc)

        # Clear all references
        self._llm_sub = None
        self._vector_sub = None
        self._rag_sub = None
        self._rag_cache = None

        logger.info("Lexigram AI provider shutdown complete")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check provider health by aggregating sub-provider and local service checks.

        Returns:
            Structured HealthCheckResult with component health information
        """
        import time

        start_time = time.perf_counter()
        details: dict[str, Any] = {"components": {}}
        overall_status = HealthStatus.HEALTHY
        errors = []

        # LLM health — delegate to sub-provider
        if self._llm_sub is not None:
            cl_start = time.perf_counter()
            try:
                cl_health = await self._llm_sub.health_check(timeout=timeout)
                if isinstance(cl_health, dict):
                    details["components"]["llm"] = cl_health
                    if cl_health.get("status") not in ("healthy", None):
                        overall_status = HealthStatus.DEGRADED
                elif hasattr(cl_health, "model_dump"):
                    details["components"]["llm"] = cl_health.model_dump()
                    if (
                        hasattr(cl_health, "status")
                        and cl_health.status != HealthStatus.HEALTHY
                    ):
                        overall_status = HealthStatus.DEGRADED
                else:
                    details["components"]["llm"] = {"status": "healthy"}
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                logger.exception("LLM health check failed")
                details["components"]["llm"] = {"status": "unhealthy", "error": str(e)}
                overall_status = HealthStatus.DEGRADED
                errors.append(f"LLM: {e}")
            details["components"]["llm"]["latency_ms"] = (
                time.perf_counter() - cl_start
            ) * 1000

        # Vector health — delegate to sub-provider
        if self._vector_sub is not None:
            v_start = time.perf_counter()
            try:
                v_health = await self._vector_sub.health_check(timeout=timeout)
                if isinstance(v_health, HealthCheckResult):
                    details["components"]["vector"] = (
                        v_health.model_dump()
                        if hasattr(v_health, "model_dump")
                        else vars(v_health).copy()
                    )
                    if v_health.status != HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                elif isinstance(v_health, dict):
                    details["components"]["vector"] = v_health
                else:
                    details["components"]["vector"] = {"status": "healthy"}
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                logger.exception("Vector store health check failed")
                details["components"]["vector"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                overall_status = HealthStatus.DEGRADED
                errors.append(f"Vector: {e}")
            details["components"]["vector"]["latency_ms"] = (
                time.perf_counter() - v_start
            ) * 1000

        return HealthCheckResult(
            component="ai",
            status=overall_status,
            details=details,
            error=" | ".join(errors) if errors else None,
            duration_ms=(time.perf_counter() - start_time) * 1000,
        )


__all__ = ["AIProvider"]
