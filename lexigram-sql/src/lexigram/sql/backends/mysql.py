"""MySQL database driver implementation"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import importlib
from typing import Any, cast

from lexigram.concurrency.task_utils import create_tracked_task
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock

aiomysql: Any = None
try:
    aiomysql = importlib.import_module("aiomysql")
    HAS_MYSQL = True
except (ImportError, ModuleNotFoundError):
    # aiomysql not installed in this environment
    aiomysql = None
    HAS_MYSQL = False

# Fallback alias: Exception when aiomysql is unavailable
MySQLError: type = getattr(aiomysql, "Error", Exception)

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.infra.resilience import CircuitBreakerProtocol
from lexigram.sql.abstractions.connection import DatabaseConnection
from lexigram.sql.lib.retry import retry_call
from lexigram.sql.monitoring import DatabaseMonitor

logger = get_logger(__name__)

HAS_MONITORING = True


from lexigram.sql.exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseTimeoutError,
    QueryError,
)


class MySQLConnection(DatabaseConnection):
    """MySQL database connection"""

    def __init__(self, connection: Any, monitor: DatabaseMonitor | None = None) -> None:
        self._conn = connection
        self.monitor = monitor
        self.connection_id = f"mysql_{id(connection)}"

    async def execute(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> Any:
        """Execute a query and return results"""
        if self.monitor and HAS_MONITORING:
            async with self.monitor.get_query_monitor().monitor_query(
                query=query,
                parameters=list(params) if params else None,
                connection_id=self.connection_id,
            ):
                try:
                    if params:
                        await self._conn.execute(query, params)
                    else:
                        await self._conn.execute(query)
                    return self._conn.affected_rows
                except MySQLError as e:  # type: ignore[misc]
                    logger.exception("MySQL query execution failed")
                    raise QueryError(
                        f"Query execution failed: {e}",
                        details={"query": query, "error": str(e)},
                    ) from e
                except (
                    DatabaseError,
                    QueryError,
                    DatabaseConnectionError,
                    DatabaseTimeoutError,
                    Exception,
                ) as e:
                    logger.exception("MySQL query execution failed (unexpected)")
                    raise QueryError(
                        f"Query execution failed: {e}",
                        details={"query": query, "error": str(e)},
                    ) from e
        else:
            try:
                if params:
                    await self._conn.execute(query, params)
                else:
                    await self._conn.execute(query)
                return self._conn.affected_rows
            except MySQLError as e:  # type: ignore[misc]
                logger.exception("MySQL query execution failed")
                raise QueryError(
                    f"Query execution failed: {e}",
                    details={"query": query, "error": str(e)},
                ) from e
            except (
                DatabaseError,
                QueryError,
                DatabaseConnectionError,
                DatabaseTimeoutError,
                Exception,
            ) as e:
                logger.exception("MySQL query execution failed (unexpected)")
                raise QueryError(
                    f"Query execution failed: {e}",
                    details={"query": query, "error": str(e)},
                ) from e

    async def execute_many(
        self,
        query: str,
        params_list: list[tuple[object, ...]],
    ) -> None:
        """Execute a query with multiple parameter sets"""
        try:
            async with self._conn.cursor() as cursor:
                await cursor.executemany(query, params_list)
                await self._conn.commit()
        except MySQLError as e:  # type: ignore[misc]
            logger.exception("MySQL batch execution failed")
            raise QueryError(
                f"Batch execution failed: {e}",
                details={"query": query, "error": str(e)},
            ) from e
        except (
            DatabaseError,
            QueryError,
            DatabaseConnectionError,
            DatabaseTimeoutError,
            Exception,
        ) as e:
            logger.exception("Unexpected error in MySQL batch operation")
            raise QueryError(
                f"Batch execution failed: {e}",
                details={"query": query, "error": str(e)},
            ) from e

    async def fetch_one(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> dict[str, Any] | None:
        """Fetch a single row"""
        if self.monitor and HAS_MONITORING:
            async with self.monitor.get_query_monitor().monitor_query(
                query=query,
                parameters=list(params) if params else None,
                connection_id=self.connection_id,
            ):
                try:
                    async with self._conn.cursor(aiomysql.DictCursor) as cursor:
                        if params:
                            await cursor.execute(query, params)
                        else:
                            await cursor.execute(query)
                        result = await cursor.fetchone()
                        return cast("dict[str, Any] | None", result)
                except MySQLError as e:  # type: ignore[misc]  # type: ignore[misc]
                    logger.exception("MySQL query fetch failed")
                    raise QueryError(
                        f"Query fetch failed: {e}",
                        details={"query": query, "error": str(e)},
                    ) from e
                except (
                    DatabaseError,
                    QueryError,
                    DatabaseConnectionError,
                    DatabaseTimeoutError,
                    Exception,
                ) as e:
                    logger.exception("Unexpected error in MySQL fetch operation")
                    raise QueryError(
                        f"Query fetch failed: {e}",
                        details={"query": query, "error": str(e)},
                    ) from e
        else:
            try:
                async with self._conn.cursor(aiomysql.DictCursor) as cursor:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    result = await cursor.fetchone()
                    return cast("dict[str, Any] | None", result)
            except MySQLError as e:  # type: ignore[misc]
                logger.exception("MySQL query fetch failed")
                raise QueryError(
                    f"Query fetch failed: {e}",
                    details={"query": query, "error": str(e)},
                ) from e
            except (
                DatabaseError,
                QueryError,
                DatabaseConnectionError,
                DatabaseTimeoutError,
                Exception,
            ) as e:
                logger.exception("Unexpected error in MySQL fetch operation")
                raise QueryError(
                    f"Query fetch failed: {e}",
                    details={"query": query, "error": str(e)},
                ) from e

    async def fetch_all(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all rows"""
        if self.monitor and HAS_MONITORING:
            async with self.monitor.get_query_monitor().monitor_query(
                query=query,
                parameters=list(params) if params else None,
                connection_id=self.connection_id,
            ):
                try:
                    async with self._conn.cursor(aiomysql.DictCursor) as cursor:
                        if params:
                            await cursor.execute(query, params)
                        else:
                            await cursor.execute(query)
                        result = await cursor.fetchall()
                        return result or []
                except MySQLError as e:  # type: ignore[misc]  # type: ignore[misc]
                    logger.exception("MySQL query fetch all failed")
                    raise QueryError(
                        f"Query fetch all failed: {e}",
                        details={"query": query, "error": str(e)},
                    ) from e
                except (
                    DatabaseError,
                    QueryError,
                    DatabaseConnectionError,
                    DatabaseTimeoutError,
                ) as e:
                    logger.exception("Unexpected error in MySQL fetch all operation")
                    raise QueryError(
                        f"Query fetch all failed: {e}",
                        details={"query": query, "error": str(e)},
                    ) from e
        else:
            try:
                async with self._conn.cursor(aiomysql.DictCursor) as cursor:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    result = await cursor.fetchall()
                    return result or []
            except MySQLError as e:  # type: ignore[misc]
                logger.exception("MySQL query fetch all failed")
                raise QueryError(
                    f"Query fetch all failed: {e}",
                    details={"query": query, "error": str(e)},
                ) from e
            except (
                DatabaseError,
                QueryError,
                DatabaseConnectionError,
                DatabaseTimeoutError,
            ) as e:
                logger.exception("Unexpected error in MySQL fetch all operation")
                raise QueryError(
                    f"Query fetch all failed: {e}",
                    details={"query": query, "error": str(e)},
                ) from e

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[MySQLConnection, None]:
        """Simple transaction context manager for MySQL connection"""
        try:
            yield self
        finally:
            pass

    async def close(self) -> None:
        """Close the connection"""
        try:
            if hasattr(self._conn, "close"):
                close_fn = self._conn.close
                if asyncio.iscoroutinefunction(close_fn):
                    await close_fn()
                else:
                    close_fn()
        except (
            OSError,
            ConnectionError,
            RuntimeError,
        ):  # pragma: no cover - best-effort close
            logger.exception("Failed to close MySQL connection")


