"""Database monitoring classes"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Any

from lexigram.concurrency.task_utils import create_tracked_task
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.sql.exceptions import DatabaseConnectionError, DatabaseError
from lexigram.sql.lib import infer_provider_type_from_url
from lexigram.sql.monitoring.metrics import (
    ConnectionMetrics,
    DbMetricsCollector,
    HealthStatus,
    QueryMetrics,
    TransactionMetrics,
)

logger = get_logger(__name__)


class QueryMonitor:
    """Monitors database query execution"""

    def __init__(
        self,
        collector: DbMetricsCollector,
        slow_query_threshold: float = 1.0,
    ):
        self.collector = collector
        self.slow_query_threshold = slow_query_threshold

    def _get_time(self) -> float:
        """Get current timestamp."""
        return ambient_clock.timestamp()

    def _get_datetime(self) -> datetime:
        """Get current datetime."""
        return ambient_clock.now()

    @asynccontextmanager
    async def monitor_query(
        self,
        query: str,
        parameters: list[Any] | None = None,
        connection_id: str | None = None,
        transaction_id: str | None = None,
    ) -> AsyncGenerator[None, None]:
        """Context manager to monitor query execution"""
        start_time = self._get_time()
        success = False
        error_message = None

        try:
            yield
            success = True
        except (
            DatabaseError,
            OSError,
            ConnectionError,
            RuntimeError,
            TimeoutError,
            ValueError,
            TypeError,
        ) as e:
            error_message = str(e)
            raise
        finally:
            execution_time = self._get_time() - start_time

            metrics = QueryMetrics(
                query=query,
                parameters=parameters,
                execution_time=execution_time,
                timestamp=self._get_datetime(),
                success=success,
                error_message=error_message,
                connection_id=connection_id,
                transaction_id=transaction_id,
            )

            await self.collector.record_query_metrics(metrics)

            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning("SLOW QUERY: %.3fs - %s", execution_time, query)

    async def get_stats(self, time_range_seconds: int = 3600) -> dict[str, Any]:
        """Get monitoring statistics"""
        return await self.collector.get_query_stats(time_range_seconds)


class TransactionMonitor:
    """Monitors database transaction execution"""

    def __init__(
        self,
        collector: DbMetricsCollector,
    ):
        self.collector = collector

    def _get_datetime(self) -> datetime:
        """Get current datetime."""
        return ambient_clock.now()

    @asynccontextmanager
    async def monitor_transaction(
        self,
        transaction_id: str,
        nested_level: int = 0,
    ) -> AsyncGenerator[None, None]:
        """Context manager to monitor transaction execution"""
        start_time = self._get_datetime()
        success = False
        operation = "unknown"
        deadlock_detected = False
        error_message = None

        try:
            yield
            success = True
            operation = "commit"
        except (
            DatabaseError,
            OSError,
            ConnectionError,
            RuntimeError,
            TimeoutError,
            ValueError,
            TypeError,
        ) as e:
            error_message = str(e)
            operation = "rollback"

            # Check for deadlock indicators
            error_lower = error_message.lower()
            if any(
                keyword in error_lower
                for keyword in [
                    "deadlock",
                    "lock wait timeout",
                    "serialization failure",
                ]
            ):
                deadlock_detected = True

            raise
        finally:
            end_time = self._get_datetime()
            duration = (end_time - start_time).total_seconds()

            metrics = TransactionMetrics(
                transaction_id=transaction_id,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                operation=operation,
                success=success,
                deadlock_detected=deadlock_detected,
                error_message=error_message,
                nested_level=nested_level,
            )

            await self.collector.record_transaction_metrics(metrics)

    async def get_stats(self, time_range_seconds: int = 3600) -> dict[str, Any]:
        """Get transaction monitoring statistics"""
        return await self.collector.get_transaction_stats(time_range_seconds)


class DatabaseHealthChecker:
    """Database health checker - avoids collision with lexigram.health.HealthChecker"""

    def __init__(
        self,
        collector: DbMetricsCollector,
    ):
        self.collector = collector

    def _get_time(self) -> float:
        """Get current timestamp."""
        return ambient_clock.timestamp()

    def _get_datetime(self) -> datetime:
        """Get current datetime."""
        return ambient_clock.now()

    async def check_database_health(
        self,
        connection_string: str,
        timeout: float = 5.0,
    ) -> HealthStatus:
        """Check database connectivity and basic health"""

        from sqlalchemy import (
            create_engine,
            text,
        )

        component = "database"
        start_time = self._get_time()

        try:
            # Create connection with timeout where supported. For SQLite URIs we skip
            # connect_args because the sqlite DBAPI doesn't accept them.
            try:
                # Prefer canonical provider detection but fall back to startswith for
                # non-conforming inputs to remain permissive.
                try:
                    is_sqlite = (
                        infer_provider_type_from_url(connection_string) == "sqlite"
                    )
                except (ValueError, TypeError):
                    is_sqlite = isinstance(
                        connection_string,
                        str,
                    ) and connection_string.startswith("sqlite:")

                if is_sqlite:
                    engine = create_engine(connection_string)
                else:
                    engine = create_engine(
                        connection_string,
                        connect_args={"connect_timeout": timeout},
                    )
            except (ValueError, TypeError, RuntimeError, OSError):
                # Some drivers may still raise; fall back to a no-args engine
                engine = create_engine(connection_string)

            async def check_connectivity() -> bool:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, _sync_check_connectivity)

            def _sync_check_connectivity() -> bool:
                with engine.connect() as conn:
                    # Simple health check query
                    result = conn.execute(text("SELECT 1 as health_check"))
                    row = result.fetchone()
                    if row is None:
                        return False
                    return bool(row[0] == 1)

            # Run with timeout and allow a fallback attempt without connect_args if the
            # first attempt fails (some drivers like SQLite reject certain connect args)
            try:
                result = await asyncio.wait_for(check_connectivity(), timeout=timeout)
            except (OSError, RuntimeError, ValueError, TimeoutError) as first_exc:
                # Try again with a fresh engine that does not pass connect_args
                try:
                    engine.dispose()
                except (RuntimeError, OSError) as e:
                    logger.debug(
                        "Engine dispose failed during health check fallback: %s",
                        e,
                        exc_info=True,
                    )

                try:
                    engine_no_connect_args = create_engine(connection_string)

                    async def _check_no_args() -> bool:
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, _sync_check_no_args)

                    def _sync_check_no_args() -> bool:
                        with engine_no_connect_args.connect() as conn:
                            result = conn.execute(text("SELECT 1 as health_check"))
                            row = result.fetchone()
                            return bool(row and row[0] == 1)

                    result = await asyncio.wait_for(_check_no_args(), timeout=timeout)
                    engine = engine_no_connect_args
                except (
                    OSError,
                    ConnectionError,
                    RuntimeError,
                    TimeoutError,
                    ValueError,
                ) as second_exc:
                    # If both attempts failed, surface the original error message
                    raise second_exc from first_exc

            if result:
                status = "healthy"
                message = "Database connection successful"
            else:
                status = "critical"
                message = "Database health check failed"

        except TimeoutError:
            status = "critical"
            message = f"Database connection timeout after {timeout}s"
        except (
            DatabaseError,
            DatabaseConnectionError,
            OSError,
            ConnectionError,
            RuntimeError,
        ) as e:
            logger.exception("Database health check failed")
            status = "critical"
            message = f"Database connection failed: {e!s}"
        finally:
            if "engine" in locals():
                engine.dispose()

        response_time = self._get_time() - start_time

        return HealthStatus(
            component=component,
            status=status,  # type: ignore[arg-type]
            message=message,
            timestamp=self._get_datetime(),
            details={"response_time": response_time, "timeout": timeout},
        )

    async def check_connection_pool_health(self, pool: Any) -> HealthStatus:
        """Check connection pool health"""
        component = "connection_pool"
        status = "critical"
        message = "Connection pool health check failed"
        details = {}

        try:
            # Get pool statistics
            active = getattr(pool, "_active_connections", 0)
            total = getattr(pool, "_total_connections", 0)
            available = total - active

            # Check utilization
            utilization = active / total if total > 0 else 0

            if utilization > 0.95:
                status = "critical"
                message = f"Connection pool critically overutilized: {utilization:.1%}"
            elif utilization > 0.85:
                status = "warning"
                message = f"Connection pool highly utilized: {utilization:.1%}"
            else:
                status = "healthy"
                message = f"Connection pool healthy: {utilization:.1%}"

            details = {
                "active_connections": active,
                "total_connections": total,
                "available_connections": available,
                "utilization": utilization,
            }

        except (
            DatabaseError,
            DatabaseConnectionError,
            OSError,
            ConnectionError,
            RuntimeError,
            TimeoutError,
            TypeError,
            AttributeError,
        ) as e:
            # Log full traceback for diagnostics then return critical status
            logger.exception("Connection pool health check failed")
            details = {"error": str(e)}

        return HealthStatus(
            component=component,
            status=status,  # type: ignore[arg-type]
            message=message,
            timestamp=self._get_datetime(),
            details=details,
        )

    async def check_performance_health(
        self,
        time_range_seconds: int = 3600,
    ) -> list[HealthStatus]:
        """Check performance against baselines"""
        baselines = await self.collector.get_performance_baselines()
        query_stats = await self.collector.get_query_stats(time_range_seconds)
        transaction_stats = await self.collector.get_transaction_stats(
            time_range_seconds,
        )

        health_checks = []

        # Check query performance
        if query_stats["total_queries"] > 0:
            avg_query_time = query_stats["average_execution_time"]
            baseline = next(
                (b for b in baselines if b.metric_name == "query_execution_time"),
                None,
            )

            if baseline:
                if avg_query_time > baseline.critical_threshold:
                    status = "critical"
                    message = f"Average query time critically high: {avg_query_time:.3f}s > {baseline.critical_threshold}s"
                elif avg_query_time > baseline.warning_threshold:
                    status = "warning"
                    message = f"Average query time elevated: {avg_query_time:.3f}s > {baseline.warning_threshold}s"
                else:
                    status = "healthy"
                    message = f"Query performance healthy: {avg_query_time:.3f}s"

                health_checks.append(
                    HealthStatus(
                        component="query_performance",
                        status=status,  # type: ignore[arg-type]
                        message=message,
                        timestamp=self._get_datetime(),
                        details={
                            "average_query_time": avg_query_time,
                            "baseline_expected": baseline.expected_value,
                            "baseline_warning": baseline.warning_threshold,
                            "baseline_critical": baseline.critical_threshold,
                        },
                    ),
                )

        # Check transaction performance
        if transaction_stats["total_transactions"] > 0:
            commit_ratio = transaction_stats["commit_ratio"]
            baseline = next(
                (b for b in baselines if b.metric_name == "transaction_commit_ratio"),
                None,
            )

            if baseline:
                if commit_ratio < baseline.critical_threshold:
                    status = "critical"
                    message = (
                        f"Transaction commit ratio critically low: {commit_ratio:.1%} "
                        f"< {baseline.critical_threshold:.1%}"
                    )
                elif commit_ratio < baseline.warning_threshold:
                    status = "warning"
                    message = f"Transaction commit ratio low: {commit_ratio:.1%} < {baseline.warning_threshold:.1%}"
                else:
                    status = "healthy"
                    message = f"Transaction success rate healthy: {commit_ratio:.1%}"

                health_checks.append(
                    HealthStatus(
                        component="transaction_performance",
                        status=status,  # type: ignore[arg-type]
                        message=message,
                        timestamp=self._get_datetime(),
                        details={
                            "commit_ratio": commit_ratio,
                            "total_transactions": transaction_stats[
                                "total_transactions"
                            ],
                            "successful_transactions": transaction_stats[
                                "successful_transactions"
                            ],
                            "failed_transactions": transaction_stats[
                                "failed_transactions"
                            ],
                        },
                    ),
                )

        return health_checks


class ConnectionPoolMonitor:
    """Monitors database connection pool usage"""

    def __init__(
        self,
        collector: DbMetricsCollector,
    ):
        self.collector = collector
        self.monitoring_task: asyncio.Task[Any] | None = None
        self.pool: Any = None
        self._provider: Any = None
        self._background_tasks: set[asyncio.Task[Any]] = set()

    def _get_datetime(self) -> datetime:
        """Get current datetime."""
        return ambient_clock.now()

    async def start_monitoring(self, pool: Any, provider: Any = None) -> None:
        """Start monitoring a connection pool.

        Args:
            pool: The connection pool to monitor.
            provider: Optional database provider used for active connection
                probing. When supplied, :meth:`_probe_pool` will open a
                scoped connection and execute ``SELECT 1`` to verify the
                pool is healthy.
        """
        self.pool = pool
        self._provider = provider
        self.monitoring_task = create_tracked_task(
            self._monitor_pool(),
            self._background_tasks,
            name=f"sql_monitor_{id(self)}",
        )

    async def stop_monitoring(self) -> None:
        """Stop pool monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            # Await the cancelled task but suppress CancelledError for graceful shutdown
            with suppress(asyncio.CancelledError):
                await self.monitoring_task
            self.monitoring_task = None

    async def _monitor_pool(self) -> None:
        """Background task to monitor pool statistics"""
        while True:
            try:
                await self._collect_pool_metrics()
                await self._probe_pool()
                await asyncio.sleep(30)  # Collect metrics every 30 seconds
            except asyncio.CancelledError:
                break
            except (
                DatabaseError,
                DatabaseConnectionError,
                OSError,
                ConnectionError,
                RuntimeError,
                TimeoutError,
            ):
                logger.exception("Error monitoring connection pool")
                await asyncio.sleep(30)

    async def _probe_pool(self) -> None:
        """Actively probe the pool by running ``SELECT 1`` via a scoped connection.

        Opens a scoped connection from ``self._provider`` and executes a
        trivial ``SELECT 1`` query to confirm the pool is healthy. On any
        failure the error is logged at WARNING level and
        ``self._provider.evict_dead_connections()`` is called to remove
        dead connections and refill the pool. The count of remaining valid
        connections is logged at INFO level.

        This method never raises — monitoring must always remain resilient.
        """
        if self._provider is None:
            return
        try:
            async with self._provider.scoped_context():
                conn = await self._provider.get_scoped_connection()
                await conn.execute("SELECT 1")
        except (
            DatabaseError,
            DatabaseConnectionError,
            OSError,
            ConnectionError,
            RuntimeError,
            TimeoutError,
            AttributeError,
        ) as exc:
            logger.warning(
                "Pool probe failed — attempting to evict dead connections: %s",
                exc,
            )
            try:
                remaining = await self._provider.evict_dead_connections()
                logger.info(
                    "Evicted dead connections; %d valid connections remaining",
                    remaining,
                )
            except AttributeError:
                pass  # Provider does not support eviction — best-effort only

    async def _collect_pool_metrics(self) -> None:
        """Collect current pool metrics"""
        if not self.pool:
            return

        try:
            # Get pool statistics - these are typical attributes for SQLAlchemy pools
            active = getattr(self.pool, "_active_connections", 0)
            total = getattr(self.pool, "_total_connections", 0)

            # Ensure we have numeric values before proceeding
            # (especially important for tests using MagicMocks)
            try:
                active = int(active)
                total = int(total)
            except (TypeError, ValueError):
                active = 0
                total = 0

            available = total - active
            checked_out = active
            checked_in = available

            # Calculate utilization
            utilization = active / total if total > 0 else 0.0

            # Record metrics
            metrics = ConnectionMetrics(
                active_connections=active,
                total_connections=total,
                available_connections=available,
                checked_out_connections=checked_out,
                checked_in_connections=checked_in,
                utilization=utilization,
                timestamp=self._get_datetime(),
            )

            await self.collector.record_connection_metrics(metrics)

        except (
            DatabaseError,
            DatabaseConnectionError,
            OSError,
            ConnectionError,
            RuntimeError,
            TimeoutError,
        ):
            logger.exception("Error collecting pool metrics")

    async def get_stats(self, time_range_seconds: int = 3600) -> dict[str, Any]:
        """Get connection pool monitoring statistics"""
        return await self.collector.get_connection_stats(time_range_seconds)


