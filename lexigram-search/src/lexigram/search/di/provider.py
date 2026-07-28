"""Search Provider."""

from __future__ import annotations

import asyncio
import time
from typing import Any, cast

from lexigram.contracts import ContainerRegistrarProtocol, ContainerResolverProtocol
from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.search.config import BackendType, SearchConfig
from lexigram.search.engine import SearchEngine

logger = get_logger(__name__)


class SearchProvider(Provider):
    """Provider for search functionality.

    Supports two registration modes:

    **Single-backend** (default, existing behaviour):
        ``SearchConfig.backends`` is empty. Registers ``SearchProvider`` and
        ``SearchEngine`` as unnamed singletons, exactly as before.

    **Multi-backend** (Named DI):
        ``SearchConfig.backends`` is non-empty. Each entry is registered as
        ``Annotated[SearchEngineProtocol, Named(entry.name)]``. The primary
        backend (``primary=True`` or the first entry) also receives the unnamed
        ``SearchEngineProtocol`` binding for backward compatibility.
        Database-backed backends (POSTGRES / MYSQL) use a ``NullBackend``
        placeholder during ``register()`` and are resolved from the container
        in ``boot()``.
    """

    name = "search"
    priority = ProviderPriority.DOMAIN

    config_key: str | None = "search"
    config_model: type | None = SearchConfig

    def __init__(self, backend: SearchEngine, config: SearchConfig | None = None):
        """Initialize the provider with a configured backend."""
        super().__init__()
        self.backend = backend
        self._config: SearchConfig | None = config
        # Tracks whether boot() must resolve a database-backed backend from the
        # container.  Set by configure() for POSTGRES / MYSQL backend types.
        self._uses_db_backend: bool = False
        # Original backend type before orchestrator may overwrite _config.
        # Set by configure() alongside _uses_db_backend.
        self._db_backend_type: BackendType | None = None
        # Multi-backend: (name, backend_instance) — populated by _register_multi_backend.
        self._search_services: list[tuple[str, Any]] = []
        # DB-backed multi-backends pending resolution at boot time: (name, sub_provider).
        # sub_provider.backend starts as NullBackend and is replaced in boot().
        self._db_pending: list[tuple[str, SearchProvider]] = []

    @classmethod
    def from_config(cls, config: SearchConfig, **context: Any) -> SearchProvider:
        """Create a SearchProvider from config.

        Delegates to the existing configure() classmethod for backend selection.
        """
        provider = cls.configure(config)
        provider._config = config
        return provider

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register search services with the container."""
        if self._config is not None and not self._config.enabled:
            logger.info("search_disabled", reason="SearchConfig.enabled=False")
            return
        if self._config is not None and self._config.backends:
            await self._register_multi_backend(container)
        else:
            await self._register_single_backend(container)

    async def _register_single_backend(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register a single (unnamed) backend — identical to the original register() logic."""
        container.singleton(SearchProvider, lambda: self)
        container.singleton(SearchEngine, lambda: self.backend)

    async def _register_multi_backend(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register multiple named search backends.

        Each entry receives an ``Annotated[SearchEngineProtocol, Named(entry.name)]``
        binding. The primary entry (``primary=True`` or the first via identity check)
        also receives the unnamed ``SearchEngineProtocol`` binding.

        DB-backed backends (POSTGRES / MYSQL) are registered with a ``NullBackend``
        placeholder and resolved for real during ``boot()``.
        """
        from lexigram.contracts.search import SearchEngineProtocol

        for entry in self._config.backends:  # type: ignore[union-attr]
            backend_config = SearchConfig.from_named(entry)
            sub_provider = SearchProvider.configure(backend_config)

            if sub_provider._uses_db_backend:
                # Placeholder — replaced by the real backend in boot().
                self._db_pending.append((entry.name, sub_provider))

            # Track for health_check / shutdown (initially the placeholder for DB-backed).
            self._search_services.append((entry.name, sub_provider.backend))

            # Named singleton — lambda reads sub_provider.backend so that boot()
            # can replace it before the factory is first invoked.
            container.singleton(
                SearchEngineProtocol,
                factory=lambda sp=sub_provider: sp.backend,
                name=entry.name,
            )

            # Primary (flag or first entry via identity) also gets the unnamed binding.
            if entry.primary or self._config.backends[0] is entry:  # type: ignore[union-attr]
                container.singleton(
                    SearchEngineProtocol,
                    factory=lambda sp=sub_provider: sp.backend,
                )

        logger.info(
            "search_registered",
            mode="multi",
            count=len(self._config.backends),  # type: ignore[union-attr]
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Initialize the search backend(s) and verify connectivity.

        In multi-backend mode all backends are health-checked in parallel via
        ``asyncio.gather``. DB-backed backends are resolved from the container
        first, replacing the ``NullBackend`` placeholder registered during
        ``register()``.

        In single-backend mode the existing sequential boot logic is preserved.

        Raises:
            RuntimeError: If any backend is unreachable at startup.
        """
        if self._config is not None and not self._config.enabled:
            return

        if not self._search_services:
            # Single-backend path (original behaviour).
            await self._boot_single(container)
            return

        # Multi-backend: resolve DB-backed placeholders first.
        for entry_name, sub_provider in self._db_pending:
            from lexigram.contracts.data import DatabaseProviderProtocol

            entry = next(
                e
                for e in self._config.backends  # type: ignore[union-attr]
                if e.name == entry_name
            )
            if entry.database:
                db_provider = await container.resolve(
                    DatabaseProviderProtocol,
                    name=entry.database,  # type: ignore[call-overload]
                )
            else:
                db_provider = await container.resolve(DatabaseProviderProtocol)

            backend_type = sub_provider._db_backend_type or (
                sub_provider._config.backend_type
                if sub_provider._config
                else None
            )

            if backend_type == BackendType.POSTGRES:
                from lexigram.search.backends.postgres.backend import (
                    PostgresDatabaseSearchBackend,
                )

                db_backend = cast("SearchEngine", PostgresDatabaseSearchBackend(provider=db_provider))
            elif backend_type == BackendType.MYSQL:
                from lexigram.search.backends.mysql import MySQLDatabaseSearchBackend

                db_backend = cast("SearchEngine", MySQLDatabaseSearchBackend(provider=db_provider))
            else:
                raise RuntimeError(
                    f"Unsupported DB-backed search backend: {backend_type}"
                )

            # Replace the NullBackend placeholder on the sub-provider so the
            # container's factory lambda returns the real backend.
            sub_provider.backend = db_backend

            # Keep _search_services in sync.
            for idx, (svc_name, _) in enumerate(self._search_services):
                if svc_name == entry_name:
                    self._search_services[idx] = (svc_name, db_backend)
                    break

        # Parallel health-check of all backends with cleanup on partial failure.
        results = await asyncio.gather(
            *(
                self._boot_check_one(backend, name)
                for name, backend in self._search_services
            ),
            return_exceptions=True,
        )
        errors = [r for r in results if isinstance(r, BaseException)]
        if errors:
            for _, backend in reversed(self._search_services):
                if hasattr(backend, "close"):
                    try:
                        await backend.close()
                    except (OSError, RuntimeError, ValueError):
                        pass
            raise errors[0]

    async def _boot_check_one(self, backend: Any, name: str) -> None:
        """Health-check a single backend instance during boot."""
        logger.info(
            "search_backend_starting",
            name=name,
            backend=backend.__class__.__name__,
        )
        result = await backend.health_check()
        if result.status.value == "unhealthy":
            raise RuntimeError(
                f"Search backend [{name}] {backend.__class__.__name__} is unhealthy at startup: "
                f"{result.error or 'no details'}"
            )
        logger.info(
            "search_backend_ready",
            name=name,
            backend=backend.__class__.__name__,
        )

    async def _boot_single(self, container: ContainerResolverProtocol) -> None:
        """Single-backend boot — original logic, preserved exactly."""
        if self._uses_db_backend:
            from lexigram.contracts.data import DatabaseProviderProtocol

            db_provider = await container.resolve(DatabaseProviderProtocol)

            backend_type = self._db_backend_type or (
                self._config.backend_type if self._config else None
            )

            if backend_type == BackendType.POSTGRES:
                from lexigram.search.backends.postgres.backend import (
                    PostgresDatabaseSearchBackend,
                )

                db_backend = cast("SearchEngine", PostgresDatabaseSearchBackend(provider=db_provider))
            elif backend_type == BackendType.MYSQL:
                from lexigram.search.backends.mysql import MySQLDatabaseSearchBackend

                db_backend = cast("SearchEngine", MySQLDatabaseSearchBackend(provider=db_provider))
            else:
                raise RuntimeError(
                    f"Unsupported DB-backed search backend: "
                    f"{backend_type}"
                )

            self.backend = db_backend

        logger.info("search_backend_starting", backend=self.backend.__class__.__name__)

        result = await self.backend.health_check()
        if result.status.value == "unhealthy":
            raise RuntimeError(
                f"Search backend {self.backend.__class__.__name__} is unhealthy at startup: "
                f"{result.error or 'no details'}"
            )

        logger.info(
            "search_backend_ready",
            backend=self.backend.__class__.__name__,
        )

    async def shutdown(self) -> None:
        """Clean up search connections.

        In multi-backend mode backends are closed in LIFO order (reversed
        registration order) so later-registered backends are torn down first.
        """
        if self._search_services:
            for _, backend in reversed(self._search_services):
                if hasattr(backend, "close"):
                    try:
                        await backend.close()
                    except (OSError, RuntimeError, ValueError) as exc:
                        logger.warning("search_shutdown_error", error=str(exc))

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check health of search backend(s).

        In multi-backend mode the overall status is the worst individual status
        (UNHEALTHY > DEGRADED > HEALTHY).
        """
        start_time = time.time()

        if self._search_services:
            results = await asyncio.gather(
                *(
                    backend.health_check(timeout=timeout)
                    for _, backend in self._search_services
                ),
                return_exceptions=True,
            )
            worst = HealthStatus.HEALTHY
            details: dict[str, str] = {}
            for (svc_name, _), r in zip(self._search_services, results, strict=False):
                if isinstance(r, BaseException):
                    worst = HealthStatus.UNHEALTHY
                    details[f"search:{svc_name}"] = str(r)
                elif r.status == HealthStatus.UNHEALTHY:
                    worst = HealthStatus.UNHEALTHY
                    details[f"search:{svc_name}"] = r.status.value
                elif (
                    r.status == HealthStatus.DEGRADED
                    and worst != HealthStatus.UNHEALTHY
                ):
                    worst = HealthStatus.DEGRADED
                    details[f"search:{svc_name}"] = r.status.value
                else:
                    details[f"search:{svc_name}"] = r.status.value
            return HealthCheckResult(
                component="search",
                status=worst,
                details=details,
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Single-backend path (original logic).
        try:
            res = await self.backend.health_check()
            latency_ms = (time.time() - start_time) * 1000
            if isinstance(res, HealthCheckResult):
                if res.duration_ms == 0.0:
                    return HealthCheckResult(
                        component=res.component,
                        status=res.status,
                        message=res.message,
                        error=res.error,
                        duration_ms=latency_ms,
                        details=res.details,
                        checked_at=res.checked_at,
                    )
                return res
            return HealthCheckResult(
                component="search",
                status=HealthStatus.HEALTHY
                if res.get("status") == "healthy"
                else HealthStatus.UNHEALTHY,
                details=res,
                duration_ms=latency_ms,
            )
        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="search",
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                details={"backend": self.backend.__class__.__name__},
                duration_ms=latency_ms,
            )

    @classmethod
    def configure(cls, config: SearchConfig) -> SearchProvider:
        """
        Create a SearchProvider configured from a SearchConfig object.
        """
        config.validate_for_backend()

        backend: Any

        if config.backend_type == BackendType.MEILISEARCH:
            from lexigram.search.backends.meilisearch import MeiliSearchBackend

            backend = MeiliSearchBackend(
                url=config.meilisearch.url,
                api_key=str(config.meilisearch.api_key)
                if config.meilisearch.api_key
                else None,
            )
            return cls(backend=backend)

        if config.backend_type == BackendType.MEMORY:
            from lexigram.search.backends.null import NullBackend

            backend = NullBackend()
            return cls(backend=backend)

        if config.backend_type == BackendType.SQLITE:
            from lexigram.search.backends.sqlite import SQLiteSearchBackend

            backend = SQLiteSearchBackend(config.sqlite)
            return cls(backend=backend)

        if config.backend_type in (BackendType.POSTGRES, BackendType.MYSQL):
            # Database-backed search backends live in lexigram-sql, not here.
            # A NullBackend is used as a placeholder; boot() will replace it
            # with the real backend resolved from the container (registered by
            # DatabaseProvider).
            from lexigram.search.backends.null import NullBackend

            provider = cls(backend=NullBackend())
            provider._uses_db_backend = True
            provider._db_backend_type = config.backend_type
            return provider

        # Should be unreachable if config matches BackendType enum
        raise ValueError(f"Unsupported backend type: {config.backend_type}")

    # Helper methods for manual setup

    @classmethod
    def with_meilisearch(
        cls,
        url: str = "http://localhost:7700",
        api_key: str | None = None,
    ) -> SearchProvider:
        """Create provider with MeiliSearch backend."""
        from lexigram.search.backends.meilisearch import MeiliSearchBackend

        backend = MeiliSearchBackend(url=url, api_key=api_key)
        return cls(backend=backend)  # type: ignore[arg-type]

    @classmethod
    def with_memory(cls) -> SearchProvider:
        """Create provider with in-memory (null) backend."""
        from lexigram.search.backends.null import NullBackend

        return cls(backend=NullBackend())


__all__ = ["SearchProvider"]
