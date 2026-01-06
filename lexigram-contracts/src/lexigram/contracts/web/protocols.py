"""HTTP web protocol definitions.

Structural protocols for the HTTP request/response lifecycle, middleware,
rate limiting, exception filtering, and web provider integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from lexigram.contracts.core.middleware import (
    ExceptionFilterChainProtocol as ExceptionFilterChainProtocol,
)
from lexigram.contracts.core.provider import ProviderProtocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import datetime

    from lexigram.contracts.core.result import Result
    from lexigram.contracts.exceptions.domain import DomainError

T = TypeVar("T")

C = TypeVar("C")


@runtime_checkable
class HttpRequestLoggerProtocol(Protocol):
    """Protocol for HTTP request/response logging middleware.

    Defines how to log completed HTTP requests with duration, status code,
    and optional metadata for monitoring and audit purposes.

    Example:
        ```python
        class RequestLogger:
            async def log_request(
                self,
                method: str,
                path: str,
                status_code: int,
                duration_ms: float,
                request_id: str | None = None,
                **metadata: Any,
            ) -> None:
                logger.info(
                    "request_completed",
                    method=method,
                    path=path,
                    status=status_code,
                    duration_ms=duration_ms,
                    request_id=request_id,
                    **metadata,
                )
        ```
    """

    async def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str | None = None,
        **metadata: Any,
    ) -> None:
        """Log a completed HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: Request path URI.
            status_code: HTTP response status code.
            duration_ms: Request processing duration in milliseconds.
            request_id: Optional request identifier for tracing.
            **metadata: Additional context-specific data (client_id, user_id, etc.).
        """
        ...


@runtime_checkable
class CORSPolicyProtocol(Protocol):
    """Protocol for CORS (Cross-Origin Resource Sharing) policy configuration.

    Defines how to evaluate CORS requests and provide the necessary headers
    and configuration for browser-based clients.

    Example:
        ```python
        class CORSPolicy:
            def is_origin_allowed(self, origin: str) -> bool:
                return origin in ("https://app.example.com", "https://admin.example.com")

            def get_allowed_headers(self) -> list[str]:
                return ["content-type", "authorization", "x-request-id"]

            def get_allowed_methods(self) -> list[str]:
                return ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

            def get_max_age(self) -> int:
                return 3600
        ```
    """

    def is_origin_allowed(self, origin: str) -> bool:
        """Check if an origin is permitted for CORS requests.

        Args:
            origin: The value of the Origin header from a CORS preflight request.

        Returns:
            True if the origin is allowed, False otherwise.
        """
        ...

    def get_allowed_headers(self) -> list[str]:
        """Return the list of allowed request headers.

        Returns:
            List of header names that clients are allowed to send.
            Common values: ["content-type", "authorization", "x-request-id"].
        """
        ...

    def get_allowed_methods(self) -> list[str]:
        """Return the list of allowed HTTP methods.

        Returns:
            List of HTTP methods clients are allowed to use.
            Typical: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"].
        """
        ...

    def get_max_age(self) -> int:
        """Return the preflight cache duration in seconds.

        Returns:
            Maximum time (in seconds) browsers should cache preflight
            responses. Typical values: 3600 (1 hour) to 86400 (24 hours).
        """
        ...


__all__ = [
    "BackgroundTaskRunnerProtocol",
    "CORSPolicyProtocol",
    "CRUDServiceProtocol",
    "CSRFProtectionProtocol",
    "ConnectionManagerProtocol",
    "ExceptionFilterChainProtocol",
    "ExceptionFilterProtocol",
    "HTTPApplicationProtocol",
    "HttpRequestLoggerProtocol",
    "RequestProtocol",
    "ResponseFactoryProtocol",
    "ResponseProtocol",
    "WebContributorProtocol",
    "WebMiddlewareProtocol",
    "WebProviderProtocol",
    "WebRateLimiterProtocol",
]


@runtime_checkable
class BackgroundTaskRunnerProtocol(Protocol):
    """Protocol for in-process background task execution.

    Background tasks run after a response is sent to the client. This
    protocol models post-response callable execution inside the web layer.
    Durable job submission belongs to the task subsystem via
    ``TaskProviderProtocol`` / ``TaskQueueProtocol`` rather than this web
    background-runner contract.
    """

    def add_task(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Add a task to run in the background.

        Args:
            func: Async or sync callable to execute.
            *args: Positional arguments for the callable.
            **kwargs: Keyword arguments for the callable.
        """
        ...


