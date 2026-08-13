"""GraphQL query execution.

This module provides the core execution engine for GraphQL queries,
mutations, and subscriptions using Strawberry GraphQL.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar

from lexigram.graphql.config import ErrorConfig
from lexigram.graphql.core.context import (
    GraphQLContext,
    GraphQLRequest,
    GraphQLResponse,
)
from lexigram.graphql.core.error_formatter import ErrorFormatter
from lexigram.graphql.events import (
    AfterExecuteEvent,
    BeforeExecuteEvent,
    OnErrorEvent,
)
from lexigram.graphql.exceptions import (
    ExecutionError,
    GraphQLError,
    GraphQLTimeoutError,
)
from lexigram.graphql.types import CacheControl, OperationType, QueryMetrics
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from strawberry import Schema as StrawberrySchema

    from lexigram.contracts.events import EventBusProtocol
    from lexigram.result import Result

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class ExecutionContextProtocol:
    """Context for a single query execution.

    Tracks execution state, metrics, and provides hooks
    for middleware and extensions.

    Attributes:
        context: The GraphQL context.
        operation_type: Type of operation being executed.
        start_time: Execution start time.
        end_time: Execution end time.
        errors: Errors encountered during execution.
        extensions: Execution extensions data.
    """

    context: GraphQLContext
    operation_type: OperationType = OperationType.QUERY
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    errors: list[Exception] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)

    def mark_complete(self) -> None:
        """Mark execution as complete."""
        self.end_time = datetime.now(UTC)

    @property
    def duration_ms(self) -> float:
        """Get execution duration in milliseconds."""
        end = self.end_time or datetime.now(UTC)
        return (end - self.start_time).total_seconds() * 1000

    def add_error(self, error: Exception) -> None:
        """Add an error to the execution context."""
        self.errors.append(error)

    @property
    def has_errors(self) -> bool:
        """Check if execution has errors."""
        return len(self.errors) > 0


class GraphQLExecutorProtocol:
    """GraphQL query executor.

    Provides a high-level interface for executing GraphQL
    operations with proper error handling, timeout support,
    and metrics collection.

    Example:
        ```python
        from strawberry import Schema
        from lexigram.graphql.core import GraphQLExecutorProtocol

        schema = Schema(query=Query)
        executor = GraphQLExecutorProtocol(schema)

        response = await executor.execute(
            query="{ hello }",
            variables={},
        )
        ```
    """

    def __init__(
        self,
        schema: StrawberrySchema,
        timeout_secs: float | None = None,
        middleware: list[Callable[..., Any]] | None = None,
        error_config: ErrorConfig | None = None,
        event_bus: EventBusProtocol | None = None,
    ) -> None:
        """Initialize the executor.

        Args:
            schema: Strawberry GraphQL schema.
            timeout_secs: Default timeout in seconds.
            middleware: List of middleware functions.
            error_config: Error configuration for formatting.
            event_bus: Optional EventBusProtocol for lifecycle event publishing.
                Subscribers receive :class:`~lexigram.graphql.events.BeforeExecuteEvent`,
                :class:`~lexigram.graphql.events.AfterExecuteEvent`, and
                :class:`~lexigram.graphql.events.OnErrorEvent`.
        """
        self._schema = schema
        self._timeout = timeout_secs
        self._middleware = middleware or []
        self._error_formatter = ErrorFormatter(error_config or ErrorConfig())
        self._event_bus = event_bus

    @property
    def schema(self) -> StrawberrySchema:
        """Get the GraphQL schema."""
        return self._schema

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
        context: GraphQLContext | None = None,
        timeout_secs: float | None = None,
    ) -> Result[GraphQLResponse[Any], GraphQLError]:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string.
            variables: Query variables.
            operation_name: Operation name to execute.
            context: GraphQL context.  Use :meth:`ContextFactory.from_dict`
                to convert a plain dictionary before passing it here.
            timeout: Timeout in seconds (overrides default).

        Returns:
            ``Ok(GraphQLResponse)`` or ``Err(GraphQLError)`` when execution
            failed.

        Raises:
            None: Infrastructure errors are wrapped in ``Err``.
        """
        from lexigram.result import Err, Ok

        # Create request and context
        request = GraphQLRequest(
            query=query,
            variables=variables or {},
            operation_name=operation_name,
        )

        if context is None:
            context = GraphQLContext(request=request)
        else:
            context.request = request

        execution_context = ExecutionContextProtocol(context=context)

        if self._event_bus is not None:
            await self._event_bus.publish(
                BeforeExecuteEvent(execution_context=execution_context),
            )

        try:
            # Execute with timeout using lexigram timeout utilities (e.g., timeout context)
            effective_timeout = timeout_secs or self._timeout

            if effective_timeout:
                # Enforce timeout using asyncio.wait_for to avoid relying on
                # external context manager implementations.
                result = await asyncio.wait_for(
                    self._execute_internal(execution_context),
                    timeout=effective_timeout,
                )
            else:
                result = await self._execute_internal(execution_context)

            execution_context.mark_complete()

            if self._event_bus is not None:
                await self._event_bus.publish(
                    AfterExecuteEvent(
                        execution_context=execution_context, result=result
                    ),
                )

            return Ok(result)

        except TimeoutError as e:
            execution_context.add_error(e)
            if self._event_bus is not None:
                await self._event_bus.publish(
                    OnErrorEvent(execution_context=execution_context, error=e),
                )
            return Err(
                GraphQLTimeoutError(
                    f"Query execution timed out after {effective_timeout}s",
                )
            )

        except (RuntimeError, ValueError, TypeError, LookupError) as e:
            execution_context.add_error(e)
            if self._event_bus is not None:
                await self._event_bus.publish(
                    OnErrorEvent(execution_context=execution_context, error=e),
                )
            if isinstance(e, GraphQLError):
                return Err(e)
            return Err(ExecutionError(str(e)))

        finally:
            # Release any scoped DI services created for this request.
            if context is not None:
                await context.dispose_scope()

    async def _execute_internal(
        self,
        execution_context: ExecutionContextProtocol,
    ) -> GraphQLResponse[Any]:
        """Internal execution logic.

        Args:
            execution_context: Execution context.

        Returns:
            GraphQL response.
        """
        context = execution_context.context
        request = context.request

        if request is None:
            raise ExecutionError("No request in context")

        try:
            # Execute via Strawberry
            logger.debug(
                "Schema type: %s, has execute: %s",
                type(self._schema),
                hasattr(self._schema, "execute"),
            )
            result = await self._schema.execute(
                query=request.query,
                variable_values=request.variables,
                operation_name=request.operation_name,
                context_value=context,
            )

            # Build response
            response: GraphQLResponse[Any] = GraphQLResponse(
                data=result.data,
                extensions=result.extensions or {},
            )

            # Convert and format errors using ErrorFormatter
            if result.errors:
                request_id = getattr(context, "request_id", None)
                for error in result.errors:
                    # Try to unwrap the original error from Strawberry/graphql-core's wrapper.
                    # Graphql-core wraps resolver exceptions in its own GraphQLError;
                    # the original may carry safe/code attributes we want to preserve.
                    effective_error: Any = error
                    original = getattr(error, "original_error", None)
                    if original is not None:
                        if isinstance(original, GraphQLError):
                            effective_error = original
                        else:
                            # DomainError subclasses (e.g. AuthenticationError from contracts)
                            # aren't Lexigram GraphQLErrors but have safe user-facing messages.
                            # Wrap them in a transient GraphQLError so format_error sees them.
                            from lexigram.graphql.exceptions import (
                                GraphQLError as LexigramGraphQLError,
                            )

                            effective_error = LexigramGraphQLError(str(original))
                            effective_error.safe = True
                    formatted = self._error_formatter.format_error(effective_error)
                    # Thread request_id into extensions (cross-cutting concern via context)
                    if request_id:
                        if "extensions" not in formatted:
                            formatted["extensions"] = {}
                        formatted["extensions"]["requestId"] = request_id
                    response.add_error(
                        message=formatted.get("message", str(effective_error)),
                        path=list(error.path) if error.path else None,
                        extensions=formatted.get("extensions", error.extensions or {}),
                    )

            # Set Cache-Control and Vary headers when caching is enabled
            cfg = getattr(context, "config", None)
            if cfg is not None and cfg.cache.enabled and not response.has_errors:
                cache_header = CacheControl(
                    max_age=cfg.cache.default_max_age,
                    scope=cfg.cache.default_scope,
                ).to_header()
                response.http_headers["Cache-Control"] = cache_header
                if cfg.cache.vary_headers:
                    response.http_headers["Vary"] = ", ".join(cfg.cache.vary_headers)

            return response

        except GraphQLError as e:
            logger.warning("GraphQL error during execution", error=str(e))
            formatted = self._error_formatter.format_error(e)
            response = GraphQLResponse(data=None, extensions={})
            response.add_error(
                message=formatted.get("message", str(e)),
                path=formatted.get("path"),
                extensions=formatted.get("extensions", {}),
            )
            return response

        except Exception as e:  # noqa: BLE001 — execution engine wraps all errors into ExecutionError to normalise failure responses
            logger.exception("Execution error")
            raise ExecutionError(f"Query execution failed: {e}") from e

    def get_metrics(
        self,
        execution_context: ExecutionContextProtocol,
    ) -> QueryMetrics:
        """Get execution metrics.

        Args:
            execution_context: Execution context.

        Returns:
            Query metrics.
        """
        context = execution_context.context
        query = context.request.query if context.request else ""

        return QueryMetrics(
            duration_ms=execution_context.duration_ms,
            depth=0,  # Would need depth analyzer
            complexity=0,  # Would need complexity analyzer
        )


async def execute_query(
    schema: StrawberrySchema,
    query: str,
    variables: dict[str, Any] | None = None,
    operation_name: str | None = None,
    context: GraphQLContext | None = None,
) -> GraphQLResponse[Any]:
    """Execute a GraphQL query (convenience function).

    If you need to build a context from a plain dictionary, use
    ``ContextFactory.from_dict()`` before calling this function.

    Args:
        schema: Strawberry GraphQL schema.
        query: GraphQL query string.
        variables: Query variables.
        operation_name: Operation name.
        context: GraphQL context.

    Returns:
        GraphQL response.
    """
    executor = GraphQLExecutorProtocol(schema)
    result = await executor.execute(
        query=query,
        variables=variables,
        operation_name=operation_name,
        context=context,
    )
    if result.is_err():
        raise result.unwrap_err()
    return result.unwrap()


__all__ = ["ExecutionContextProtocol", "GraphQLExecutorProtocol", "execute_query"]
