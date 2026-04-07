"""Database provider protocols.

These protocols define the contract for database implementations,
enabling swappable database backends (PostgreSQL, MySQL, SQLite, MongoDB).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from contextlib import AbstractAsyncContextManager
    from datetime import datetime

    from lexigram.contracts.core import HealthCheckResult


class IsolationLevel(StrEnum):
    """Standard SQL transaction isolation levels.

    These map directly to the ANSI SQL standard isolation levels.
    Drivers translate them to the appropriate driver-specific syntax.

    Note:
        Not all levels are supported by every database engine.
        SQLite maps levels to its ``DEFERRED``/``IMMEDIATE``/``EXCLUSIVE``
        semantics as a best-effort approximation.
    """

    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


@dataclass(frozen=True)
class QueryResult:
    """Result of a database query.

    Implements the iterator and sequence protocols so that code expecting
    a plain ``list[dict]`` from a query result continues to work after the
    return type is normalised to ``QueryResult``.

    Example::

        result = await provider.execute_query("SELECT * FROM users")
        for row in result:          # iterate directly
            print(row["email"])
        if not result:              # bool coercion
            raise LookupError("no rows")
        first = result[0]           # index access
        rows = list(result)         # convert to plain list
    """

    rows: list[dict[str, Any]]
    row_count: int
    execution_time: float
    success: bool
    error_message: str | None = None

    # ------------------------------------------------------------------
    # Sequence-like helpers
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate over query rows."""
        return iter(self.rows)

    def __len__(self) -> int:
        """Return the number of rows in the result."""
        return len(self.rows)

    def __bool__(self) -> bool:
        """Return ``True`` when the query succeeded and returned at least one row."""
        return self.success and bool(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        """Return the row at *index*.

        Args:
            index: Zero-based row index.

        Returns:
            Row dict at the requested index.
        """
        return self.rows[index]


@runtime_checkable
class ConnectionProtocol(Protocol):
    """Protocol for database connections.

    Represents an active database connection that can execute queries.
    """

    async def execute(
        self,
        query: str,
        *args: Any,
        timeout: float | None = None,
    ) -> QueryResult:
        """Execute a SQL query.

        Args:
            query: SQL query string with positional parameters ($1, $2, ...).
            *args: Positional arguments for the query.
            timeout: Optional timeout in seconds.

        Returns:
            QueryResult with rows and metadata.
        """
        ...

    async def fetchrow(
        self,
        query: str,
        *args: Any,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Fetch a single row from the database.

        Args:
            query: SQL query string.
            *args: Positional arguments for the query.
            timeout: Optional timeout in seconds.

        Returns:
            Row dictionary or None if not found.
        """
        ...

    async def close(self) -> None:
        """Close the connection."""
        ...

    async def fetch(
        self,
        query: str,
        *args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch rows from the database.

        Args:
            query: SQL query string.
            *args: Positional query parameters.
            **kwargs: Named query parameters.

        Returns:
            List of row dictionaries.
        """
        ...


@runtime_checkable
class DatabaseProviderProtocol(Protocol):
    """Protocol for database providers.

    This defines the interface that all database providers must implement,
    regardless of the underlying database technology.

    Example:
        ```python
        class PostgresProvider:
            async def connect(self) -> None:
                self._pool = await asyncpg.create_pool(self._dsn)

            async def execute_query(
                self,
                sql: str,
                params: list[Any] | None = None,
            ) -> QueryResult:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(sql, *params or [])
                    return QueryResult(rows=list(map(dict, rows)), ...)
        ```
    """

    # Connection lifecycle
    async def connect(self) -> None:
        """Establish connection to the database."""
        ...

    async def disconnect(self) -> None:
        """Close connection to the database."""
        ...

    async def is_connected(self) -> bool:
        """Check if database is connected."""
        ...

    async def get_primary_pool(self) -> ConnectionPoolProtocol:
        """Return the primary connection pool.

        For multi-backend setups, returns the backend marked `primary: true`.
        Raises NoPrimaryBackendError if no primary is marked or zero backends.

        Returns:
            The primary connection pool.

        Raises:
            NoPrimaryBackendError: If no primary backend is configured.
        """
        ...

    # Query execution
    async def execute_query(
        self,
        sql: str,
        params: list[Any] | None = None,
        **kwargs: Any,
    ) -> QueryResult:
        """Execute a SELECT query.

        Args:
            sql: SQL query string.
            params: Query parameters.
            **kwargs: Additional options.

        Returns:
            QueryResult with rows and execution metadata.
        """
        ...

    async def execute_insert(
        self,
        table: str,
        data: dict[str, Any],
        **kwargs: Any,
    ) -> InsertResult:
        """Execute an INSERT operation.

        Args:
            table: Table name.
            data: Column-value mapping.
            **kwargs: Additional options.

        Returns:
            InsertResult with inserted ID and influenced rows.
        """
        ...

    async def execute_update(
        self,
        table: str,
        data: dict[str, Any],
        where_clause: str,
        where_params: list[Any] | None = None,
        **kwargs: Any,
    ) -> UpdateResult:
        """Execute an UPDATE operation.

        Args:
            table: Table name.
            data: Column-value updates.
            where_clause: WHERE condition.
            where_params: Parameters for WHERE clause.
            **kwargs: Additional options.

        Returns:
            UpdateResult with affected rows.
        """
        ...

    async def execute_delete(
        self,
        table: str,
        where_clause: str,
        where_params: list[Any] | None = None,
        **kwargs: Any,
    ) -> DeleteResult:
        """Execute a DELETE operation.

        Args:
            table: Table name.
            where_clause: WHERE condition.
            where_params: Parameters for WHERE clause.
            **kwargs: Additional options.

        Returns:
            DeleteResult with affected rows.
        """
        ...

    async def execute(
        self,
        sql: str,
        params: Any = None,
    ) -> QueryResult:
        """Execute a raw SQL query with parameters.

        Args:
            sql: SQL query string.
            params: Query parameters.

        Returns:
            QueryResult with execution results.
        """
        ...

    # Transaction management
    def transaction(
        self, isolation_level: IsolationLevel | None = None
    ) -> AbstractAsyncContextManager[Any]:
        """Context manager for transactions.

        Args:
            isolation_level: Optional ANSI SQL isolation level.  When ``None``
                the driver's default isolation level is used.

        Example:
            ```python
            async with db.transaction(isolation_level=IsolationLevel.SERIALIZABLE):
                await db.execute("INSERT INTO ...")
                await db.execute("UPDATE ...")
            ```
        """
        ...

    async def begin_transaction(self) -> None:
        """Begin a transaction."""
        ...

    async def commit_transaction(self) -> None:
        """Commit current transaction."""
        ...

    async def rollback_transaction(self) -> None:
        """Rollback current transaction."""
        ...

    # Schema operations
    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        ...

    # Health check
    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform health check on database connection."""
        ...

    # Scoped session management
    def scoped_context(self) -> AbstractAsyncContextManager[Any]:
        """Return an async context manager that establishes a scoped session.

        The scoped context binds a database session to the current
        async context so that ``get_scoped_connection`` can retrieve it
        without passing the connection around explicitly.

        Returns:
            Async context manager that yields no value (or the session).
        """
        ...

    async def get_scoped_connection(self) -> ConnectionProtocol:
        """Return the connection bound to the current scoped context.

        Must be called within an active :meth:`scoped_context` block.

        Returns:
            Active :class:`ConnectionProtocol` for the current scope.
        """
        ...

    # Connection pool acquisition (low-level)
    async def acquire(self) -> ConnectionProtocol:
        """Acquire a connection from the pool for manual management.

        Use this when you need fine-grained control over connection lifecycle,
        but prefer :meth:`scoped_context` when possible for automatic cleanup.

        Returns:
            An acquired connection that must be released via :meth:`release`.

        Example:
            ```python
            conn = await db.acquire()
            try:
                result = await conn.execute("SELECT * FROM users")
            finally:
                await db.release(conn)
            ```
        """
        ...

    async def release(self, connection: ConnectionProtocol) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Connection acquired via :meth:`acquire`.
        """
        ...


@dataclass(frozen=True)
class InsertResult:
    """Result of an insert operation."""

    inserted_id: Any | None
    affected_rows: int
    execution_time: float
    success: bool
    error_message: str | None = None


@dataclass(frozen=True)
class UpdateResult:
    """Result of an update operation."""

    affected_rows: int
    execution_time: float
    success: bool
    error_message: str | None = None


@dataclass(frozen=True)
class DeleteResult:
    """Result of a delete operation."""

    affected_rows: int
    execution_time: float
    success: bool
    error_message: str | None = None


@runtime_checkable
class ConnectionPoolProtocol(Protocol):
    """Protocol for connection pools."""

    @property
    def max_connections(self) -> int: ...

    @property
    def connection_timeout(self) -> float: ...

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        ...

    async def shutdown(self) -> None:
        """Shutdown the connection pool."""
        ...

    def get_connection(self) -> AbstractAsyncContextManager[Any]:
        """Get a connection from the pool."""
        ...

    async def get_pool_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        ...

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check pool health."""
        ...

    async def get_query_stats(self, time_range_seconds: int = 3600) -> dict[str, Any]:
        """Get query statistics."""
        ...

    async def warm(self, count: int | None = None) -> None:
        """Pre-create *count* connections to avoid cold-start latency.

        Args:
            count: Number of connections to open. Defaults to ``min_connections``
                   (or the pool minimum) if not specified.
        """
        ...

    async def validate_connections(self) -> int:
        """Validate all idle connections in the pool, evicting dead ones.

        Returns:
            Number of valid connections remaining after validation.
        """
        ...


@dataclass
class MigrationRecord:
    """Record of a database migration."""

    version: str
    name: str
    applied_at: datetime
    success: bool
    error_message: str | None


@runtime_checkable
class MigrationManagerProtocol(Protocol):
    """Protocol for migration management."""

    async def initialize_migration_table(self) -> None:
        """Initialize the migration tracking table."""
        ...

    async def get_applied_migrations(self) -> list[MigrationRecord]:
        """Get list of applied migrations."""
        ...

    async def apply_migration(self, version: str, name: str, sql: str) -> bool:
        """Apply a migration."""
        ...

    async def rollback_migration(self, version: str) -> bool:
        """Rollback a migration."""
        ...

    async def get_pending_migrations(
        self,
        available_migrations: list[str],
    ) -> list[str]:
        """Get migrations that haven't been applied yet."""
        ...


# ---------------------------------------------------------------------------
# Focused sub-protocols (D1.2)
#
# Code that only needs one concern should depend on the narrowest protocol:
#
#   - TransactionManagerProtocol  — begin / commit / rollback only
#   - SchemaManagerProtocol       — DDL / table inspection
#   - CrudOperationsProtocol      — raw query execution
#   - HealthMonitorProtocol       — health-check only
#
# DatabaseProviderProtocol satisfies all four.
# ---------------------------------------------------------------------------


@runtime_checkable
class TransactionManagerProtocol(Protocol):
    """Minimal protocol for managing database transactions.

    Consume this instead of :class:`DatabaseProviderProtocol` when you only
    need transaction demarcation (e.g. a Unit of Work decorator).
    """

    async def begin_transaction(self) -> None:
        """Begin a new transaction."""
        ...

    async def commit_transaction(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback_transaction(self) -> None:
        """Roll back the current transaction."""
        ...


@runtime_checkable
class SchemaManagerProtocol(Protocol):
    """Minimal protocol for DDL / schema inspection.

    Consume this instead of :class:`DatabaseProviderProtocol` when you only
    need to inspect or modify the schema (e.g. a migration runner).
    """

    async def table_exists(self, table_name: str) -> bool:
        """Return ``True`` if the named table exists."""
        ...


@runtime_checkable
class CrudOperationsProtocol(Protocol):
    """Minimal protocol for raw CRUD query execution.

    Consume this instead of :class:`DatabaseProviderProtocol` when you only
    need to execute queries and DML statements (e.g. a generic repository).

    All methods return typed result objects so callers do not need to parse
    raw driver-specific return values.
    """

    async def execute_query(
        self,
        query: str,
        params: Any = None,
        *,
        timeout: float | None = None,
    ) -> QueryResult:
        """Execute a SELECT (or any read) query."""
        ...

    async def execute_insert(
        self,
        table: str,
        data: dict[str, Any],
        *,
        returning: list[str] | None = None,
    ) -> InsertResult:
        """Execute an INSERT statement."""
        ...

    async def execute_update(
        self,
        table: str,
        data: dict[str, Any],
        conditions: dict[str, Any],
        *,
        returning: list[str] | None = None,
    ) -> UpdateResult:
        """Execute an UPDATE statement."""
        ...

    async def execute_delete(
        self,
        table: str,
        conditions: dict[str, Any],
    ) -> DeleteResult:
        """Execute a DELETE statement."""
        ...


@runtime_checkable
class HealthMonitorProtocol(Protocol):
    """Minimal protocol for database health checking.

    Consume this instead of :class:`DatabaseProviderProtocol` when you only
    need to probe liveness (e.g. a health endpoint or a readiness probe).
    """

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return the current health of the database connection."""
        ...


@runtime_checkable
class DatabaseMetricsProtocol(Protocol):
    """Minimal protocol for exposing database connection-pool metrics.

    Consume this instead of :class:`DatabaseProviderProtocol` when you only
    need to collect pool telemetry (e.g. a metrics exporter or health dashboard).

    Implementations should return at least the following keys in the dict
    returned by :meth:`get_pool_stats`, though they may include additional
    driver-specific entries:

    * ``active_connections`` – number of connections currently in use.
    * ``idle_connections``   – number of connections available in the pool.
    * ``wait_time_ms``       – average time (ms) callers waited for a connection.
    """

    async def get_pool_stats(self) -> dict[str, int | float]:
        """Return pool statistics keyed by metric name.

        Returns:
            A dict containing at minimum ``active_connections``,
            ``idle_connections``, and ``wait_time_ms`` as ``int`` or
            ``float`` values.
        """
        ...


__all__ = [
    "ConnectionPoolProtocol",
    "ConnectionProtocol",
    "CrudOperationsProtocol",
    "DatabaseMetricsProtocol",
    "DatabaseProviderProtocol",
    "DeleteResult",
    "HealthMonitorProtocol",
    "InsertResult",
    "IsolationLevel",
    "MigrationManagerProtocol",
    "MigrationRecord",
    "QueryResult",
    "SchemaManagerProtocol",
    "TransactionManagerProtocol",
    "UpdateResult",
]