@runtime_checkable
class CSRFProtectionProtocol(Protocol):
    """Protocol for CSRF (Cross-Site Request Forgery) protection.

    Validates that state-modifying requests (POST, PUT, PATCH, DELETE)
    include a valid CSRF token that matches the session cookie.

    This is essential for browser-based applications using session cookies.
    """

    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token for a session.

        Args:
            session_id: Unique session identifier.

        Returns:
            CSRF token string.
        """
        ...

    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate a CSRF token against a session.

        Args:
            token: CSRF token from request.
            session_id: Session identifier.

        Returns:
            True if token is valid for the session.
        """
        ...

    def get_cookie_name(self) -> str:
        """Get the name of the CSRF cookie.

        Returns:
            Cookie name (default: "csrf_token").
        """
        ...

    def get_header_name(self) -> str:
        """Get the name of the CSRF header.

        Returns:
            Header name (default: "X-CSRF-Token").
        """
        ...


@runtime_checkable
class WebRateLimiterProtocol(Protocol):
    """Protocol for web rate limiting.

    Handles rate limiting for HTTP requests based on various scopes.
    """

    async def check_rate_limit(
        self,
        request: Any,
        *,
        max_requests: int,
        window_seconds: int,
        scope: str = "user",
    ) -> None:
        """Check if request is within rate limit.

        Args:
            request: The incoming request.
            max_requests: Maximum requests per window.
            window_seconds: Time window in seconds.
            scope: Rate limit scope (user, ip, or endpoint).

        Raises:
            Exception: If rate limit exceeded.
        """
        ...


