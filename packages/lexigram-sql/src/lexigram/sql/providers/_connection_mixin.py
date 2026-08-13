"""Connection lifecycle, transaction, and scoped context mixin for DatabaseService."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts import HealthStatus

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from lexigram.contracts.data.sql.database import DatabaseProviderProtocol


class _ConnectionMixin:
    """Mixin providing connection lifecycle and transaction management for DatabaseService.

    All ``self.*`` attribute accesses here are satisfied by ``DatabaseService.__init__``;
    ``# type: ignore[attr-defined]`` comments suppress mypy errors for attributes that
    are not declared on this mixin but are guaranteed to exist at runtime.
    """

    db_provider: DatabaseProviderProtocol | None
    _started: bool
    _pipeline: Any | None

    async def connect(self) -> None:
        """Establish connection to the database.

        Delegates to the underlying db_provider if available,
        otherwise calls boot().
        """
        if self.db_provider:
            await self.db_provider.connect()
        elif not self._started:
            await self.boot()

    async def disconnect(self) -> None:
        """Close connection to the database."""
        if self.db_provider:
            await self.db_provider.disconnect()

    async def is_connected(self) -> bool:
        """Check if database is connected."""
        if self.db_provider:
            return await self.db_provider.is_connected()
        return self._started

    async def boot(self, container: Any | None = None) -> None:
        """Start the database provider and establish connections.

        Initializes the underlying database provider, connection pool,
        and runs health checks.

        Args:
            container: Optional DI container.

        Raises:
            RuntimeError: If the database health check fails.
        """
        if self._started:
            return

        if self.db_provider is None:
            self.db_provider = self._create_driver_provider()

        async def _connect() -> None:
            if self.db_provider and hasattr(self.db_provider, "connect"):
                await self.db_provider.connect()

        if (
            self.kwargs.get("connection_retry")  # type: ignore[attr-defined]
            and self.resilience_handler.retry_config  # type: ignore[attr-defined]
        ):
            pipeline = self._ensure_resilience_pipeline()
            if pipeline:
                await pipeline.execute(_connect)
            else:
                await _connect()
        else:
            await _connect()

        if (
            self.connection_pool  # type: ignore[attr-defined]
            and not getattr(
                self.connection_pool,  # type: ignore[attr-defined]
                "_initialized",
                False,
            )
            and hasattr(self.connection_pool, "initialize")  # type: ignore[attr-defined]
        ):
            await self.connection_pool.initialize()  # type: ignore[attr-defined]

        if (
            self.migration_manager  # type: ignore[attr-defined]
            and not getattr(
                self.migration_manager,  # type: ignore[attr-defined]
                "_initialized",
                False,
            )
            and hasattr(self.migration_manager, "initialize_migration_table")  # type: ignore[attr-defined]
        ):
            await self.migration_manager.initialize_migration_table()  # type: ignore[attr-defined]

        if self.migration_manager and hasattr(self.migration_manager, "upgrade"):  # type: ignore[attr-defined]
            await self.migration_manager.upgrade("head")  # type: ignore[attr-defined]

        health = await self.health_check()  # type: ignore[attr-defined]
        if hasattr(health, "status") and health.status == HealthStatus.UNHEALTHY:
            raise RuntimeError(
                f"Database health check failed: {getattr(health, 'error', 'Unknown error')}",
            )

        self._started = True

    def _create_driver_provider(self) -> Any:
        """Create the underlying driver-specific database provider.

        ``DatabaseService.__init__`` guarantees ``self.config`` is always a
        :class:`~lexigram.sql.config.DatabaseConfig` instance after the URL /
        string normalisation step.  The URL is exposed as a ``SecretStr`` on
        ``self.config.backend.url``; we unwrap it exactly once here, at the
        driver-connection boundary.
        """
        url = self.config.backend.url.get_secret_value()  # type: ignore[attr-defined]

        provider_type = (
            self._explicit_provider_type  # type: ignore[attr-defined]
            or self._infer_provider_type(url)  # type: ignore[attr-defined]
        )
        loader = self.get_driver_loader(provider_type)  # type: ignore[attr-defined]
        if loader is None:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        # Clean up kwargs to avoid multiple values for 'url'
        loader_kwargs = self.kwargs.copy()  # type: ignore[attr-defined]
        loader_kwargs.pop("url", None)
        loader_kwargs.pop("dsn", None)

        provider = loader(
            url,
            connection_pool=self.connection_pool,  # type: ignore[attr-defined]
            query_logger=self.query_logger,  # type: ignore[attr-defined]
            **loader_kwargs,
        )

        query_executor = getattr(provider, "query_executor", None)
        if query_executor is not None:
            query_executor._context = getattr(self, "_context", None)

        hook_registry = getattr(self, "_hook_registry", None)
        connection_manager = getattr(provider, "connection_manager", None)
        if connection_manager is not None and hasattr(
            connection_manager,
            "set_hook_registry",
        ):
            connection_manager.set_hook_registry(hook_registry)

        transaction_manager = getattr(provider, "transaction_manager", None)
        if transaction_manager is not None and hasattr(
            transaction_manager,
            "set_hook_registry",
        ):
            transaction_manager.set_hook_registry(hook_registry)

        return provider

    def _ensure_resilience_pipeline(self) -> Any:
        """Ensure the resilience pipeline (retry/circuit breaker) is configured."""
        if not self._pipeline:
            self._pipeline = self.resilience_handler.get_pipeline(  # type: ignore[attr-defined]
                self.name  # type: ignore[attr-defined]
            )
        return self._pipeline

    @asynccontextmanager
    async def transaction(
        self, isolation_level: Any | None = None
    ) -> AsyncGenerator[None, None]:
        """Context manager for executing code within a transaction.

        Args:
            isolation_level: Optional isolation level to use. When ``None``
                the driver's default is used.

        Yields:
            None - the transaction is managed automatically.

        Example:
            >>> async with provider.transaction():
            ...     await provider.execute_insert("users", data)
            ...     # Committed on success, rolled back on exception
        """
        if not self.db_provider:
            await self.boot()
        async with self.manager.transaction(isolation_level):  # type: ignore[attr-defined]
            yield

    @asynccontextmanager
    async def scoped_context(self) -> AsyncGenerator[Any, None]:
        """Get a scoped context for the current request/task.

        Yields:
            The scoped context dictionary.
        """
        async with self.manager.scoped_context() as ctx:  # type: ignore[attr-defined]
            yield ctx

    def get_current_context(self) -> dict[str, Any] | None:
        """Get the current database context for this request/scope."""
        return cast(
            "dict[str, Any] | None",
            self.manager.get_current_context(),  # type: ignore[attr-defined]
        )

    async def get_scoped_connection(self) -> Any:
        """Get a connection from the current scope.

        Returns:
            A database connection from the pool.
        """
        if not self.db_provider:
            await self.boot()
        return await self.manager.get_connection()  # type: ignore[attr-defined]

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Async context manager yielding a connection from the current scope or pool.

        When called within an active scoped context, borrows the scoped
        connection (which the scope will release).  When called outside a
        scope, acquires a fresh connection from the pool and releases it on
        context manager exit — preventing leaks.

        Yields:
            A database connection.

        Example:
            >>> async with provider.get_connection() as conn:
            ...     await conn.execute("SELECT * FROM users")
        """
        # Check if we're inside a scoped context that already has a connection.
        ctx = self.manager.get_current_context()  # type: ignore[attr-defined]
        if ctx is not None and ctx.get("connection") is not None:
            # Borrow from the scope — the scope's __aexit__ handles cleanup.
            conn = await self.manager.get_connection()  # type: ignore[attr-defined]
            yield conn
            return

        # No active scope — acquire from the pool and release on exit.
        # When booted, db_provider is a real provider with a proper
        # connection_manager that handles pool lifecycle.  Before boot or
        # in tests with a mock db_provider, fall through to the manager
        # path with manual cleanup.
        if self._started and self.db_provider is not None:
            cm = getattr(self.db_provider, "connection_manager", None)
            if cm is not None:
                async with cm.get_connection() as conn:
                    yield conn
                    return

        conn = await self.manager.get_connection()  # type: ignore[attr-defined]
        try:
            yield conn
        finally:
            if hasattr(conn, "close"):
                try:
                    await conn.close()
                except Exception:  # noqa: S110 — intentional best-effort fallback
                    pass

    def get_unit_of_work(self) -> Any:
        """Get a Unit of Work instance for the current scope.

        Returns:
            A UnitOfWork instance.
        """
        return self.manager.get_unit_of_work()  # type: ignore[attr-defined]

    async def begin_transaction(self) -> None:
        """Begin a transaction on the underlying database provider."""
        if not self.db_provider:
            await self.boot()
        if self.db_provider and hasattr(self.db_provider, "begin_transaction"):
            await self.db_provider.begin_transaction()

    async def commit_transaction(self) -> None:
        """Commit the current transaction."""
        if self.db_provider and hasattr(
            self.db_provider,
            "commit_transaction",
        ):
            await self.db_provider.commit_transaction()
        elif self.db_provider and hasattr(
            self.db_provider,
            "commit",
        ):
            await self.db_provider.commit()

    async def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        if self.db_provider and hasattr(
            self.db_provider,
            "rollback_transaction",
        ):
            await self.db_provider.rollback_transaction()
        elif self.db_provider and hasattr(
            self.db_provider,
            "rollback",
        ):
            await self.db_provider.rollback()

    async def shutdown(self) -> None:
        """Shutdown the database provider and close connections."""
        if not self._started:
            return
        connection_pool = getattr(self, "connection_pool", None)
        if connection_pool and hasattr(connection_pool, "shutdown"):
            await connection_pool.shutdown()
        if self.db_provider and hasattr(
            self.db_provider,
            "disconnect",
        ):
            await self.db_provider.disconnect()
        self._started = False

    @property
    def url(self) -> str:
        """Get the database connection URL.

        Returns:
            The connection URL string.
        """
        if hasattr(self.config, "backend"):  # type: ignore[attr-defined]
            raw_url = self.config.backend.url  # type: ignore[attr-defined]
            return (
                raw_url.get_secret_value()
                if hasattr(raw_url, "get_secret_value")
                else str(raw_url)
            )
        return str(self.config)  # type: ignore[attr-defined]

    async def acquire(self) -> Any:
        """Acquire a connection from the pool for manual management.

        Use this when you need fine-grained control over connection lifecycle,
        but prefer :meth:`scoped_context` when possible for automatic cleanup.

        Returns:
            An acquired connection that must be released via :meth:`release`.
        """
        if not self.db_provider:
            await self.boot()
        return await self.manager.get_connection()  # type: ignore[attr-defined]

    async def release(self, connection: Any) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Connection acquired via :meth:`acquire`.
        """
        if self.db_provider and hasattr(self.db_provider, "release"):
            await self.db_provider.release(connection)

    async def evict_dead_connections(self) -> int:
        """Evict dead connections from the pool and return count of remaining connections.

        Delegates to the connection pool's ``validate_connections()`` method if available.
        Returns 0 if no pool exists or the pool doesn't support validation.

        Returns:
            Number of valid connections remaining after eviction.
        """
        if self.connection_pool is None:  # type: ignore[attr-defined]
            return 0
        validator = getattr(self.connection_pool, "validate_connections", None)  # type: ignore[attr-defined]
        if validator is None:
            return 0
        return cast("int", await validator())
