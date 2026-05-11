"""Lexigram GraphQL Provider

Provider for GraphQL functionality in Lexigram Framework.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, TypeVar, cast

from lexigram.contracts.core import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
    ProviderPriority,
)
from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.contracts.web import WebRateLimiterProtocol
from lexigram.di.provider import Provider
from lexigram.graphql import constants as const
from lexigram.graphql.config import GraphQLConfig
from lexigram.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )
    from lexigram.graphql.core.caching import ResponseCache
    from lexigram.graphql.core.context import ContextFactory
    from lexigram.graphql.core.execution import GraphQLExecutorProtocol
    from lexigram.graphql.monitoring.metrics import MetricsCollectorProtocol

    # Types used only for annotations inside the provider
    from lexigram.graphql.schema.builder import SchemaBuilderProtocol
    from lexigram.graphql.security.rate_limit import UnifiedRateLimiter


_T = TypeVar("_T")


def _require(instance: _T | None, name: str) -> _T:
    """Return *instance* or raise RuntimeError if ``boot()`` has not been called.

    Args:
        instance: The service instance (``None`` until ``boot()`` runs).
        name: Human-readable service class name for the error message.

    Returns:
        The non-None instance.

    Raises:
        RuntimeError: When ``boot()`` has not completed before resolution.
    """
    if instance is None:
        raise RuntimeError(
            f"{name} not initialised. "
            "Ensure GraphQLProvider.boot() has been called before resolving this service.",
        )
    return instance


class GraphQLProvider(Provider):
    """Provider for GraphQL functionality.

    This provider integrates GraphQL capabilities into the Lexigram Framework,
    including schema building, execution, federation, and monitoring.

    Features:
    - GraphQL schema management and execution
    - Apollo Federation support (subgraph)
    - DataLoaderProtocol for batching and caching
    - Query validation and depth limiting
    - Metrics collection and tracing
    - Subscription support
    - Security features (rate limiting, auth)

    Configuration:
        The provider is configured via GraphQLConfig in the application
        configuration. If no config is provided, sensible defaults are used.

    Usage:
        ```python
        app = Application()
        app.add_provider(GraphQLProvider())
        ```
    """

    name = "graphql"
    priority = ProviderPriority.PRESENTATION
    config_key: str | None = "graphql"
    config_model: type | None = GraphQLConfig

    def __init__(
        self,
        config: GraphQLConfig | None = None,
        query_class: Any | None = None,
        mutation_class: Any | None = None,
        subscription_class: Any | None = None,
        context_factory_class: Any | None = None,
        priority: ProviderPriority = ProviderPriority.PRESENTATION,
    ) -> None:
        """Initialize the GraphQL provider.

        Args:
            config: GraphQL configuration. If None, uses defaults.
            query_class: Optional GraphQL Query class.
            mutation_class: Optional GraphQL Mutation class.
            subscription_class: Optional GraphQL Subscription class.
            context_factory_class: Optional custom ContextFactory subclass.
                When ``None``, the framework's default ``ContextFactory`` is used.
            priority: Provider priority for initialization order.
        """
        super().__init__(priority=priority)
        self._requested_config = config
        self.config = config
        self._identity: Any = None
        self.query_class = query_class
        self.mutation_class = mutation_class
        self.subscription_class = subscription_class
        self._context_factory_class = context_factory_class
        self._schema_builder: SchemaBuilderProtocol | None = None
        self._executor: GraphQLExecutorProtocol | None = None
        self._metrics_collector: MetricsCollectorProtocol | None = None
        self._context_factory: Any | None = None
        self._response_cache: ResponseCache | None = None
        self._ws_transport: Any | None = None
        self._rate_limiter: UnifiedRateLimiter | None = None

    @classmethod
    def from_config(cls, config: GraphQLConfig, **context: Any) -> GraphQLProvider:
        """Create a GraphQLProvider from config.

        Context kwargs may include query_class, mutation_class, subscription_class,
        and context_factory_class.
        """
        return cls(
            config=config,
            query_class=context.get("query_class"),
            mutation_class=context.get("mutation_class"),
            subscription_class=context.get("subscription_class"),
            context_factory_class=context.get("context_factory_class"),
        )

    @classmethod
    def auto_discover(
        cls,
        *packages: str,
        config: GraphQLConfig | None = None,
        **kwargs: Any,
    ) -> GraphQLProvider:
        """Create a ``GraphQLProvider`` by scanning packages for Strawberry types.

        Scans each package recursively for classes decorated with
        ``@strawberry.type`` whose name is ``Query``, ``Mutation``, or
        ``Subscription``.  Use ``@strawberry.type`` plus the naming convention
        or explicitly set ``__graphql_role__ = "query"`` / ``"mutation"`` /
        ``"subscription"`` on the class to override the name-based detection.

        Args:
            *packages: Dotted Python package paths to scan, e.g.
                ``"my_app.graphql"``.
            config: Optional :class:`~lexigram.graphql.config.GraphQLConfig`.
                Falls back to framework defaults when not provided.
            **kwargs: Extra keyword arguments forwarded to
                :class:`GraphQLProvider.__init__`.

        Returns:
            A configured :class:`GraphQLProvider` instance.

        Example::

            app.add_provider(GraphQLProvider.auto_discover("my_app.graphql"))

        In ``my_app/graphql/schema.py``::

            import strawberry

            @strawberry.type
            class Query:
                @strawberry.field
                async def hello(self) -> str:
                    return "world"

            @strawberry.type
            class Mutation:
                @strawberry.mutation
                async def set_name(self, name: str) -> str:
                    return name
        """
        import importlib
        import pkgutil

        query_cls: Any = None
        mutation_cls: Any = None
        subscription_cls: Any = None

        def _is_strawberry_type(obj: Any) -> bool:
            return isinstance(obj, type) and hasattr(obj, "__strawberry_definition__")

        def _scan(pkg_name: str) -> None:
            nonlocal query_cls, mutation_cls, subscription_cls
            try:
                root = importlib.import_module(pkg_name)
            except ImportError:
                logger.debug("graphql.auto_discover.import_failed", package=pkg_name)
                return

            modules_to_scan = [root]
            root_path = getattr(root, "__path__", None)
            if root_path is not None:
                for _finder, modname, _ispkg in pkgutil.walk_packages(
                    root_path,
                    prefix=pkg_name + ".",
                    onerror=lambda n: logger.debug(
                        "graphql.auto_discover.walk_error", module=n
                    ),
                ):
                    try:
                        modules_to_scan.append(importlib.import_module(modname))
                    except Exception:  # noqa: BLE001
                        pass

            for module in modules_to_scan:
                for attr_name in dir(module):
                    try:
                        obj = getattr(module, attr_name)
                    except Exception:  # noqa: BLE001, S112
                        continue
                    if not _is_strawberry_type(obj):
                        continue
                    role: str = (
                        getattr(obj, "__graphql_role__", "").lower()
                        or attr_name.lower()
                    )
                    if role == "query" and query_cls is None:
                        query_cls = obj
                        logger.debug("graphql.auto_discover.query", cls=obj.__name__)
                    elif role == "mutation" and mutation_cls is None:
                        mutation_cls = obj
                        logger.debug("graphql.auto_discover.mutation", cls=obj.__name__)
                    elif role == "subscription" and subscription_cls is None:
                        subscription_cls = obj
                        logger.debug(
                            "graphql.auto_discover.subscription", cls=obj.__name__
                        )

        for pkg in packages:
            _scan(pkg)

        return cls(
            config=config,
            query_class=query_cls,
            mutation_class=mutation_cls,
            subscription_class=subscription_cls,
            context_factory_class=kwargs.get("context_factory_class"),
        )

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register GraphQL services with the DI container.

        Args:
            container: The dependency injection container registrar.
        """
        # Import here to avoid circular imports
        from lexigram.graphql.controllers import GraphQLController
        from lexigram.graphql.core.caching import ResponseCache
        from lexigram.graphql.core.context import ContextFactory
        from lexigram.graphql.core.execution import GraphQLExecutorProtocol
        from lexigram.graphql.dataloader.cache import InMemoryCache
        from lexigram.graphql.monitoring.metrics import MetricsCollectorProtocol
        from lexigram.graphql.schema.builder import SchemaBuilderProtocol
        from lexigram.graphql.security.rate_limit import RateLimiter, UnifiedRateLimiter

        # Register the provider itself for injection
        container.singleton(GraphQLProvider, lambda: self)

        # Register core services — fully initialised in boot() before resolution;
        # _require() raises RuntimeError if resolution is attempted before boot().
        container.singleton(
            GraphQLExecutorProtocol,
            lambda: _require(self._executor, "GraphQLExecutorProtocol"),
        )
        container.singleton(
            SchemaBuilderProtocol,
            lambda: _require(self._schema_builder, "SchemaBuilderProtocol"),
        )
        container.singleton(
            MetricsCollectorProtocol,
            lambda: _require(self._metrics_collector, "MetricsCollectorProtocol"),
        )
        container.singleton(
            ContextFactory, lambda: _require(self._context_factory, "ContextFactory")
        )
        container.singleton(
            ResponseCache, lambda: _require(self._response_cache, "ResponseCache")
        )

        # Register default implementations
        container.singleton(InMemoryCache, InMemoryCache)

        # UnifiedRateLimiter registered with no-op fallback; boot() will wire
        # the real WebRateLimiterProtocol dependency via self._rate_limiter.
        container.singleton(
            RateLimiter,
            lambda: (
                self._rate_limiter
                if self._rate_limiter is not None
                else UnifiedRateLimiter()
            ),
        )
        container.singleton(
            UnifiedRateLimiter,
            lambda: (
                self._rate_limiter
                if self._rate_limiter is not None
                else UnifiedRateLimiter()
            ),
        )

        # Register GraphQLController for the web layer
        container.singleton(GraphQLController, lambda: GraphQLController(self))

        # Register WebSocket transport via contracts protocol (built in boot())
        from lexigram.contracts.graphql.protocols import WebSocketTransportProtocol

        container.singleton(
            WebSocketTransportProtocol,
            lambda: _require(self._ws_transport, "WebSocketTransportProtocol"),
        )

    async def boot(self, container: BootContainerProtocol) -> None:
        """Initialize GraphQL components.

        Args:
            container: The application container resolver.
        """
        # Import here to avoid circular imports
        from lexigram.contracts.core.identity import IdGeneratorProtocol
        from lexigram.graphql.config import GraphQLConfig
        from lexigram.graphql.core.context import ContextFactory
        from lexigram.graphql.core.execution import GraphQLExecutorProtocol
        from lexigram.graphql.monitoring.metrics import MetricsCollectorProtocol
        from lexigram.graphql.schema.builder import SchemaBuilderProtocol
        from lexigram.graphql.security.extensions import RateLimitExtension
        from lexigram.graphql.security.rate_limit import RateLimiter, UnifiedRateLimiter

        # Resolve core infrastructure (identity) for injection into services
        if container is not None and hasattr(container, "resolve"):
            with contextlib.suppress(UnresolvableDependencyError, AttributeError):
                self._identity = await container.resolve(IdGeneratorProtocol)

        # Get or create configuration
        self.config = self._requested_config or self.config or GraphQLConfig()

        # Initialize schema builder
        self._schema_builder = SchemaBuilderProtocol(self.config)

        # Configure query/mutation/subscription classes if set
        if hasattr(self, "query_class") and self.query_class is not None:
            self._schema_builder.query(self.query_class)
        if hasattr(self, "mutation_class") and self.mutation_class is not None:
            self._schema_builder.mutation(self.mutation_class)
        if hasattr(self, "subscription_class") and self.subscription_class is not None:
            self._schema_builder.subscription(self.subscription_class)

        # Build GraphQL rate limiter with constructor injection from web contracts.
        web_rate_limiter = None
        if container is not None and hasattr(container, "resolve"):
            try:
                web_rate_limiter = await container.resolve(WebRateLimiterProtocol)
            except UnresolvableDependencyError:
                web_rate_limiter = None

        self._rate_limiter = UnifiedRateLimiter(web_rate_limiter=web_rate_limiter)

        # Wire RateLimitExtension into schema (replaces ad-hoc executor hook)
        rate_limiter: RateLimiter | None = self._rate_limiter
        if rate_limiter is not None:
            self._schema_builder.add_extension(
                RateLimitExtension(
                    rate_limiter=rate_limiter,
                    max_requests=self.config.rate_limit.requests_per_minute
                    if self.config.rate_limit
                    else const.DEFAULT_REQUESTS_PER_MINUTE,
                ),
            )

        schema = self._schema_builder.build()

        # Resolve MetricsRecorderProtocol from kernel for unified observability
        recorder = None
        if container is not None and hasattr(container, "resolve"):
            with contextlib.suppress(
                ImportError,
                AttributeError,
                RuntimeError,
                TypeError,
                UnresolvableDependencyError,
            ):
                from lexigram.contracts.observability.metrics import (
                    MetricsRecorderProtocol,
                )

                recorder = await container.resolve(MetricsRecorderProtocol)
        self._metrics_collector = MetricsCollectorProtocol(recorder=recorder)

        # Resolve EventBusProtocol for execution lifecycle events
        event_bus = None
        if container is not None and hasattr(container, "resolve"):
            with contextlib.suppress(
                ImportError,
                AttributeError,
                RuntimeError,
                TypeError,
                UnresolvableDependencyError,
            ):
                from lexigram.contracts.events import EventBusProtocol

                event_bus = await container.resolve(EventBusProtocol)

        self._executor = GraphQLExecutorProtocol(schema, event_bus=event_bus)

        # Initialize context factory — use custom class if provided, otherwise default ContextFactory.
        # Pre-populate any DataLoaderProtocol factories registered via
        # SchemaBuilderProtocol.add_dataloader() before boot() was called.
        factory_cls = self._context_factory_class or ContextFactory
        self._context_factory = factory_cls(
            config=self.config,
            resolver=container,
            dataloader_factories=dict(self._schema_builder._dataloader_factories),
            identity=self._identity,
        )

        # Wire CacheConfig to ResponseCache — use the platform CacheBackendProtocol from the
        # container if one is registered; otherwise fall back to a local in-memory shim
        # so the GraphQL provider works standalone without a cache provider mounted.
        from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
        from lexigram.graphql.core.caching import ResponseCache, _MemoryCacheShim

        cache_cfg = self.config.cache
        cache_backend: CacheBackendProtocol = _MemoryCacheShim(
            default_ttl=cache_cfg.default_max_age or 300
        )  # type: ignore[assignment]
        if container is not None and hasattr(container, "resolve"):
            try:
                resolver: BootContainerProtocol = container
                cache_backend = await resolver.resolve(CacheBackendProtocol)
            except (UnresolvableDependencyError, RuntimeError, ValueError):
                logger.debug(
                    "No CacheBackendProtocol bound; using local in-memory shim for GraphQL response cache."
                )

        self._response_cache = ResponseCache(
            backend=cache_backend,
            enabled=cache_cfg.enabled,
            default_ttl=cache_cfg.default_max_age or 300,
        )

        # Build WebSocket subscription transport
        from lexigram.graphql.subscriptions.transport import GraphQLWSTransport

        auth_handler = None
        with contextlib.suppress(
            ImportError,
            AttributeError,
            RuntimeError,
            TypeError,
            UnresolvableDependencyError,
        ):
            from lexigram.graphql.subscriptions.auth import SubscriptionAuth

            auth_handler = await container.resolve(
                SubscriptionAuth,
                bypass_visibility=True,
            )

        self._ws_transport = GraphQLWSTransport(
            execute=schema.execute,
            subscribe=schema.subscribe,
            context_factory=self._context_factory,
            auth_handler=auth_handler,
        )

        # Schema diff — compare current schema against baseline file when configured
        await self._run_schema_diff(schema)

    async def _run_schema_diff(self, current_schema: Any) -> None:
        """Compare *current_schema* against the configured baseline SDL file.

        Only runs when :attr:`~lexigram.graphql.config.GraphQLConfig.schema_baseline_path`
        is set.  Logs breaking removals at WARNING level and non-breaking additions
        at DEBUG level.

        Args:
            current_schema: The freshly built Strawberry :class:`Schema` object.
        """
        if self.config is None or not self.config.schema_baseline_path:
            return

        import pathlib

        from lexigram.graphql.schema.diff import SchemaDiffer

        baseline_path = pathlib.Path(self.config.schema_baseline_path)
        if not baseline_path.exists():
            logger.warning(
                "graphql.schema_diff.baseline_not_found",
                path=str(baseline_path),
            )
            return

        try:
            baseline_sdl = baseline_path.read_text(encoding="utf-8")
            # Parse the SDL into a comparable structure using strawberry's schema
            # introspection.  We convert both to type-name sets via SchemaDiffer.
            from graphql import build_ast_schema, parse

            baseline_schema = build_ast_schema(parse(baseline_sdl))
            differ = SchemaDiffer()
            diff = differ.diff(baseline_schema, current_schema)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "graphql.schema_diff.error",
                path=str(baseline_path),
                error=str(exc),
            )
            return

        if not diff.has_changes():
            logger.debug("graphql.schema_diff.no_changes", path=str(baseline_path))
            return

        if diff.breaking:
            for removed in sorted(diff.removed):
                logger.warning(
                    "graphql.schema_diff.breaking_removal",
                    type_name=removed,
                    baseline=str(baseline_path),
                )
        for added in sorted(diff.added):
            logger.debug(
                "graphql.schema_diff.addition",
                type_name=added,
                baseline=str(baseline_path),
            )

    def executor(self) -> GraphQLExecutorProtocol | None:
        """Get the GraphQL executor instance."""
        return self._executor

    @property
    def context_factory(self) -> ContextFactory | None:
        """Get the GraphQL context factory instance."""
        return self._context_factory

    async def shutdown(self) -> None:
        """Shutdown GraphQL components."""
        if self._metrics_collector is not None:
            await self._metrics_collector.close()
        if self._response_cache is not None and hasattr(self._response_cache, "close"):
            await self._response_cache.close()
        self._schema_builder = None
        self._executor = None
        self._metrics_collector = None
        self._context_factory = None
        self._response_cache = None
        self._ws_transport = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check the health of GraphQL components.

        Returns:
            Health check results.
        """
        details = {
            "schema_loaded": self._schema_builder is not None,
            "executor_ready": self._executor is not None,
            "metrics_enabled": self._metrics_collector is not None,
            "federation_enabled": self.config.federation.enabled
            if self.config
            else False,
        }

        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY
            if self._executor is not None
            else HealthStatus.UNHEALTHY,
            details=details,
            category=HealthCheckCategory.READINESS,
        )


__all__ = ["GraphQLProvider"]
