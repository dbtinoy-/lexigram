"""GraphQL query tracing.

This module provides tracing support for GraphQL queries,
including resolver timing and execution path tracking.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
import functools
import time
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast

from strawberry.extensions import SchemaExtension

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.observability.tracing import SpanProtocol, TracerProtocol

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class TraceSpan:
    """A span in the execution trace.

    Attributes:
        name: Span name.
        start_time: Start timestamp.
        end_time: End timestamp.
        duration_ms: Duration in milliseconds.
        metadata: Additional span metadata.
        children: Child spans.
    """

    name: str
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list[TraceSpan] = field(default_factory=list)

    def end(self) -> None:
        """End the span and calculate duration."""
        self.end_time = datetime.now(UTC)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def add_child(self, child: TraceSpan) -> None:
        """Add a child span."""
        self.children.append(child)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": round(self.duration_ms, 3),
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class ExecutionTrace:
    """Complete execution trace.

    Attributes:
        operation_name: Name of the operation.
        start_time: Execution start time.
        end_time: Execution end time.
        total_duration_ms: Total duration.
        root_span: Root span of the trace.
        resolver_count: Number of resolvers called.
    """

    operation_name: str | None = None
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    total_duration_ms: float = 0.0
    root_span: TraceSpan | None = None
    resolver_count: int = 0

    def end(self) -> None:
        """End the trace."""
        self.end_time = datetime.now(UTC)
        self.total_duration_ms = (
            self.end_time - self.start_time
        ).total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation (Apollo tracing format).
        """
        return {
            "version": 1,
            "startTime": self.start_time.isoformat(),
            "endTime": self.end_time.isoformat() if self.end_time else None,
            "duration": int(self.total_duration_ms * 1_000_000),  # nanoseconds
            "execution": {
                "resolvers": self.root_span.to_dict() if self.root_span else {},
            },
        }


class TracingExtension(SchemaExtension):
    """Strawberry extension for query tracing.

    Adds tracing information to query responses in Apollo
    tracing format.

    Example:
        ```python
        from lexigram.graphql.monitoring import TracingExtension

        schema = strawberry.Schema(
            query=Query,
            extensions=[TracingExtension()],
        )
        ```
    """

    def __init__(
        self,
        include_in_response: bool = True,
        tracer: TracerProtocol | None = None,
    ) -> None:
        """Initialize the extension.

        Args:
            include_in_response: Include tracing in response extensions.
            tracer: Optional kernel TracerProtocol for unified distributed tracing.
                When provided, GraphQL operation and resolver spans are forwarded
                to the application-wide tracing pipeline so GraphQL telemetry is
                correlated with infra traces.
        """
        self._include_in_response = include_in_response
        self._tracer: TracerProtocol | None = tracer
        self._trace: ExecutionTrace | None = None
        self._current_span: TraceSpan | None = None
        self._kernel_root_span: SpanProtocol | None = None

    def on_operation(self) -> Iterator[None]:
        """Hook called during operation execution."""
        execution_context = self.execution_context

        # Start kernel-level span for unified distributed tracing
        if self._tracer is not None:
            self._kernel_root_span = self._tracer.start_span(
                "graphql.operation",
                attributes={
                    "operation_name": execution_context.operation_name or "",
                    "graphql.type": "operation",
                },
            )

        # Start trace
        self._trace = ExecutionTrace(
            operation_name=execution_context.operation_name,
        )
        self._trace.root_span = TraceSpan(name="operation")
        self._current_span = self._trace.root_span

        yield

        # End trace
        if self._trace:
            self._trace.root_span.end()
            self._trace.end()

            # Add to response extensions
            if self._include_in_response and execution_context.result:
                if not execution_context.result.extensions:
                    execution_context.result.extensions = {}
                execution_context.result.extensions["tracing"] = self._trace.to_dict()

        # Close kernel span
        if self._kernel_root_span is not None:
            has_errors = bool(
                execution_context.result and execution_context.result.errors
            )
            self._kernel_root_span.set_status("ERROR" if has_errors else "OK")
            self._kernel_root_span = None

    def resolve(
        self,
        _next: Callable[..., Any],
        root: Any,
        info: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Hook called during field resolution."""
        if self._trace:
            self._trace.resolver_count += 1

        # Create span for resolver
        field_name = info.field_name if hasattr(info, "field_name") else "unknown"
        parent_type: str | None = (
            info.parent_type.name
            if hasattr(info, "parent_type") and info.parent_type
            else None
        )
        return_type: str | None = (
            str(info.return_type) if hasattr(info, "return_type") else None
        )
        span = TraceSpan(
            name=field_name,
            metadata={
                "parentType": parent_type,
                "returnType": return_type,
            },
        )

        # Add as child of current span
        if self._current_span:
            self._current_span.add_child(span)

        # Forward to kernel tracer for distributed tracing correlation
        kernel_span: SpanProtocol | None = None
        if self._tracer is not None:
            kernel_span = self._tracer.start_span(
                f"graphql.resolve.{field_name}",
                attributes={
                    "field_name": field_name,
                    "parent_type": parent_type or "",
                    "return_type": return_type or "",
                },
            )

        try:
            return _next(root, info, *args, **kwargs)
        except Exception as _trace_err:  # noqa: BLE001 — tracing wrapper must capture any error to mark the span before re-raising
            if kernel_span is not None:
                kernel_span.set_status("ERROR")
            raise
        finally:
            span.end()
            if kernel_span is not None:
                kernel_span.set_status("OK")


def trace_resolver(
    name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for tracing resolver execution.

    Args:
        name: Optional span name.

    Returns:
        Decorator function.

    Example:
        ```python
        @strawberry.type
        class Query:
            @trace_resolver("fetch_user")
            @strawberry.field
            async def user(self, info: Info, id: str) -> User:
                return await get_user(id)
        ```
    """

    def decorator(func: Callable[P, T]) -> Callable[P, Any]:
        span_name = name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            try:
                # Support coroutine functions but allow mypy to understand
                # that result could be awaitable or a direct value.
                result = func(*args, **kwargs)
                if isinstance(result, Awaitable):
                    return cast("T", await result)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                logger.debug("ResolverProtocol %s took %.2fms", span_name, duration_ms)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.time() - start_time) * 1000
                logger.debug("ResolverProtocol %s took %.2fms", span_name, duration_ms)

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


__all__ = [
    "ExecutionTrace",
    "TraceSpan",
    "TracingExtension",
    "trace_resolver",
]
