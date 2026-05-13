"""DI provider for lexigram-vector."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.data.vector.protocols import VectorStoreProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.vector.config import VectorConfig
from lexigram.vector.constants import (
    BACKEND_MEMORY,
    BACKEND_PGVECTOR,
    BACKEND_PINECONE,
    BACKEND_QDRANT,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.container import (  # type: ignore[import-untyped]
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class VectorProvider(Provider):
    """Register vector store services into the DI container.

    Selects the backend based on ``VectorConfig.backend`` and registers
    the appropriate ``VectorStoreProtocol`` implementation.

    Supports single-backend and multi-backend (``VectorConfig.backends``)
    modes.  In multi-backend mode each entry is registered under its name
    via ``container.singleton(..., name=entry.name)``.  The primary backend
    (``primary=True`` or the first entry) also receives the unnamed
    binding for backward compatibility.
    """

    name = "vector"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "vector"
    config_model: type | None = VectorConfig

    def __init__(self, config: VectorConfig | None = None) -> None:
        """Initialize with optional config."""
        super().__init__()
        self._requested_config = config
        self._config = config or VectorConfig()
        self._store: VectorStoreProtocol | None = None
        # Multi-backend: (name, store) pairs; populated by _register_multi_backend
        # and potentially updated during boot() for pgvector entries.
        self._store_services: list[tuple[str, Any]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_store(self) -> VectorStoreProtocol:
        """Return the single-backend store, raising if boot() has not run yet."""
        if self._store is None:
            raise RuntimeError(
                "VectorStoreProtocol resolved before VectorProvider.boot() completed. "
                "Ensure the application fully boots before resolving vector services."
            )
        return self._store

    def _create_store(self, config: VectorConfig) -> Any:
        """Instantiate (but do not connect) the store for *config*.

        Returns ``None`` for the pgvector backend because
        :class:`~lexigram.vector.backends.pgvector.PgVectorStore` requires a
        ``DatabaseProviderProtocol`` that can only be resolved from the DI
        container during :meth:`boot`.  All other backends are created eagerly
        at registration time.
        """
        backend = config.backend
        if backend == BACKEND_MEMORY:
            from lexigram.vector.backends.memory import MemoryVectorStore

            return MemoryVectorStore(config=config.memory)
        if backend == BACKEND_PINECONE:
            from lexigram.vector.backends.pinecone import PineconeStore

            return PineconeStore(config=config.pinecone)
        if backend == BACKEND_QDRANT:
            from lexigram.vector.backends.qdrant import QdrantStore

            return QdrantStore(config=config.qdrant)
        if backend == BACKEND_PGVECTOR:
            # Cannot instantiate without a DB provider — sentinel, resolved in boot().
            return None
        msg = f"Unknown vector backend: {backend}"
        raise ValueError(msg)

    async def _maybe_wrap_with_tenancy(
        self,
        store: VectorStoreProtocol,
        container: ContainerResolverProtocol,
    ) -> VectorStoreProtocol:
        """Wrap *store* with ``TenantVectorStoreDecorator`` when tenancy is enabled."""
        if not self._config.tenancy.enabled:
            return store

        from lexigram.primitives.context import Context
        from lexigram.vector.tenancy.decorator import TenantVectorStoreDecorator
        from lexigram.vector.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )

        ctx = await container.resolve(Context)
        kind = self._config.tenancy.resolver_kind
        if kind == "pinecone_namespace":
            from lexigram.vector.tenancy.pinecone_namespace import (
                PineconeNamespaceTenantResolver,
            )

            resolver: Any = PineconeNamespaceTenantResolver()
        else:
            resolver = TemplatedTenantCollectionResolver()

        return TenantVectorStoreDecorator(inner=store, resolver=resolver, ctx=ctx)

    def _make_named_store_factory(self, name: str) -> Any:
        """Return a factory closure that reads the named store from ``_store_services``.

        The closure defers resolution until the singleton is actually requested,
        which means pgvector stores (created in boot()) are safely accessible
        after the provider has fully booted.
        """

        def _factory() -> VectorStoreProtocol:
            for n, s in self._store_services:
                if n == name:
                    if s is None:
                        raise RuntimeError(
                            f"Vector store '{name}' is not yet initialized. "
                            "Ensure VectorProvider.boot() has completed before "
                            "resolving named vector stores."
                        )
                    return s
            raise RuntimeError(f"Named vector store '{name}' not found in provider.")

        return _factory

    # ------------------------------------------------------------------
    # Provider lifecycle
    # ------------------------------------------------------------------

    async def register(
        self,
        container: ContainerRegistrarProtocol,
    ) -> None:
        """Register the vector store config and (lazy) singleton bindings."""
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), VectorConfig)
            else self._config
        )
        container.singleton(VectorConfig, self._config)

        if not self._config.enabled:
            logger.info("vector_disabled", reason="VectorConfig.enabled=False")
            return

        # Unnamed binding — will be overwritten by the primary in multi-backend mode.
        container.singleton(VectorStoreProtocol, factory=self._get_store)

        if self._config and self._config.backends:
            self._register_multi_backend(container)
        else:
            logger.info("vector_provider_registered", backend=self._config.backend)

    def _register_multi_backend(
        self,
        container: ContainerRegistrarProtocol,
    ) -> None:
        """Register multiple named vector backends.

        Each backend receives a named DI binding resolvable via
        ``Annotated[VectorStoreProtocol, Named(entry.name)]`` (or
        ``container.resolve(..., name=entry.name)``).  The primary backend
        (``primary=True`` or the first entry by identity) also receives the
        unnamed ``VectorStoreProtocol`` binding for backward compatibility.
        """
        for entry in self._config.backends:
            synthetic_config = VectorConfig.from_named(entry, base=self._config)
            store = self._create_store(synthetic_config)  # None for pgvector
            self._store_services.append((entry.name, store))

            # Use direct reference capture for non-pgvector stores (canonical pattern).
            # pgvector stores are None here and filled in during boot(), so they need
            # the deferred closure that searches _store_services at resolution time.
            factory = (
                self._make_named_store_factory(entry.name)
                if store is None
                else lambda s=store: s
            )

            # Named binding — resolvable via Annotated[VectorStoreProtocol, Named(name)]
            container.singleton(VectorStoreProtocol, factory=factory, name=entry.name)

            # Unnamed binding for the primary backend (backward compat)
            if entry.primary or self._config.backends[0] is entry:
                container.singleton(VectorStoreProtocol, factory=factory)

        logger.info(
            "vector_provider_registered",
            backend="multi",
            count=len(self._config.backends),
        )

    async def boot(
        self,
        container: ContainerResolverProtocol,
    ) -> None:
        """Connect to the vector store(s).

        Multi-backend mode:
            All stores are connected in parallel via ``asyncio.gather``.
            pgvector entries whose store could not be created at register time
            are instantiated here using the fully-resolved DI container.
            On partial failure the successfully-connected stores are
            disconnected before re-raising the first error.

        Single-backend mode:
            Preserves the original sequential boot behaviour.
        """
        if not self._config.enabled:
            return

        if self._store_services:
            await self._boot_multi_backend(container)
            return

        # ---- single-backend path (original behaviour) ----
        backend = self._config.backend

        if backend == BACKEND_PGVECTOR:
            from typing import Annotated

            from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
            from lexigram.di.markers import Named
            from lexigram.vector.backends.pgvector import PgVectorStore

            db_name = self._config.pgvector.database
            db = await container.resolve(
                Annotated[DatabaseProviderProtocol, Named(db_name)]
            )
            self._store = PgVectorStore(provider=db, config=self._config.pgvector)
        else:
            self._store = self._create_store(self._config)

        await self._store.connect()
        self._store = await self._maybe_wrap_with_tenancy(self._store, container)
        container.bind(VectorStoreProtocol, self._store)
        logger.info("vector_store_connected", backend=backend)

    async def _boot_multi_backend(
        self,
        container: ContainerResolverProtocol,
    ) -> None:
        """Resolve pgvector placeholders and connect all stores in parallel."""
        # Fill in pgvector entries that returned None from _create_store.
        for i, (name, store) in enumerate(self._store_services):
            if store is not None:
                continue

            # Locate the original NamedVectorConfig entry by name.
            entry = next(e for e in self._config.backends if e.name == name)
            synthetic_config = VectorConfig.from_named(entry, base=self._config)

            from typing import Annotated

            from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
            from lexigram.di.markers import Named
            from lexigram.vector.backends.pgvector import PgVectorStore

            db_name = synthetic_config.pgvector.database
            db = await container.resolve(
                Annotated[DatabaseProviderProtocol, Named(db_name)]
            )
            pgvector_store = PgVectorStore(
                provider=db, config=synthetic_config.pgvector
            )
            self._store_services[i] = (name, pgvector_store)

        # Connect all stores in parallel; handle partial failures gracefully.
        results = await asyncio.gather(
            *(svc.connect() for _, svc in self._store_services),
            return_exceptions=True,
        )
        errors = [r for r in results if isinstance(r, BaseException)]
        if errors:
            # Disconnect already-connected stores before propagating the error.
            for (_, svc), result in zip(self._store_services, results, strict=False):
                if not isinstance(result, BaseException):
                    try:
                        await svc.disconnect()
                    except Exception as e:  # noqa: BLE001 — best-effort cleanup; all stores must attempt disconnect
                        logger.warning(
                            "vector_store_disconnect_failed_on_cleanup", error=str(e)
                        )
            raise errors[0]

        # Wrap each store with tenancy if enabled, then re-bind in container.
        for i, (name, svc) in enumerate(self._store_services):
            wrapped = await self._maybe_wrap_with_tenancy(svc, container)
            self._store_services[i] = (name, wrapped)

        logger.info("vector_stores_connected", count=len(self._store_services))

    async def shutdown(self) -> None:
        """Disconnect from all vector store(s).

        Multi-backend mode: stores are disconnected in LIFO order; errors
        are suppressed so all stores get a chance to clean up.

        Single-backend mode: original behaviour is preserved.
        """
        if self._store_services:
            for _, svc in reversed(self._store_services):
                try:
                    await svc.disconnect()
                except Exception as e:  # noqa: BLE001 — best-effort shutdown; all stores must attempt disconnect
                    logger.warning("vector_store_disconnect_failed", error=str(e))
            logger.info("vector_stores_disconnected", count=len(self._store_services))
            return

        if self._store is not None:
            await self._store.disconnect()
            logger.info("vector_store_disconnected")
            self._store = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check provider health across all registered backends.

        Multi-backend mode: health checks run in parallel; the overall
        status is the worst individual status
        (UNHEALTHY > DEGRADED > HEALTHY).

        Single-backend mode: original behaviour is preserved.

        Args:
            timeout: Maximum seconds to wait for each health check response.

        Returns:
            :class:`~lexigram.contracts.core.HealthCheckResult` with status
            and per-backend component details.
        """
        start = time.perf_counter()

        if not self._config.enabled:
            return HealthCheckResult(
                component="vector",
                status=HealthStatus.DEGRADED,
                message="vector not enabled",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        if self._store_services:
            results = await asyncio.gather(
                *(svc.health_check(timeout=timeout) for _, svc in self._store_services),
                return_exceptions=True,
            )
            statuses: list[HealthStatus] = []
            details: dict[str, str] = {}
            for (name, _), result in zip(self._store_services, results, strict=False):
                if isinstance(result, Exception):
                    statuses.append(HealthStatus.UNHEALTHY)
                    details[f"vector:{name}"] = str(result)
                else:
                    statuses.append(result.status)  # type: ignore[union-attr]
                    details[f"vector:{name}"] = result.status.value  # type: ignore[union-attr]

            overall = (
                HealthStatus.UNHEALTHY
                if HealthStatus.UNHEALTHY in statuses
                else HealthStatus.DEGRADED
                if HealthStatus.DEGRADED in statuses
                else HealthStatus.HEALTHY
            )
            return HealthCheckResult(
                component="vector",
                status=overall,
                details=details,
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        # ---- single-backend path ----
        if self._store is None:
            return HealthCheckResult(
                component="vector",
                status=HealthStatus.DEGRADED,
                message="vector store not initialized",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        try:
            store_result = await self._store.health_check(timeout=timeout)
            return HealthCheckResult(
                component="vector",
                status=store_result.status,
                details=store_result.details,
                error=store_result.error,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        except (ConnectionError, TimeoutError, RuntimeError) as exc:
            return HealthCheckResult(
                component="vector",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
                duration_ms=(time.perf_counter() - start) * 1000,
            )


__all__ = ["VectorProvider"]
