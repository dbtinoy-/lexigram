"""DI provider that registers database services into the container.

This is the single canonical entry point for registering all database
services into the DI container.  ``DatabaseService`` is a plain facade
(not a DI ``Provider`` subclass), and ``DatabaseDriver`` is a raw
driver abstraction — neither of them should interact with the container
directly.
"""

from __future__ import annotations

import inspect
import time
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import (
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.core.hooks import HookRegistryProtocol
from lexigram.contracts.exceptions import UnresolvableDependencyError
from lexigram.contracts.exceptions.infra import NoPrimaryBackendError
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import get_logger
from lexigram.primitives.context import Context
from lexigram.sql.config import DatabaseConfig
from lexigram.sql.providers.database_service import DatabaseService

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class DatabaseProvider(Provider):
    """DI provider that registers database services into the container.

    Single registration path for all database-related singletons and
    scoped services: DatabaseService, protocol bindings, connection pool,
    query logger, migration manager, audit logger, unit-of-work, and
    optional metrics/tracer.

    Manages lifecycle: connect on boot, disconnect on shutdown.
    Multi-backend support: when ``config.backends`` is non-empty, each backend
    is registered under its name via ``container.singleton(name=entry.name)``.
    The primary backend (``primary=True`` or first entry) also receives the
    unnamed bindings for backward compatibility.
    """

    name = "database"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "sql"
    config_model: type | None = DatabaseConfig

    def __init__(
        self,
        config: DatabaseConfig | str | None = None,
        migration_dir: str = "migrations",
        enable_migrations: bool = False,
    ) -> None:
        super().__init__()
        if isinstance(config, str):
            config = DatabaseConfig.from_url(config)
        self._explicit_config: DatabaseConfig | None = config
        self._migration_dir = migration_dir
        self._enable_migrations = enable_migrations
        self._db_provider: Any = None
        # Multi-backend: list of (name, db_service)
        self._db_services: list[tuple[str, Any]] = []
        self._clock: Any = None
        self._id_generator: Any = None
        self._tracer: Any = None
        self._metrics: Any = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register all database services (singletons/scoped) into the container."""
        # Resolve effective config: explicit arg → auto-injected → sqlite default
        effective_config: DatabaseConfig
        if self._explicit_config is not None:
            effective_config = self._explicit_config
        elif isinstance(getattr(self, "config", None), DatabaseConfig):
            effective_config = self.config
        else:
            effective_config = DatabaseConfig()

        # Store as instance attr so remaining methods can reference self._config
        self._config = effective_config

        # Resolve optional dependencies
        id_generator: Any = None
        tracer: Any = None
        metrics: Any = None

        resolve_optional = getattr(container, "resolve_optional", None)
        if callable(resolve_optional):
            from lexigram.contracts.core.identity import IdGeneratorProtocol
            from lexigram.contracts.observability.metrics import (
                MetricsCollectorProtocol,
            )
            from lexigram.contracts.observability.tracing import TracerProtocol

            try:
                maybe_id_gen = resolve_optional(IdGeneratorProtocol)
                maybe_id_gen = (
                    await maybe_id_gen
                    if inspect.isawaitable(maybe_id_gen)
                    else maybe_id_gen
                )
                if maybe_id_gen is not None:
                    id_generator = maybe_id_gen
            except Exception:
                pass

            try:
                maybe_tracer = resolve_optional(TracerProtocol)
                maybe_tracer = (
                    await maybe_tracer
                    if inspect.isawaitable(maybe_tracer)
                    else maybe_tracer
                )
                if maybe_tracer is not None:
                    tracer = maybe_tracer
            except Exception:
                pass

            try:
                maybe_metrics = resolve_optional(MetricsCollectorProtocol)
                maybe_metrics = (
                    await maybe_metrics
                    if inspect.isawaitable(maybe_metrics)
                    else maybe_metrics
                )
                if maybe_metrics is not None:
                    metrics = maybe_metrics
            except Exception:
                pass

        self._clock = None  # Now using ambient clock
        self._id_generator = id_generator
        self._tracer = tracer
        self._metrics = metrics

        # Register data-layer config and query compiler
        from lexigram.sql.config import DataConfig
        from lexigram.sql.query.compiler import PredicateCompiler

        container.singleton(DataConfig, instance=DataConfig())
        container.singleton(PredicateCompiler, instance=PredicateCompiler())

        if effective_config.backends:
            await self._register_multi_backend(container, effective_config)
        else:
            await self._register_single_backend(container, effective_config)

        # Register admin widget services
        self._register_admin_widgets(container)

    async def _register_single_backend(
        self,
        container: ContainerRegistrarProtocol,
        config: DatabaseConfig,
    ) -> None:
        """Register a single database backend (existing behavior, preserved exactly)."""
        from lexigram.contracts import (
            ConnectionPoolProtocol,
            DatabaseProviderProtocol,
            MigrationManagerProtocol,
            QueryLoggerProtocol,
            UnitOfWorkProtocol,
        )

        self._db_provider = self._db_provider or DatabaseService(
            config, clock=self._clock, id_generator=self._id_generator
        )
        container.singleton(DatabaseService, self._db_provider)
        container.singleton(DatabaseProviderProtocol, self._db_provider)

        # Protocol bindings for optional collaborators
        container.singleton(
            ConnectionPoolProtocol,
            lambda: self._db_provider.connection_pool,
        )
        container.singleton(
            QueryLoggerProtocol,
            lambda: self._db_provider.query_logger,
        )

        if self._db_provider.migration_manager:
            container.singleton(
                MigrationManagerProtocol,
                lambda: self._db_provider.migration_manager,
            )

        # High-level MigrationRunnerProtocol — used by the CLI and other consumers
        # that want to run/rollback migrations without importing lexigram-sql internals.
        from lexigram.contracts.data.sql.migrations import MigrationRunnerProtocol
        from lexigram.sql.migrations.runner import MigrationRunnerAdapter

        _migration_runner_factory = lambda: MigrationRunnerAdapter(  # noqa: E731
            self._db_provider.migration_manager
        )
        container.singleton(MigrationRunnerProtocol, _migration_runner_factory)

        # Scoped unit-of-work
        container.scoped(UnitOfWorkProtocol, self._db_provider.get_unit_of_work)  # type: ignore[type-abstract]

        self._register_shared_stores(container, self._db_provider)

        # Register migration manager if alembic is available
        try:
            from lexigram.sql.migrations.api import AlembicManager

            # Unwrap SecretStr only at the driver call site — never store plain URL
            raw_url = config.backend.url if hasattr(config, "backend") else config.url  # type: ignore[attr-defined]
            migration_url = (
                raw_url.get_secret_value()
                if hasattr(raw_url, "get_secret_value")
                else str(raw_url)
            )
            migration_manager = AlembicManager(migration_url, self._migration_dir)
            container.singleton(AlembicManager, migration_manager)
            if self._enable_migrations:
                self._db_provider.migration_manager = migration_manager
        except ImportError:
            pass

        # Database-backed search backends have moved to lexigram-search
        # (`lexigram.search.backends.mysql` / `lexigram.search.backends.postgres`).
        # SearchProvider is responsible for
        # resolving DatabaseProviderProtocol from the container and registering
        # the appropriate DatabaseSearchBackendProtocol singleton.  DatabaseProvider
        # no longer imports from lexigram.sql.search to keep the package boundary clean.

    async def _register_multi_backend(
        self,
        container: ContainerRegistrarProtocol,
        config: DatabaseConfig,
    ) -> None:
        """Register multiple named database backends.

        Each backend in ``config.backends`` is registered under its name via
        ``container.singleton(name=entry.name)``, resolvable through
        ``Annotated[DatabaseProviderProtocol, Named(name)]``.  The primary
        backend (``primary=True`` or the first entry) also receives unnamed
        bindings for backward compatibility.
        """
        from lexigram.contracts import (
            ConnectionPoolProtocol,
            DatabaseProviderProtocol,
            QueryLoggerProtocol,
            UnitOfWorkProtocol,
        )

        backends = config.backends
        primary_entry = next((b for b in backends if b.primary), backends[0])

        self._db_services = []
        primary_svc: Any = None

        for entry in backends:
            db_cfg = DatabaseConfig.from_named(entry, base=config)
            db_svc = DatabaseService(
                db_cfg, clock=self._clock, id_generator=self._id_generator
            )
            # Track backend service for parallel boot/shutdown/health coordination
            self._db_services.append((entry.name, db_svc))

            # Named registration — resolvable via Annotated[T, Named(entry.name)]
            container.singleton(
                DatabaseProviderProtocol,
                name=entry.name,
                instance=db_svc,
            )
            container.singleton(
                DatabaseService,
                name=entry.name,
                instance=db_svc,
            )

            # Named protocol bindings — each backend resolves via Annotated[T, Named(entry.name)]
            _svc = db_svc  # capture per-iteration for closure correctness
            container.scoped(
                UnitOfWorkProtocol,  # type: ignore[type-abstract]
                _svc.get_unit_of_work,
                name=f"{entry.name}:uow",
            )
            container.singleton(
                ConnectionPoolProtocol,
                lambda svc=_svc: svc.connection_pool,
                name=f"{entry.name}:pool",
            )
            container.singleton(
                QueryLoggerProtocol,
                lambda svc=_svc: svc.query_logger,
                name=f"{entry.name}:logger",
            )

            # Register named migration runner for backends that declare a migration_dir
            if entry.migration_dir:
                self._register_migration_runner(
                    container, db_svc, entry.migration_dir, name=entry.name
                )

            if entry.name == primary_entry.name:
                primary_svc = db_svc

        # Primary backend also gets the unnamed bindings (backward compat)
        self._db_provider = primary_svc
        container.singleton(DatabaseProviderProtocol, instance=primary_svc)
        container.singleton(DatabaseService, instance=primary_svc)

        container.scoped(UnitOfWorkProtocol, primary_svc.get_unit_of_work)  # type: ignore[type-abstract]

        container.singleton(
            ConnectionPoolProtocol,
            lambda: self._db_provider.connection_pool,
        )
        container.singleton(
            QueryLoggerProtocol,
            lambda: self._db_provider.query_logger,
        )

        # Shared stores (audit, state, secrets, locks) — always use primary
        self._register_shared_stores(container, primary_svc)

        # Unnamed migration runner for primary backend (backward compat — resolves without Named())
        if primary_entry.migration_dir:
            self._register_migration_runner(
                container, primary_svc, primary_entry.migration_dir
            )

    def _register_shared_stores(
        self,
        container: ContainerRegistrarProtocol,
        db_provider: Any,
    ) -> None:
        """Register shared database-backed stores: state, secrets, locks."""
        from lexigram.contracts.core.stores import LockStoreProtocol
        from lexigram.contracts.infra import StateStoreProtocol
        from lexigram.contracts.security.stores import AsyncSecretStoreProtocol
        from lexigram.sql.stores import (
            DatabaseLockStore,
            DatabaseSecretStore,
            DatabaseStateStore,
        )

        _db_ref = db_provider
        container.singleton(
            StateStoreProtocol,
            lambda: DatabaseStateStore(db_provider=_db_ref),
        )
        container.singleton(
            AsyncSecretStoreProtocol,
            lambda: DatabaseSecretStore(db_provider=_db_ref),
        )
        container.singleton(
            LockStoreProtocol,
            lambda: DatabaseLockStore(db_provider=_db_ref),
        )

    def _register_migration_runner(
        self,
        container: ContainerRegistrarProtocol,
        db_provider: Any,
        migration_dir: str,
        name: str | None = None,
    ) -> None:
        """Register migration runner for a database backend.

        Called for every backend that has ``migration_dir`` set (with ``name``),
        and again unnamed for the primary backend to preserve backward compatibility.
        """
        from lexigram.contracts import MigrationManagerProtocol
        from lexigram.contracts.data.sql.migrations import MigrationRunnerProtocol
        from lexigram.sql.migrations.runner import MigrationRunnerAdapter

        _db_ref = db_provider

        if db_provider.migration_manager:
            container.singleton(
                MigrationManagerProtocol,
                lambda: _db_ref.migration_manager,
                name=name,
            )

        _factory = lambda: MigrationRunnerAdapter(_db_ref.migration_manager)  # noqa: E731
        container.singleton(MigrationRunnerProtocol, _factory, name=name)

        try:
            from lexigram.sql.migrations.api import AlembicManager

            raw_url = _db_ref.config.backend.url
            migration_url = (
                raw_url.get_secret_value()
                if hasattr(raw_url, "get_secret_value")
                else str(raw_url)
            )
            migration_manager = AlembicManager(migration_url, migration_dir)
            container.singleton(AlembicManager, migration_manager, name=name)
            if self._enable_migrations:
                _db_ref.migration_manager = migration_manager
        except ImportError:
            pass

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot all database backends and wire optional observability integrations.

        In multi-backend mode all backends are connected in parallel.  In
        single-backend mode the existing sequential boot is preserved.
        """
        import asyncio

        context = None
        hooks = None
        resolve_optional = getattr(container, "resolve_optional", None)
        if callable(resolve_optional):
            maybe_context = resolve_optional(Context)
            context = (
                await maybe_context
                if inspect.isawaitable(maybe_context)
                else maybe_context
            )
            maybe_hooks = resolve_optional(HookRegistryProtocol)
            hooks = (
                await maybe_hooks if inspect.isawaitable(maybe_hooks) else maybe_hooks
            )
        services_to_wire = [svc for _, svc in self._db_services]
        if self._db_provider is not None:
            services_to_wire.append(self._db_provider)

        wired_service_ids: set[int] = set()
        for service in services_to_wire:
            service_id = id(service)
            if service_id in wired_service_ids:
                continue
            wired_service_ids.add(service_id)
            if hasattr(service, "set_context"):
                service.set_context(context)
            if hasattr(service, "set_hook_registry"):
                service.set_hook_registry(hooks)

        if self._db_services:
            # Multi-backend: connect all backends in parallel
            await asyncio.gather(*(svc.boot() for _, svc in self._db_services))
            logger.info(
                "all_databases_connected",
                count=len(self._db_services),
                names=[n for n, _ in self._db_services],
            )
        elif self._db_provider is not None:
            await self._db_provider.boot()
            logger.info("database_connected")
        else:
            return

        for service in services_to_wire:
            if hasattr(service, "set_context"):
                service.set_context(context)

        # Wire optional observability integrations into the primary backend
        if self._db_provider is None:
            return

        if self._db_provider.metrics is None:
            from lexigram.contracts.observability.metrics import (
                MetricsCollectorProtocol,
            )

            try:
                self._db_provider.metrics = await container.resolve(
                    MetricsCollectorProtocol
                )
            except UnresolvableDependencyError:
                logger.debug("metrics_collector_unavailable")

        if self._db_provider.tracer is None:
            from lexigram.contracts.observability.tracing import TracerProtocol

            try:
                self._db_provider.tracer = await container.resolve(TracerProtocol)
            except UnresolvableDependencyError:
                logger.debug("trace_provider_unavailable")

        # Wire optional resilience pipeline factory (provided by lexigram-resilience).
        resilience = self._db_provider.resilience_handler
        if resilience._pipeline_factory is None:
            from lexigram.contracts.infra.resilience import (
                ResiliencePipelineFactoryProtocol,
            )

            try:
                resilience._pipeline_factory = await container.resolve(
                    ResiliencePipelineFactoryProtocol
                )
            except UnresolvableDependencyError:
                logger.debug("resilience_pipeline_factory_unavailable")

        await self._boot_admin_widgets(container)

    def _register_admin_widgets(
        self,
        container: ContainerRegistrarProtocol,
    ) -> None:
        """Register admin widget services (renderer, handlers, contributor).

        Called after database backend registration.
        """
        from lexigram.sql.admin.contributor import SqlAdminContributor
        from lexigram.sql.admin.handlers.migration_status import (
            MigrationStatusWidgetHandler,
        )
        from lexigram.sql.admin.handlers.pool_utilization import (
            PoolUtilizationWidgetHandler,
        )
        from lexigram.sql.admin.handlers.query_stats import QueryStatsWidgetHandler
        from lexigram.sql.admin.renderer import PackageWidgetRenderer

        container.singleton(PackageWidgetRenderer, PackageWidgetRenderer)
        container.singleton(
            PoolUtilizationWidgetHandler,
            lambda: PoolUtilizationWidgetHandler(db=None),  # type: ignore[arg-type]
        )
        container.singleton(
            QueryStatsWidgetHandler,
            lambda: QueryStatsWidgetHandler(db=None),  # type: ignore[arg-type]
        )
        container.singleton(
            MigrationStatusWidgetHandler,
            lambda: MigrationStatusWidgetHandler(migration_manager=None),  # type: ignore[arg-type]
        )
        container.singleton(SqlAdminContributor, SqlAdminContributor)

    async def _boot_admin_widgets(
        self,
        container: ContainerResolverProtocol,
    ) -> None:
        """Boot admin widgets by calling on_admin_boot on the contributor."""
        from lexigram.sql.admin.contributor import SqlAdminContributor

        contributor = await container.resolve(SqlAdminContributor)
        await contributor.on_admin_boot(container)

    async def get_primary_pool(self) -> ConnectionPoolProtocol:  # type: ignore[name-defined]
        """Return the primary connection pool.

        For multi-backend setups, returns the backend marked `primary: true`.
        Raises NoPrimaryBackendError if no primary is marked or zero backends.

        Returns:
            The primary connection pool.

        Raises:
            NoPrimaryBackendError: If no primary backend is configured.
        """
        if self._db_provider is None:
            raise NoPrimaryBackendError(
                "No database backend is configured. "
                "Ensure DatabaseProvider is registered with a valid config."
            )

        pool = self._db_provider.connection_pool
        if pool is None:
            raise NoPrimaryBackendError(
                "Primary backend has no connection pool. "
                "Ensure the database backend was booted successfully."
            )

        return pool

    async def shutdown(self) -> None:
        """Disconnect all database backends in reverse registration order."""
        if self._db_services:
            for name, svc in reversed(self._db_services):
                await svc.shutdown()
                logger.info("database_disconnected", name=name)
        elif self._db_provider is not None:
            await self._db_provider.shutdown()
            logger.info("database_disconnected")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check provider health across all registered backends.

        In multi-backend mode the overall status is the worst individual status.

        Args:
            timeout: Maximum seconds to wait for health check response.

        Returns:
            HealthCheckResult with status and component details.
        """
        import asyncio

        start = time.perf_counter()

        if self._db_provider is None and not self._db_services:
            return HealthCheckResult(
                component="database",
                status=HealthStatus.DEGRADED,
                message="database provider not initialized",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        if self._db_services:
            results = await asyncio.gather(
                *(svc.health_check(timeout=timeout) for _, svc in self._db_services),
                return_exceptions=True,
            )
            statuses = []
            details: dict[str, str] = {}
            for (name, _), result in zip(self._db_services, results, strict=False):
                if isinstance(result, Exception):
                    statuses.append(HealthStatus.UNHEALTHY)
                    details[f"database:{name}"] = str(result)
                else:
                    statuses.append(result.status)  # type: ignore[union-attr]
                    details[f"database:{name}"] = result.status.value  # type: ignore[union-attr]

            overall = (
                HealthStatus.UNHEALTHY
                if HealthStatus.UNHEALTHY in statuses
                else HealthStatus.DEGRADED
                if HealthStatus.DEGRADED in statuses
                else HealthStatus.HEALTHY
            )
            return HealthCheckResult(
                component="database",
                status=overall,
                details=details,
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        # Single-backend fallback (existing behaviour unchanged)
        try:
            db_result = await self._db_provider.health_check(timeout=timeout)
            return HealthCheckResult(
                component="database",
                status=db_result.status,
                details=db_result.details,
                error=db_result.error,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        except (ConnectionError, TimeoutError, RuntimeError) as exc:
            return HealthCheckResult(
                component="database",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
                duration_ms=(time.perf_counter() - start) * 1000,
            )
