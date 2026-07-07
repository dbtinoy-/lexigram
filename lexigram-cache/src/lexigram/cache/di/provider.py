"""
Integration layer for Lexigram Cache provider.

This module provides dependency injection and provider registration
for the cache service, integrating with lexigram's provider system.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from lexigram.cache.service.core import CacheService
    from lexigram.contracts import CacheBackendProtocol

# Import from root config.py - Single source of truth
from lexigram.cache.backends.registry import BackendRegistry
from lexigram.cache.config import (
    CacheBackendConfig,
    CacheConfig,
    resolve_backend_type,
)
from lexigram.cache.service.health import get_health_status as _get_health_status
from lexigram.cache.service.health import get_metrics as _get_metrics
from lexigram.cache.service.stampede import StampedeProtectedCache
from lexigram.contracts.core import (
    HealthCheckCategory,
    HealthCheckResult,
    HookRegistryProtocol,
    ProviderPriority,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts import ContainerRegistrarProtocol, ContainerResolverProtocol

logger = get_logger(__name__)

T = TypeVar("T")


class CacheProvider(Provider):
    """
    Lexigram Cache provider for lexigram integration.

    Integrates cache services with lexigram's provider system,
    managing lifecycle, configuration, and service registration.
    """

    name = "cache"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "cache"
    config_model: type | None = CacheConfig

    def __init__(self, config: CacheConfig | None = None) -> None:
        """Initialize the cache provider.

        Args:
            config: Optional cache configuration. When provided the provider is
                configured immediately (equivalent to calling :meth:`configure`).
        """
        super().__init__()
        self.config: CacheConfig | None = None
        self._services: dict[str, CacheService] = {}
        self._backends: dict[str, CacheBackendProtocol] = {}
        self._serializers: dict[str, Any] = {}
        self._protection: StampedeProtectedCache | None = None
        self._observed_pairs: list[tuple[Any, Any]] = []
        if config is not None:
            self.configure(config)

    @classmethod
    def from_config(cls, config: CacheConfig, **context: Any) -> CacheProvider:
        """Create a CacheProvider from a CacheConfig.

        The provider is created and immediately configured with the config dict.
        """
        provider = cls()
        provider.configure(
            config.model_dump() if hasattr(config, "model_dump") else config,
        )
        return provider

    def configure(self, config: dict[str, Any] | CacheConfig) -> None:
        """Configure the provider with cache settings."""
        if isinstance(config, CacheConfig):
            self.config = config
        else:
            # Convert dict config to CacheConfig
            self.config = CacheConfig(**config)

        # Initialize synchronously so the provider is usable immediately
        self._initialize_serializers()
        # Defer backend init until register() when container is available
        # self._initialize_backends()
        # Services init here; register() will re-init with protection if needed
        # self._initialize_services()

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register cache services with the container.

        Only binds factories — no I/O.  All real initialization happens in boot().
        """
        logger.info("Registering Lexigram Cache services with container")

        # Register backend registry
        self._backend_registry = BackendRegistry()
        container.singleton(BackendRegistry, self._backend_registry)

        # Register CacheStatusRegistry in the container (D4.1).
        # Using the container-managed singleton eliminates the module-level
        # global accessor (get_cache_status_registry).  Code that already
        # resolves via the container will use this instance; legacy call-sites
        # that still call get_cache_status_registry() will get the same object
        # once we assign it below.
        from lexigram.cache.service.registry import (
            CacheStatusRegistry,
            reset_cache_status_registry,
        )

        self._status_registry = CacheStatusRegistry()
        container.singleton(CacheStatusRegistry, self._status_registry)
        # Back-fill the module-level singleton so legacy call-sites resolve to
        # the same instance without requiring a container reference.
        reset_cache_status_registry()
        import lexigram.cache.service.registry as _reg_mod

        _reg_mod._registry = self._status_registry

        # AsyncStringSerializerProtocol initialization is synchronous — safe here
        self._initialize_serializers()

        # Register provider and protocol (no I/O)
        container.singleton(CacheProvider, self)
        from lexigram.contracts.infra.cache.protocols import CacheProviderProtocol

        container.singleton(CacheProviderProtocol, self)

        # Bind lazy factories that resolve after boot() populates self._backends / _services.
        # CacheBackendProtocol → the default backend (Result-based contract), symmetric
        # with the per-name bindings below.  CacheService → the ergonomic bare-value facade.
        from lexigram.cache.service.core import CacheService  # noqa: PLC0415
        from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol

        container.singleton(
            CacheBackendProtocol, factory=lambda: self.get_backend(None)
        )
        container.singleton(CacheService, factory=self.get_default_service)

        # Named bindings — one per configured, enabled backend
        if self.config:
            for backend_cfg in self.config.backends:
                if not backend_cfg.enabled:
                    continue
                _name = backend_cfg.name
                container.singleton(
                    CacheBackendProtocol,
                    factory=lambda n=_name: self.get_backend(n),
                    name=_name,
                )
                container.singleton(
                    CacheService,
                    factory=lambda n=_name: self.get_service(n),
                    name=_name,
                )
                logger.debug("registered_named_cache_binding", backend=_name)

        # Register the warming service so it can be resolved from the container (lazy)
        from lexigram.cache.service.warmer import CacheWarmer

        container.singleton(
            CacheWarmer,
            lambda: CacheWarmer(cache=self.get_default_service()._backend),  # type: ignore[arg-type]
        )

        # Register semantic cache if faiss is available
        self._register_semantic_cache(container)

        # Register a RedisStateStore for each Redis backend so that
        # create_backend() can resolve state_store.{name} during boot().
        if self.config:
            from lexigram.cache.stores.redis_state import (
                RedisStateStore,
            )
            from lexigram.cache.types import BackendType

            for backend_config in self.config.backends:
                if (
                    backend_config.enabled
                    and resolve_backend_type(backend_config) == BackendType.REDIS
                    and backend_config.redis_url
                ):
                    store = RedisStateStore(  # type: ignore[abstract]
                        url=backend_config.redis_url,
                        prefix=backend_config.key_prefix,
                    )
                    container.singleton(f"state_store.{backend_config.name}", store)
                    logger.debug(
                        "registered_redis_state_store", backend=backend_config.name
                    )

        await self._discover_backends(container)

        # Register admin widget components
        self._register_admin_components(container)

        logger.info("Lexigram Cache services registered successfully")

    async def _discover_backends(self, container: ContainerRegistrarProtocol) -> None:
        """Scan the ``lexigram.cache.backends`` entry-point group.

        Any entry point that resolves to a
        :class:`~lexigram.di.provider.Provider` subclass is instantiated
        and its :meth:`~lexigram.di.provider.Provider.register` method is
        called, allowing third-party backend packages to self-register.

        Args:
            container: The DI container registrar.
        """
        import importlib.metadata as _meta

        from lexigram.di.provider import Provider as _Provider

        eps = _meta.entry_points(group="lexigram.cache.backends")
        for ep in eps:
            try:
                candidate = ep.load()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "cache_ep_load_failed",
                    entry_point=ep.name,
                    error=str(exc),
                )
                continue
            if not (isinstance(candidate, type) and issubclass(candidate, _Provider)):
                logger.debug(
                    "cache_ep_skipped",
                    entry_point=ep.name,
                    reason="not a Provider subclass",
                )
                continue
            logger.debug(
                "cache_ep_found",
                entry_point=ep.name,
                provider=candidate.__name__,
            )
            try:
                await candidate().register(container)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "cache_ep_register_failed",
                    entry_point=ep.name,
                    provider=candidate.__name__,
                    error=str(exc),
                )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Start the cache provider.

        All real I/O initialization (backend connections, protection setup,
        service wiring) happens here, after the container is frozen.

        Args:
            container: The DI container provided by the framework.
        """
        logger.info("Starting Lexigram Cache provider")

        # NOTE: RedisStateStore registration is intentionally delegated to
        # lexigram-sql's provider to avoid cross-extension imports.  If you need
        # a StateStoreProtocol alongside the cache, ensure lexigram-sql is installed and
        # its DatabaseProvider is registered before the CacheProvider.
        await self._initialize_backends(container)

        # Initialize stampede protection using the default backend
        if self.config and self.config.service.enable_protection and self._backends:
            default_backend_name = next(
                (
                    name
                    for name, cfg in zip(
                        self._backends.keys(),
                        self.config.backends,
                        strict=False,
                    )
                    if cfg.default
                ),
                next(iter(self._backends)),
            )
            default_backend = self._backends.get(default_backend_name)
            if default_backend is not None:
                self._protection = StampedeProtectedCache(
                    default_backend,
                    lock_timeout=self.config.service.protection_lock_ttl,
                    lock_wait_timeout=self.config.service.protection_max_wait,
                )
            else:
                logger.warning("No cache backend available, cache protection disabled")

        # Initialize services (sync) — must run after backends and protection are ready
        self._initialize_services()

        for cache_repository, repository in self._observed_pairs:
            cache_repository.observe(repository)

        from lexigram.cache.admin.contributor import CacheAdminContributor

        try:
            contributor = await container.resolve(CacheAdminContributor)
            await contributor.on_admin_boot(container)
        except Exception:  # noqa: BLE001
            logger.warning("cache_admin_contributor_boot_failed")

        logger.info("Lexigram Cache provider started successfully")

    def observe_repository(self, cache_repository: Any, repository: Any) -> None:
        """Queue cache repository observation wiring for provider boot.

        Args:
            cache_repository: Cache repository that exposes ``observe()``.
            repository: Source repository whose mutations should invalidate cache.
        """
        self._observed_pairs.append((cache_repository, repository))

    async def shutdown(self) -> None:
        """Shutdown the cache provider and cleanup resources."""
        logger.info("Shutting down Lexigram Cache provider")

        # Shutdown services
        for service in self._services.values():
            try:
                # Some services may not provide close(); use getattr
                close_fn = getattr(service, "close", None)
                if close_fn is not None:
                    await close_fn()
            except (RuntimeError, OSError, ValueError, TypeError, AttributeError):
                logger.exception("Error closing cache service")

        # Shutdown backends
        for backend in self._backends.values():
            try:
                close_fn = getattr(backend, "close", None)
                if close_fn is not None:
                    await close_fn()
            except (RuntimeError, OSError, ValueError, TypeError, AttributeError):
                logger.exception("Error closing cache backend")

        # Clear references
        self._services.clear()
        self._backends.clear()
        self._serializers.clear()
        self._protection = None

        logger.info("Lexigram Cache provider shutdown complete")

    @property
    def cache(self) -> CacheService:
        """Get the default cache service."""
        return self.get_default_service()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check provider health."""
        result = await self.get_health_status()
        return HealthCheckResult(
            component=result.component,
            status=result.status,
            message=result.message,
            error=result.error,
            duration_ms=result.duration_ms,
            details=result.details,
            checked_at=result.checked_at,
            category=HealthCheckCategory.READINESS,
        )

    def _initialize_serializers(self) -> None:
        """Initialize available serializers.

        Note:
            Domain-model reconstruction for ``@cacheable`` envelopes is
            gated by ``DEFAULT_REGISTRY``
            (``lexigram.cache.serialization.type_registry``): the
            ``TypeRegistry.with_defaults()`` instance is the single
            registration surface — deny-by-default. The cache package
            defines no model types itself, so nothing is registered here;
            consumers register their domain models at boot via
            ``DEFAULT_REGISTRY.register(ModelClass)``.
        """
        from lexigram.cache.serialization.factory import create_serializers

        self._serializers = create_serializers()
        logger.debug("Initialized serializers: %s", list(self._serializers.keys()))

    async def _initialize_backends(
        self, container: ContainerResolverProtocol | None = None
    ) -> None:
        """Initialize configured cache backends."""
        if not self.config:
            logger.warning("No configuration provided for cache provider")
            return

        for backend_config in self.config.backends:
            if not backend_config.enabled:
                logger.debug("Skipping disabled backend: %s", backend_config.name)
                continue

            try:
                backend = await self._create_backend(backend_config, container)
                self._backends[backend_config.name] = backend
                logger.info(
                    "Initialized backend: %s (%s)",
                    backend_config.name,
                    resolve_backend_type(backend_config),
                )
            except Exception as e:
                logger.exception("Failed to initialize backend %s", backend_config.name)
                if backend_config.default:
                    raise RuntimeError(
                        f"Failed to initialize default backend: {backend_config.name}",
                    ) from e

    async def _create_backend(
        self,
        config: CacheBackendConfig,
        container: ContainerResolverProtocol | None = None,
    ) -> CacheBackendProtocol:
        """Create a backend instance from configuration."""
        from lexigram.cache.backends.factory import create_backend

        hooks = None
        if container is not None:
            resolve_optional = getattr(container, "resolve_optional", None)
            if callable(resolve_optional):
                maybe_hooks = resolve_optional(HookRegistryProtocol)
                hooks = (
                    await maybe_hooks
                    if inspect.isawaitable(maybe_hooks)
                    else maybe_hooks
                )

        return await create_backend(config, container, hooks=hooks)

    def _initialize_services(self) -> None:
        """Initialize cache services for each backend."""
        from lexigram.cache.service.factory import create_service

        if not self.config:
            return

        for backend_name, backend in self._backends.items():
            try:
                service = create_service(self, backend_name, backend, self._protection)
                self._services[backend_name] = service
                logger.info("Initialized cache service for backend: %s", backend_name)
            except (
                RuntimeError,
                OSError,
                ValueError,
                TypeError,
                AttributeError,
                ImportError,
            ):
                logger.exception(
                    "Failed to initialize service for backend %s", backend_name
                )

    def _create_service(
        self,
        backend_name: str,
        backend: CacheBackendProtocol,
    ) -> CacheService:
        """Create a cache service for a backend."""
        if not self.config:
            raise RuntimeError("Provider not configured")

        from lexigram.cache.service.core import CacheService

        return CacheService(provider=self, protection=self._protection)

    def get_service(self, backend_name: str | None = None) -> CacheService:
        """
        Get a cache service by backend name.

        Args:
            backend_name: Name of the backend, uses default if None

        Returns:
            CacheService instance

        Raises:
            ValueError: If backend not found
        """
        if backend_name is None and self.config:
            backend_name = self.config.service.default_backend
            if backend_name is None:
                # Find default backend
                default_config = self.config.get_default_backend()
                if default_config:
                    backend_name = default_config.name

        if backend_name not in self._services:
            available = list(self._services.keys())
            raise ValueError(
                f"Cache service '{backend_name}' not found. Available: {available}",
            )

        return self._services[backend_name]

    def get_backend(self, backend_name: str | None = None) -> Any:
        """
        Get a backend instance by name.

        Args:
            backend_name: Name of the backend, uses default if None

        Returns:
            Backend instance

        Raises:
            ValueError: If backend not found
        """
        if backend_name is None and self.config:
            backend_name = self.config.service.default_backend
            if backend_name is None:
                # Find default backend
                default_config = self.config.get_default_backend()
                if default_config:
                    backend_name = default_config.name

        if backend_name not in self._backends:
            available = list(self._backends.keys())
            raise ValueError(
                f"Backend '{backend_name}' not found. Available: {available}",
            )

        return self._backends[backend_name]

    def get_default_service(self) -> CacheService:
        """
        Get the default cache service.

        Returns:
            Default CacheService instance
        """
        return self.get_service()

    async def get_health_status(self) -> HealthCheckResult:
        """Return comprehensive health status of all cache services and backends.

        Returns:
            Structured :class:`~lexigram.contracts.types.HealthCheckResult`.
        """
        return await _get_health_status(self._services, self._backends)

    async def get_metrics(self) -> dict[str, Any]:
        """Return comprehensive metrics from all registered cache services.

        Returns:
            Metrics dictionary with per-service statistics.
        """
        return await _get_metrics(self._services, self._backends, self._protection)

    def _register_semantic_cache(self, container: ContainerRegistrarProtocol) -> None:
        """Register semantic cache components if faiss is available.

        Conditionally registers SemanticCacheStore and its dependencies
        (VectorIndexProtocol, FaissVectorIndex) only if faiss package
        is installed and EmbeddingClientProtocol is registered. If faiss
        is not available or EmbeddingClientProtocol is missing, logs a
        debug message and skips registration.

        Args:
            container: The DI container registrar.
        """
        if not self._faiss_available():
            logger.debug("semantic_cache_skipped_faiss_not_available")
            return

        # Check if EmbeddingClientProtocol is registered
        try:
            from lexigram.contracts.ai.llm import EmbeddingClientProtocol

            if not container.has(EmbeddingClientProtocol):
                logger.debug(
                    "semantic_cache_skipped_no_embedding_client",
                    required_type="EmbeddingClientProtocol",
                )
                return
        except ImportError as exc:
            logger.warning(
                "semantic_cache_registration_failed_import",
                error=str(exc),
            )
            return

        try:
            from lexigram.cache.semantic.cost_decision import CostAwareCacheDecision
            from lexigram.cache.semantic.protocols import VectorIndexProtocol
            from lexigram.cache.semantic.store import SemanticCacheStore
            from lexigram.cache.semantic.vector_index import FaissVectorIndex
            from lexigram.contracts.ai.llm import SemanticCacheProtocol

            # Register vector index (internal protocol, package-local)
            container.singleton(VectorIndexProtocol, FaissVectorIndex)

            # Register cost decision helper
            container.singleton(CostAwareCacheDecision, CostAwareCacheDecision)

            # Register semantic cache store as singleton
            # Constructor injection will wire up the dependencies:
            # - CacheBackendProtocol (already registered above)
            # - EmbeddingClientProtocol (verified available above)
            # - VectorIndexProtocol (registered above)
            container.singleton(SemanticCacheProtocol, SemanticCacheStore)

            logger.debug("semantic_cache_registered")
        except ImportError as exc:
            logger.warning(
                "semantic_cache_registration_failed_import",
                error=str(exc),
            )

    @staticmethod
    def _faiss_available() -> bool:
        """Check if faiss package is installed.

        Returns:
            True if faiss can be imported, False otherwise.
        """
        try:
            import faiss  # type: ignore[import-not-found]  # noqa: F401

            return True
        except ImportError:
            return False

    def _register_admin_components(self, container: ContainerRegistrarProtocol) -> None:
        """Register admin contributor.

        Args:
            container: The DI container registrar.
        """
        from lexigram.cache.admin.contributor import CacheAdminContributor

        container.singleton(CacheAdminContributor, CacheAdminContributor)

        logger.debug("Registered cache admin widget components")


__all__ = ["CacheProvider"]


def __getattr__(name: str) -> Any:
    """Lazy-load heavy symbols that are only needed at runtime."""
    if name == "CacheService":
        from lexigram.cache.service.core import CacheService

        return CacheService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