class DatabaseMonitor:
    """Comprehensive database monitoring"""

    def __init__(
        self,
        collector: DbMetricsCollector | None = None,
        slow_query_threshold: float = 1.0,
    ):
        from lexigram.sql.monitoring.metrics import (
            InMemoryDbMetricsCollector,
        )

        self.collector = collector or InMemoryDbMetricsCollector()
        self.query_monitor = QueryMonitor(self.collector, slow_query_threshold)
        self.pool_monitor = ConnectionPoolMonitor(self.collector)
        self.transaction_monitor = TransactionMonitor(self.collector)
        self.health_checker = DatabaseHealthChecker(self.collector)

    def _get_datetime(self) -> datetime:
        """Get current datetime."""
        return ambient_clock.now()

    async def start_pool_monitoring(
        self,
        pool: Any,
        provider: Any | None = None,
    ) -> None:
        """Start monitoring a connection pool.

        Args:
            pool: The pool or provider object to monitor.
            provider: Optional provider used for active ``SELECT 1`` probing.
                When omitted, the pool itself is used as the provider only if
                it exposes ``scoped_context()``.
        """
        probe_provider = provider
        if probe_provider is None and hasattr(pool, "scoped_context"):
            probe_provider = pool
        await self.pool_monitor.start_monitoring(pool, probe_provider)

    async def stop_pool_monitoring(self) -> None:
        """Stop pool monitoring"""
        await self.pool_monitor.stop_monitoring()

    def get_query_monitor(self) -> QueryMonitor:
        """Get the query monitor"""
        return self.query_monitor

    def get_transaction_monitor(self) -> TransactionMonitor:
        """Get the transaction monitor"""
        return self.transaction_monitor

    def get_health_checker(self) -> DatabaseHealthChecker:
        """Get the health checker"""
        return self.health_checker

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive monitoring statistics"""
        query_stats = await self.query_monitor.get_stats()
        connection_stats = await self.collector.get_connection_stats()
        transaction_stats = await self.transaction_monitor.get_stats()

        return {
            "query_stats": query_stats,
            "connection_stats": connection_stats,
            "transaction_stats": transaction_stats,
            "timestamp": self._get_datetime(),
        }

    async def perform_health_check(
        self,
        connection_string: str,
        pool: Any = None,
    ) -> dict[str, Any]:
        """Perform comprehensive health check"""
        health_checks = []

        # Database connectivity check
        db_health = await self.health_checker.check_database_health(connection_string)
        health_checks.append(db_health)

        # Connection pool check (if pool provided)
        if pool:
            pool_health = await self.health_checker.check_connection_pool_health(pool)
            health_checks.append(pool_health)

        # Performance checks
        perf_checks = await self.health_checker.check_performance_health()
        health_checks.extend(perf_checks)

        # Aggregate status

        statuses = [check.status for check in health_checks]
        if "critical" in statuses:
            overall_status = "critical"
        elif "warning" in statuses:
            overall_status = "warning"
        elif "healthy" in statuses:
            overall_status = "healthy"
        else:
            overall_status = "unknown"

        return {
            "overall_status": overall_status,
            "checks": [
                {
                    "component": check.component,
                    "status": check.status,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details,
                }
                for check in health_checks
            ],
            "timestamp": self._get_datetime().isoformat(),
        }
