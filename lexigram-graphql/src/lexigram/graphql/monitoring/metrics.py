"""GraphQL metrics collection.

This module provides metrics collection for GraphQL queries,
including execution time, error rates, and operation counts.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
import time
from typing import TYPE_CHECKING, Any

from strawberry.extensions import SchemaExtension

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from lexigram.contracts.observability.metrics import MetricsRecorderProtocol


logger = get_logger(__name__)


@dataclass
class QueryStats:
    """Statistics for a single query execution.

    Attributes:
        operation_name: Name of the operation.
        operation_type: Type (query, mutation, subscription).
        start_time: Execution start time.
        end_time: Execution end time.
        duration_ms: Execution duration in milliseconds.
        success: Whether execution succeeded.
        error_count: Number of errors.
    """

    operation_name: str | None = None
    operation_type: str = "query"
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_ms: float = 0.0
    success: bool = True
    error_count: int = 0


@dataclass
class GraphQLMetrics:
    """Aggregated GraphQL metrics.

    Attributes:
        total_requests: Total number of requests.
        successful_requests: Number of successful requests.
        failed_requests: Number of failed requests.
        total_duration_ms: Total execution time.
        avg_duration_ms: Average execution time.
        operations_by_type: Count by operation type.
        operations_by_name: Count by operation name.
        errors_by_type: Error count by type.
    """

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    operations_by_type: dict[str, int] = field(default_factory=dict)
    operations_by_name: dict[str, int] = field(default_factory=dict)
    errors_by_type: dict[str, int] = field(default_factory=dict)

    def record_request(self, stats: QueryStats) -> None:
        """Record a request's statistics.

        Args:
            stats: Query statistics.
        """
        self.total_requests += 1
        self.total_duration_ms += stats.duration_ms

        if stats.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # Update operation type count
        op_type = stats.operation_type
        self.operations_by_type[op_type] = self.operations_by_type.get(op_type, 0) + 1

        # Update operation name count
        if stats.operation_name:
            self.operations_by_name[stats.operation_name] = (
                self.operations_by_name.get(stats.operation_name, 0) + 1
            )

        # Update average
        if self.total_requests > 0:
            self.avg_duration_ms = self.total_duration_ms / self.total_requests

    def record_error(self, error_type: str) -> None:
        """Record an error.

        Args:
            error_type: Type of error.
        """
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "success_rate": (
                round(self.successful_requests / self.total_requests * 100, 2)
                if self.total_requests > 0
                else 0.0
            ),
            "operations_by_type": dict(self.operations_by_type),
            "operations_by_name": dict(self.operations_by_name),
            "errors_by_type": dict(self.errors_by_type),
        }


class MetricsCollectorProtocol:
    """Collector for GraphQL metrics.

    Collects and aggregates metrics from GraphQL operations.  When a
    ``MetricsRecorderProtocol`` is provided (resolved from the DI container) every
    recorded query stat is forwarded to the kernel-level unified metrics
    pipeline so GraphQL telemetry lands alongside infra metrics.

    Example::

        from lexigram.contracts.observability.metrics import MetricsRecorderProtocol

        collector = MetricsCollectorProtocol(recorder=recorder)
        collector.record(QueryStats(operation_name="GetUser", duration_ms=50.0))
    """

    def __init__(
        self,
        max_history: int = 1000,
        recorder: MetricsRecorderProtocol | None = None,
    ) -> None:
        """Initialize the collector.

        Args:
            max_history: Maximum number of stats to keep in the rolling history.
            recorder: Optional kernel MetricsRecorderProtocol for unified observability.
        """
        self._max_history = max_history
        self._metrics = GraphQLMetrics()
        self._history: deque[QueryStats] = deque(maxlen=max_history)
        self._recorder = recorder

    def record(self, stats: QueryStats) -> None:
        """Record query statistics and forward to the kernel MetricsRecorderProtocol.

        Args:
            stats: Query statistics.
        """
        self._metrics.record_request(stats)

        # Keep history bounded — deque(maxlen) auto-evicts oldest entries
        self._history.append(stats)

        if self._recorder is not None:
            tags: dict[str, str] = {"operation_type": stats.operation_type}
            if stats.operation_name:
                tags["operation_name"] = stats.operation_name
            self._recorder.gauge("graphql.duration_ms", stats.duration_ms, tags=tags)
            self._recorder.increment("graphql.requests.total", tags=tags)
            if not stats.success:
                self._recorder.increment("graphql.requests.failed", tags=tags)

    def record_error(self, error: Exception) -> None:
        """Record an error.

        Args:
            error: The exception.
        """
        error_type = type(error).__name__
        self._metrics.record_error(error_type)

    def get_metrics(self) -> GraphQLMetrics:
        """Get current metrics.

        Returns:
            Current metrics.
        """
        return self._metrics

    def get_recent_stats(
        self,
        limit: int = 100,
    ) -> list[QueryStats]:
        """Get recent query statistics.

        Args:
            limit: Maximum number of stats to return.

        Returns:
            List of recent stats.
        """
        return list(self._history)[-limit:]

    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics = GraphQLMetrics()
        self._history.clear()

    async def close(self) -> None:
        """Async close hook for the collector (no-op).

        Provides symmetry with other resources that expose async close
        so callers can await shutdown without conditional checks.
        """
        # Currently a no-op; keep for API symmetry and future cleanup.
        self.reset()


async def get_metrics_collector(context: Any | None = None) -> MetricsCollectorProtocol:
    """Get the metrics collector instance."""
    from lexigram.di.resolution.context import get_resolver

    resolver = get_resolver(context)
    if resolver is None:
        raise ValueError("Could not find resolver")
    return await resolver.resolve(MetricsCollectorProtocol)


class MetricsExtension(SchemaExtension):
    """Strawberry extension for metrics collection.

    Automatically collects metrics for all GraphQL operations.

    Example:
        ```python
        from lexigram.graphql.monitoring import MetricsExtension

        schema = strawberry.Schema(
            query=Query,
            extensions=[MetricsExtension()],
        )
        ```
    """

    def __init__(
        self,
        collector: MetricsCollectorProtocol | None = None,
    ) -> None:
        """Initialize the extension.

        Args:
            collector: Metrics collector to use.
        """
        self._collector = collector
        self._start_time: float = 0

    async def on_operation(self) -> AsyncGenerator[None, None]:
        """Hook called during operation execution."""
        execution_context = self.execution_context

        if self._collector is None:
            # Resolve lazy
            self._collector = await get_metrics_collector(execution_context.context)

        # Record start time
        self._start_time = time.time()

        yield

        # Calculate duration
        duration_ms = (time.time() - self._start_time) * 1000

        # Get operation info
        operation_name = execution_context.operation_name
        operation_type = "query"

        if execution_context.graphql_document:
            for definition in execution_context.graphql_document.definitions:
                if hasattr(definition, "operation"):
                    operation_type = definition.operation.value
                    break

        # Check for errors
        result = execution_context.result
        success = True
        error_count = 0

        if result and hasattr(result, "errors") and result.errors:
            success = False
            error_count = len(result.errors)
            for error in result.errors:
                self._collector.record_error(Exception(str(error)))

        # Record stats
        stats = QueryStats(
            operation_name=operation_name,
            operation_type=operation_type,
            duration_ms=duration_ms,
            success=success,
            error_count=error_count,
        )
        self._collector.record(stats)


__all__ = [
    "GraphQLMetrics",
    "MetricsCollectorProtocol",
    "MetricsExtension",
    "QueryStats",
    "get_metrics_collector",
]