@runtime_checkable
class WebMiddlewareProtocol(Protocol):
    """Protocol for HTTP web middleware.

    WebMiddlewareProtocol intercepts HTTP requests and responses for cross-cutting
    concerns such as authentication, logging, CORS, and compression.

    This is distinct from ``MiddlewareProtocol`` in ``contracts.middleware``
    which is transport-agnostic (events, commands, queries). WebMiddlewareProtocol is
    exclusively for the HTTP request/response lifecycle in ``lexigram-web``
    and compatible ASGI frameworks.

    Example::

        class LoggingMiddleware:
            async def __call__(self, request, call_next):
                start = time.monotonic()
                response = await call_next(request)
                logger.info("%s %s %.2fs", request.method, request.url, time.monotonic()-start)
                return response
    """

    async def __call__(
        self,
        request: Any,
        call_next: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Process the HTTP request.

        Args:
            request: Incoming HTTP request.
            call_next: Callable to invoke the next middleware/handler.

        Returns:
            HTTP response.
        """
        ...


@runtime_checkable
class ExceptionFilterProtocol(Protocol):
    """Protocol for exception handling filters.

    Exception filters convert exceptions to HTTP responses.

    Example:
        ```python
        class ValidationExceptionFilter:
            def can_handle(self, exc):
                return isinstance(exc, ValidationError)

            def handle(self, exc, request):
                return JSONResponse(
                    {"errors": exc.errors()},
                    status_code=422,
                )
        ```
    """

    def can_handle(self, exc: Exception) -> bool:
        """Check if this filter handles the exception.

        Args:
            exc: Exception to check.

        Returns:
            True if this filter can handle the exception.
        """
        ...

    def handle(self, exc: Exception, request: Any) -> Any:
        """Convert exception to a response.

        Args:
            exc: Exception to handle.
            request: Original request.

        Returns:
            HTTP response.
        """
        ...


@runtime_checkable
class RequestProtocol(Protocol):
    """Protocol for HTTP requests."""

    url: Any
    method: str
    headers: Any
    path_params: dict[str, Any]
    query_params: Any
    cookies: Any
    state: Any
    user: Any
    auth: Any

    async def json(self) -> Any: ...

    async def body(self) -> bytes: ...


@runtime_checkable
class ResponseProtocol(Protocol):
    """Protocol for HTTP responses."""

    status_code: int
    headers: Any
    body: bytes
    media_type: str | None
    background: Any | None

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: int | None = None,
        expires: int | datetime | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str = "lax",
    ) -> None: ...

    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: str | None = None,
    ) -> None: ...


@runtime_checkable
class ResponseFactoryProtocol(Protocol):
    """Protocol for creating HTTP responses.

    Abstracts response creation to avoid hard dependencies on specific
    web frameworks (e.g., Starlette/FastAPI) in business logic or middleware.
    """

    def json(
        self,
        content: Any,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> ResponseProtocol:
        """Create a JSON response."""
        ...

    def html(
        self,
        content: str,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> ResponseProtocol:
        """Create an HTML response."""
        ...

    def redirect(
        self,
        url: str,
        status_code: int = 302,
        headers: dict[str, str] | None = None,
    ) -> ResponseProtocol:
        """Create a redirect response."""
        ...


@runtime_checkable
class WebProviderProtocol(ProviderProtocol, Protocol):
    """Protocol for web providers that provide HTTP routing and middleware.

    Web providers are responsible for setting up HTTP servers, routing,
    middleware, and request/response handling.
    """


@runtime_checkable
class HTTPApplicationProtocol(Protocol):
    """Minimal protocol for an ASGI-compatible HTTP application.

    Extension packages that need to mount sub-applications (e.g.
    ``lexigram-graphql`` mounting a ``/graphql`` endpoint) must depend on
    this protocol — NOT on ``lexigram-web`` — to avoid cross-extension imports.
    The web provider implements this protocol; the container resolves it.
    """

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        """ASGI callable entry-point.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive channel callable.
            send: ASGI send channel callable.
        """
        ...

    def mount(self, path: str, app: HTTPApplicationProtocol) -> None:
        """Mount a sub-application at the given path prefix.

        Args:
            path: URL path prefix (e.g. ``"/api/v2"``).
            app: The application to mount.
        """
        ...

    def add_route(
        self,
        path: str,
        handler: Any,
        methods: list[str] | None = None,
    ) -> None:
        """Register a route handler.

        Args:
            path: URL path pattern.
            handler: Callable (sync or async) that handles matched requests.
            methods: Allowed HTTP methods; ``None`` means all methods.
        """
        ...

    def add_middleware(self, middleware: Any) -> None:
        """Register a middleware layer.

        Middleware is applied in reverse registration order (last registered
        is the innermost layer).

        Args:
            middleware: A middleware class or instance.
        """
        ...


@runtime_checkable
class CRUDServiceProtocol(Protocol[T]):
    """Protocol for services that implement basic CRUD operations."""

    async def list_items(
        self, limit: int = 20, offset: int = 0, **filters: Any
    ) -> Result[list[T], DomainError]:
        """List items with pagination and filters."""
        ...

    async def get(self, item_id: Any) -> Result[T | None, DomainError]:
        """Get single item by ID."""
        ...

    async def create(self, data: dict[str, Any]) -> Result[T, DomainError]:
        """Create new item."""
        ...

    async def update(
        self, item_id: Any, data: dict[str, Any]
    ) -> Result[T | None, DomainError]:
        """Update existing item."""
        ...

    async def delete(self, item_id: Any) -> Result[bool, DomainError]:
        """Delete item."""
        ...


@runtime_checkable
class ConnectionManagerProtocol(Protocol[C]):  # type: ignore[misc]
    """Protocol for connection managers that track and broadcast to clients.

    Both WebSocket and SSE handlers manage connections; this protocol
    captures the shared surface so higher-level code can depend on the
    abstraction rather than a concrete transport.
    """

    async def add(self, connection: C) -> None:
        """Register a new connection."""
        ...

    async def remove(self, connection: C) -> None:
        """Unregister a connection."""
        ...

    async def broadcast(self, message: Any, exclude: C | None = None) -> None:
        """Send a message to all tracked connections."""
        ...

    @property
    def count(self) -> int:
        """Return the number of active connections."""
        ...


@runtime_checkable
class WebContributorProtocol(Protocol):
    """Protocol for packages that contribute controllers and middleware.

    Extension packages can also mount sub-applications via the mount_to_app hook.

    Extension packages can implement this protocol to register their HTTP
    controllers and middleware components with the web provider via
    entry-point discovery. This allows packages like ``lexigram-graphql``
    and ``lexigram-admin`` to expose web routes without requiring the
    web provider to explicitly import them.

    Example:
        ```python
        class GraphQLWebContributor:
            @property
            def contributor_id(self) -> str:
                return "graphql"

            def get_controllers(self) -> list[type]:
                return [GraphQLController]

            def get_middleware(self) -> list[type]:
                return []

            async def mount_to_app(
                self, app: HTTPApplicationProtocol, container: object
            ) -> None:
                pass  # No-op for controller-only contributors
        ```
    """

    @property
    def contributor_id(self) -> str:
        """Unique contributor identifier such as ``graphql`` or ``admin``.

        Returns:
            A string identifier for this contributor, used for tracking
            and debugging. Must be unique across all registered contributors.
        """
        ...

    def get_controllers(self) -> list[type[Any]]:
        """Return controller classes contributed by the package.

        Returns:
            List of controller classes to register with the web provider.
            Each class should implement the controller contract with
            route definitions.
        """
        ...

    def get_middleware(self) -> list[type[Any]]:
        """Return middleware classes contributed by the package.

        Returns:
            List of middleware classes to register with the web provider.
            Middleware is applied in registration order.
        """
        ...

    async def mount_to_app(self, app: Any, container: object) -> None:
        """Mount sub-applications or additional routes to the web app.

        Called during route setup phase after metrics and debug routes
        but before static files and controller discovery.

        Args:
            app: The ASGI application (typically Starlette) to mount routes on.
            container: The DI container for resolving dependencies.

        Note:
            Controller-only contributors should implement this as a no-op.
        """