from lexigram.contracts import (
    ConnectionPoolProtocol,
    HealthCheckResult,
    HealthStatus,
    RetryConfig,
)

# ...


class MySQLConnectionPool(ConnectionPoolProtocol):
    """MySQL connection pool with health checks and resilience"""

    def __init__(
        self,
        host: str,
        port: int = 3306,
        user: str = "",
        password: str = "",
        database: str = "",
        min_size: int = 10,
        max_size: int = 20,
        ssl: dict[str, Any] | None = None,
        retry_config: RetryConfig | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
        monitor: DatabaseMonitor | None = None,
        **kwargs: Any,
    ) -> None:
        if not HAS_MYSQL:
            raise ImportError(
                "aiomysql is required for MySQL support. Install with: pip install lexigram-sql[mysql]",
            )

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.ssl = ssl
        self.pool_kwargs = kwargs
        self._pool: Any | None = None
        self._is_healthy = False
        self._last_health_check = 0.0
        self._connection_count = 0
        self._error_count = 0
        self._total_connections_created = 0
        self._background_tasks: set[asyncio.Task[Any]] = set()

        # Resilience patterns
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            retry_on=(MySQLError, ConnectionError),
        )
        self.circuit_breaker: CircuitBreakerProtocol | None = circuit_breaker

        # Monitoring
        self.monitor = monitor
        if self.monitor and HAS_MONITORING:
            # Start pool monitoring via TaskManager for graceful shutdown

            self._monitoring_task = create_tracked_task(
                self.monitor.start_pool_monitoring(self),
                self._background_tasks,
                name=f"mysql_pool_monitor_{id(self)}",
            )

    @property
    def max_connections(self) -> int:
        return self.max_size

    @property
    def connection_timeout(self) -> float:
        return cast("float", self.pool_kwargs.get("timeout", 10.0))

    async def initialize(self) -> None:
        """Initialize the connection pool with SSL and retry logic"""
        if self._pool:
            return

        # Configure SSL if specified
        pool_kwargs = self.pool_kwargs.copy()
        if self.ssl:
            pool_kwargs.update(self.ssl)

        # Set pool size parameters
        pool_kwargs.update(
            {
                "minsize": self.min_size,
                "maxsize": self.max_size,
            },
        )

        # Create connection pool
        if self.retry_config:
            await retry_call(
                self._create_pool,
                config=self.retry_config,
                pool_kwargs=pool_kwargs,
            )
        else:
            await self._create_pool(pool_kwargs)

    async def _create_pool(self, pool_kwargs: dict[str, Any]) -> None:
        """Internal pool creation with error handling"""
        try:
            self._pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                **pool_kwargs,
            )
            self._total_connections_created += 1
            self._is_healthy = True
            logger.info(
                "MySQL pool initialized with %s-%s connections",
                self.min_size,
                self.max_size,
            )
        except Exception as e:  # noqa: BLE001 — pool initialization must catch all infrastructure errors
            self._error_count += 1
            self._is_healthy = False
            logger.exception("Failed to create MySQL pool")
            raise DatabaseConnectionError(f"Pool creation failed: {e}") from e

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[MySQLConnection, None]:
        """Get a connection from the pool with circuit breaker protection"""
        if not self._pool:
            await self.initialize()

        if self._pool is None:
            raise RuntimeError("MySQL pool not initialized")

        # Use circuit breaker for connection acquisition
        logger.debug("Acquiring MySQL connection")
        if self.circuit_breaker:
            async with self.circuit_breaker.protect():
                try:
                    async with self._pool.acquire() as conn:
                        self._connection_count += 1
                        yield MySQLConnection(conn, self.monitor)
                except (
                    OSError,
                    ConnectionError,
                    RuntimeError,
                    TimeoutError,
                    Exception,
                ) as e:
                    self._error_count += 1
                    self._is_healthy = False
                    logger.exception("Connection acquisition failed")
                    raise DatabaseConnectionError(
                        f"Connection acquisition failed: {e}",
                    ) from e

        else:
            try:
                async with self._pool.acquire() as conn:
                    self._connection_count += 1
                    yield MySQLConnection(conn, self.monitor)
            except (
                OSError,
                ConnectionError,
                RuntimeError,
                TimeoutError,
                Exception,
            ) as e:
                self._error_count += 1
                self._is_healthy = False
                logger.exception("Connection acquisition failed")
                raise DatabaseConnectionError(
                    f"Connection acquisition failed: {e}"
                ) from e

    async def shutdown(self) -> None:
        """Close all connections in the pool"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            self._is_healthy = False

            # Stop monitoring
            if self.monitor and HAS_MONITORING:
                await self.monitor.stop_pool_monitoring()

            logger.info("MySQL pool closed")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform health check on the MySQL connection pool"""
        current_time = ambient_clock.timestamp()

        # Cache health checks for 30 seconds
        if current_time - self._last_health_check < 30.0 and self._is_healthy:
            return HealthCheckResult(
                component="database",
                status=HealthStatus.HEALTHY,
                details={
                    "host": f"{self.host}:{self.port}",
                    "database": self.database,
                    "pool_size": f"{self.min_size}-{self.max_size}",
                    "connections_created": self._total_connections_created,
                    "cached": True,
                },
                checked_at=datetime.fromtimestamp(current_time, UTC),
            )

        self._last_health_check = current_time

        if not self._pool:
            self._is_healthy = False
            return HealthCheckResult(
                component="database",
                status=HealthStatus.UNHEALTHY,
                message="Pool not initialized",
                error="Pool not initialized",
                details={
                    "host": f"{self.host}:{self.port}",
                    "database": self.database,
                    "pool_size": f"{self.min_size}-{self.max_size}",
                },
                checked_at=datetime.fromtimestamp(current_time, UTC),
            )

        try:
            # Test connection with a simple query
            async with self.get_connection() as conn:  # type: MySQLConnection
                result = await conn.execute("SELECT 1 as health_check")
                if result is not None:
                    self._is_healthy = True
                    return HealthCheckResult(
                        component="database",
                        status=HealthStatus.HEALTHY,
                        details={
                            "host": f"{self.host}:{self.port}",
                            "database": self.database,
                            "pool_size": f"{self.min_size}-{self.max_size}",
                            "connections_created": self._total_connections_created,
                            "active_connections": self._connection_count,
                            "error_count": self._error_count,
                            "circuit_breaker_state": (
                                str(self.circuit_breaker.state)
                                if self.circuit_breaker
                                else "unknown"
                            ),
                        },
                        checked_at=datetime.fromtimestamp(current_time, UTC),
                    )
                self._is_healthy = False
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Health check query failed",
                    error="Health check query failed",
                    details={
                        "host": f"{self.host}:{self.port}",
                        "database": self.database,
                        "pool_size": f"{self.min_size}-{self.max_size}",
                    },
                    checked_at=datetime.fromtimestamp(current_time, UTC),
                )
        except (
            DatabaseError,
            QueryError,
            DatabaseConnectionError,
            DatabaseTimeoutError,
            Exception,
        ) as e:
            self._is_healthy = False
            if not isinstance(e, DatabaseConnectionError):
                self._error_count += 1
            logger.exception("MySQL health check failed")
            return HealthCheckResult(
                component="database",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                error=str(e),
                details={
                    "host": f"{self.host}:{self.port}",
                    "database": self.database,
                    "pool_size": f"{self.min_size}-{self.max_size}",
                    "error_count": self._error_count,
                },
                checked_at=datetime.fromtimestamp(current_time, UTC),
            )

    async def get_pool_stats(self) -> dict[str, Any]:
        """Get MySQL connection pool statistics"""
        return {
            "host": f"{self.host}:{self.port}",
            "database": self.database,
            "pool_size": f"{self.min_size}-{self.max_size}",
            "is_initialized": self._pool is not None,
            "is_healthy": self._is_healthy,
            "total_connections_created": self._total_connections_created,
            "active_connection_count": self._connection_count,
            "error_count": self._error_count,
            "circuit_breaker_state": (
                str(self.circuit_breaker.state) if self.circuit_breaker else "unknown"
            ),
            "last_health_check": self._last_health_check,
            "monitoring_enabled": self.monitor is not None,
        }

    async def get_query_stats(self, time_range_seconds: int = 3600) -> dict[str, Any]:
        """Get query stats"""
        return {}


