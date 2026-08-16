"""GraphQL execution middleware pipeline.

This module provides middleware support for GraphQL execution,
enabling cross-cutting concerns like logging, auth, and metrics.

**Why GraphQL middleware is intentionally distinct from HTTP middleware**
------------------------------------------------------------------------

The HTTP/ASGI middleware contract (``lexigram.contracts.web.middleware.Middleware``)
operates at the ASGI transport layer — it receives raw ``scope``/``receive``/``send``
arguments and wraps the full HTTP connection.

GraphQL middleware here operates at the **GraphQL execution layer** — it wraps
individual *field resolution or operation execution* callbacks.  The concerns and
signatures are fundamentally different:

- HTTP middleware: ``(scope, receive, send) → None``
- GraphQL middleware: ``(context, next_handler) → response``

Aligning them into a single protocol would force an artificial abstraction and
couple ``lexigram-graphql`` to ASGI internals.  They are therefore intentionally
separate.

If you need to apply cross-cutting HTTP logic to the GraphQL endpoint (e.g.,
auth, rate-limiting, request-id injection), do so via the HTTP middleware stack
configured in ``WebProvider``.  Use ``GraphQLMiddleware`` only for logic that
needs access to the parsed GraphQL operation (query, variables, context).
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

# Type variable for generic middleware
T = TypeVar("T")


@dataclass
class MiddlewareResult:
    """Result of middleware processing.

    Attributes:
        response: The GraphQL response (if middleware handled it).
        skipped: Whether the middleware skipped processing.
        error: Any error that occurred.
    """

    response: Any = None
    skipped: bool = False
    error: Exception | None = None


class GraphQLMiddleware(Protocol):
    """Protocol for GraphQL middleware.

    Middleware can inspect, modify, or short-circuit GraphQL requests.
    """

    async def process(
        self,
        context: Any,
        next_handler: Callable[..., Any],
    ) -> Any:
        """Process a GraphQL operation.

        Args:
            context: The execution context.
            next_handler: The next handler in the chain.

        Returns:
            GraphQL response.
        """
        ...


class AbstractMiddleware(ABC):
    """Abstract base class for GraphQL middleware.

    Provides common functionality for middleware implementations.
    """

    def __init__(self, enabled: bool = True):
        """Initialize the middleware.

        Args:
            enabled: Whether this middleware is enabled.
        """
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        """Check if middleware is enabled."""
        return self._enabled

    async def process(
        self,
        context: Any,
        next_handler: Callable[..., Any],
    ) -> Any:
        """Process a GraphQL operation.

        Default implementation just calls the next handler.
        Subclasses should override to add custom logic.
        """
        return await next_handler(context)


class LoggingMiddleware(AbstractMiddleware):
    """Middleware for logging GraphQL operations.

    Logs request and response information.
    """

    def __init__(
        self,
        enabled: bool = True,
        log_variables: bool = False,
    ):
        """Initialize the logging middleware.

        Args:
            enabled: Whether logging is enabled.
            log_variables: Whether to log query variables.
        """
        super().__init__(enabled)
        self._log_variables = log_variables

    async def process(
        self,
        context: Any,
        next_handler: Callable[..., Any],
    ) -> Any:
        """Process and log GraphQL operation."""
        if not self._enabled:
            return await next_handler(context)

        request = getattr(context, "request", None)
        query = getattr(request, "query", "") if request else "unknown"

        # Log request
        logger.debug(
            "GraphQL request: %s",
            query[:100] + "..." if len(query) > 100 else query,
        )

        # Execute
        try:
            response = await next_handler(context)
            logger.debug("GraphQL response: success")
            return response
        except Exception as _gql_err:  # noqa: BLE001 — middleware must intercept any exception for logging before re-raising
            logger.exception("GraphQL request failed")
            raise


class AuthMiddleware(AbstractMiddleware):
    """Middleware for authentication/authorization.

    Validates user authentication before execution.
    """

    def __init__(
        self,
        enabled: bool = True,
        require_auth: bool = False,
    ):
        """Initialize the auth middleware.

        Args:
            enabled: Whether auth is enabled.
            require_auth: Whether authentication is required.
        """
        super().__init__(enabled)
        self._require_auth = require_auth

    async def process(
        self,
        context: Any,
        next_handler: Callable[..., Any],
    ) -> Any:
        """Process authentication check."""
        if not self._enabled:
            return await next_handler(context)

        # Check for user in context
        user = getattr(context, "user", None)

        if self._require_auth and user is None:
            from lexigram.graphql.exceptions import AuthenticationError

            raise AuthenticationError("Authentication required")

        return await next_handler(context)


class MetricsMiddleware(AbstractMiddleware):
    """Middleware for collecting execution metrics.

    Tracks execution time and other metrics.
    """

    def __init__(self, enabled: bool = True):
        """Initialize the metrics middleware."""
        super().__init__(enabled)
        self._metrics: dict[str, Any] = {}

    async def process(
        self,
        context: Any,
        next_handler: Callable[..., Any],
    ) -> Any:
        """Process and collect metrics."""
        if not self._enabled:
            return await next_handler(context)

        import time

        start = time.perf_counter()

        try:
            response = await next_handler(context)
            duration = time.perf_counter() - start

            # Record metrics
            self._metrics["total_requests"] = self._metrics.get("total_requests", 0) + 1
            self._metrics["total_time"] = self._metrics.get("total_time", 0) + duration

            return response
        except Exception as _metrics_err:  # noqa: BLE001 — metrics middleware must capture any error to track error count before re-raising
            self._metrics["total_errors"] = self._metrics.get("total_errors", 0) + 1
            raise

    def get_metrics(self) -> dict[str, Any]:
        """Get collected metrics."""
        return self._metrics.copy()


class MiddlewarePipeline:
    """Chain of middleware executed around GraphQL operations.

    Example:
        ```python
        pipeline = MiddlewarePipeline([
            LoggingMiddleware(),
            AuthMiddleware(),
            MetricsMiddleware(),
        ])

        response = await pipeline.execute(context, handler)
        ```
    """

    def __init__(self, middlewares: list[AbstractMiddleware] | None = None):
        """Initialize the pipeline.

        Args:
            middlewares: List of middleware to apply.
        """
        self._middlewares = middlewares or []

    def add(self, middleware: AbstractMiddleware) -> MiddlewarePipeline:
        """Add a middleware to the pipeline.

        Args:
            middleware: The middleware to add.

        Returns:
            Self for chaining.
        """
        self._middlewares.append(middleware)
        return self

    async def execute(
        self,
        context: Any,
        handler: Callable[..., Any],
    ) -> Any:
        """Execute the middleware pipeline.

        Args:
            context: Execution context.
            handler: Final handler to call.

        Returns:
            GraphQL response.
        """
        # Build the chain of handlers
        next_handler = handler

        # Reverse order so first middleware runs first
        for middleware in reversed(self._middlewares):
            if not middleware.enabled:
                continue

            current_middleware = middleware
            next_handler = lambda ctx, next=next_handler: current_middleware.process(
                ctx, next
            )

        # Execute the chain
        return await next_handler(context)


def create_middleware_pipeline(
    config: dict[str, bool] | None = None,
) -> MiddlewarePipeline:
    """Create a middleware pipeline from configuration.

    Args:
        config: Configuration dict with middleware settings.

    Returns:
        Configured MiddlewarePipeline.
    """
    config = config or {}

    pipeline = MiddlewarePipeline()

    if config.get("logging", True):
        pipeline.add(LoggingMiddleware())

    if config.get("auth", False):
        pipeline.add(AuthMiddleware(require_auth=config.get("require_auth", False)))

    if config.get("metrics", True):
        pipeline.add(MetricsMiddleware())

    return pipeline


__all__ = [
    "AbstractMiddleware",
    "AuthMiddleware",
    "GraphQLMiddleware",
    "LoggingMiddleware",
    "MetricsMiddleware",
    "MiddlewarePipeline",
    "MiddlewareResult",
    "create_middleware_pipeline",
]