def create_mysql_pool(
    host: str = "localhost",
    port: int = 3306,
    user: str = "root",
    password: str = "",
    database: str = "",
    min_size: int = 10,
    max_size: int = 20,
    ssl: dict[str, Any] | None = None,
    retry_config: RetryConfig | None = None,
    circuit_breaker: CircuitBreakerProtocol | None = None,
    monitor: DatabaseMonitor | None = None,
    **kwargs: Any,
) -> MySQLConnectionPool:
    """Factory function to create MySQL connection pool with resilience features

    Args:
        host: MySQL server host
        port: MySQL server port
        user: MySQL username
        password: MySQL password
        database: MySQL database name
        min_size: Minimum pool size
        max_size: Maximum pool size
        ssl: SSL configuration dictionary
        retry_config: Retry configuration for connection operations
        circuit_breaker: Pre-configured circuit breaker instance for protection
        monitor: Database monitor for observability
        **kwargs: Additional aiomysql pool arguments

    Returns:
        Configured MySQL connection pool
    """
    return MySQLConnectionPool(  # type: ignore[abstract]
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        min_size=min_size,
        max_size=max_size,
        ssl=ssl,
        retry_config=retry_config,
        circuit_breaker=circuit_breaker,
        monitor=monitor,
        **kwargs,
    )
