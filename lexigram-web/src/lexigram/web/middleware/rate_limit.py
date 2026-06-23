"""Rate limiting middleware using Redis or CacheBackendProtocol.

Implements sliding window algorithm with per-user and per-IP limits.
Supports Redis (atomic Lua script), CacheBackendProtocol (fixed-window via get/set),
and in-memory (process-local, dev/test only).
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import TYPE_CHECKING, Any, Literal

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from lexigram.contracts.exceptions import RateLimitError
from lexigram.contracts.web import WebRateLimiterProtocol
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache import CacheBackendProtocol

logger = get_logger(__name__)


def _rate_limit_429_response(exc: Exception) -> JSONResponse:
    """Build the standard 429 response for a rate-limit breach.

    Args:
        exc: The :class:`~lexigram.contracts.exceptions.RateLimitError`.

    Returns:
        A 429 ``JSONResponse`` with a ``Retry-After`` header when the
        error carries a ``retry_after`` detail.
    """
    from starlette.responses import JSONResponse

    details = getattr(exc, "details", {}) or {}
    retry_after = details.get("retry_after")
    return JSONResponse(
        {"error": "rate_limit_exceeded", "message": str(exc)},
        status_code=429,
        headers={"Retry-After": str(retry_after)} if retry_after else {},
    )


class MemoryLimiter:
    """In-memory sliding window rate limiter for request tracking.

    This is a local implementation to avoid cross-package imports.
    """

    def __init__(
        self,
        window_size: float,
        max_requests: int,
    ) -> None:
        self.window_size = window_size
        self.max_requests = max_requests
        self._requests: deque[float] = deque()
        self._lock = asyncio.Lock()

    def _cleanup_old_requests(self) -> None:
        """Remove requests outside the current window."""
        now = ambient_clock.monotonic()
        cutoff = now - self.window_size
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    async def try_acquire(self) -> bool:
        """Try to acquire permission without blocking."""
        async with self._lock:
            self._cleanup_old_requests()
            if len(self._requests) < self.max_requests:
                self._requests.append(ambient_clock.monotonic())
                return True
            return False

    @property
    def current_requests(self) -> int:
        """Get current number of requests in the window."""
        self._cleanup_old_requests()
        return len(self._requests)


class CacheBackendLimiter:
    """Fixed-window rate limiter backed by any CacheBackendProtocol.

    Uses a fixed-window counter pattern: ``get`` → increment → ``set``.
    This is not atomic (race between get and set), but the window is short
    and the error margin is bounded to at most ``max_requests`` extra
    requests per process per window.  For strict distributed enforcement
    use the Redis-backed limiter instead.

    Args:
        cache: Any ``CacheBackendProtocol`` implementation (Redis, Memcached, …).
        window_size: Window duration in seconds.
        max_requests: Maximum requests allowed per window.
    """

    def __init__(
        self,
        cache: CacheBackendProtocol,
        window_size: float,
        max_requests: int,
    ) -> None:
        self._cache = cache
        self.window_size = window_size
        self.max_requests = max_requests

    async def try_acquire(self, key: str) -> tuple[bool, int]:
        """Attempt to acquire a rate-limit slot.

        Returns:
            Tuple of (allowed, remaining) where remaining is tokens left in
            the current window.
        """
        current_time = ambient_clock.timestamp()
        bucket = int(current_time // self.window_size)
        cache_key = f"rl:{key}:{bucket}"
        raw_result = await self._cache.get(cache_key)
        raw = raw_result.unwrap_or(None) if raw_result.is_ok() else None
        count: int = int(raw) if raw is not None else 0
        if count >= self.max_requests:
            return False, 0
        # Increment and reset TTL; not atomic but bounded error
        new_count = count + 1
        await self._cache.set(cache_key, new_count, ttl=int(self.window_size) + 1)
        return True, self.max_requests - new_count


class RateLimiter:
    """Token bucket rate limiter using Redis.

    Implements token bucket algorithm:
        - Bucket has max capacity (burst limit)
        - Tokens refill at steady rate
        - Each request consumes 1 token
        - Request rejected if no tokens available

    Features:
        - Per-user limits (authenticated requests)
        - Per-IP limits (anonymous requests)
        - Per-endpoint limits
        - Sliding window for accurate rate calculation

    Example:
        >>> limiter = RateLimiter(redis_client)
        >>>
        >>> @app.post("/api/expensive")
        >>> async def expensive_endpoint(request: Request):
        ...     await limiter.check_rate_limit(
        ...         request=request,
        ...         max_requests=10,
        ...         window_seconds=60,
        ...     )
        ...     return await do_expensive_work()
    """

    def __init__(
        self,
        redis_client: Any | None = None,
        trusted_proxies: frozenset[str] | None = None,
        cache_backend: CacheBackendProtocol | None = None,
    ) -> None:
        """Initialize rate limiter.

        Args:
            redis_client: Redis client for atomic Lua-script based sliding
                window limiting.  Preferred for production.
            trusted_proxies: Set of trusted proxy IP addresses whose
                ``X-Forwarded-For`` header is honoured.  When *None*
                (the default) the header is **ignored** and the direct
                peer address from ``request.client.host`` is used
                instead.  Set to a non-empty ``frozenset`` when the
                application runs behind a known reverse proxy.
            cache_backend: ``CacheBackendProtocol`` used for fixed-window distributed
                rate limiting when no ``redis_client`` is provided.  Shared
                across all workers that share the same cache; slightly less
                precise than the Redis Lua path but requires no raw Redis
                dependency.
        """
        self.redis = redis_client
        self._cache_backend = cache_backend
        self._trusted_proxies = trusted_proxies
        self._memory_limiters: dict[str, MemoryLimiter] = {}
        self._cache_limiters: dict[str, CacheBackendLimiter] = {}
        if not redis_client and not cache_backend:
            logger.warning(
                "rate_limiter_using_in_memory_store",
                extra={
                    "reason": "No Redis client or CacheBackendProtocol provided. Rate limiting state is "
                    "process-local and NOT shared across workers or instances. "
                    "Provide a redis_client or cache_backend for production multi-process deployments."
                },
            )

    async def check_rate_limit(
        self,
        request: Request,
        *,
        max_requests: int,
        window_seconds: int,
        scope: Literal["user", "ip", "endpoint"] = "user",
    ) -> None:
        """Check if request is within rate limit.

        Args:
            request: Starlette request.
            max_requests: Maximum requests per window.
            window_seconds: Time window in seconds.
            scope: Rate limit scope (user, ip, or endpoint).

        Raises:
            RateLimitError: If rate limit exceeded.

        Example:
            >>> # Allow 100 requests per minute per user
            >>> await limiter.check_rate_limit(
            ...     request=request,
            ...     max_requests=100,
            ...     window_seconds=60,
            ...     scope="user",
            ... )
        """
        # Get rate limit key based on scope
        key = self._get_rate_limit_key(request, scope)

        # Check using sliding window
        now = ambient_clock.now()
        window_start = now - timedelta(seconds=window_seconds)

        # Redis key for this rate limit
        redis_key = f"rate_limit:{key}"

        # Use Lua script for atomic operation
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        local window_seconds = tonumber(ARGV[4])

        -- Remove old entries outside window
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        -- Count requests in current window
        local current_count = redis.call('ZCARD', key)

        if current_count < max_requests then
            -- Add current request
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, window_seconds)
            return {1, max_requests - current_count - 1}
        else
            -- Rate limit exceeded
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local retry_after = math.ceil(oldest[2] + window_seconds - now)
            return {0, retry_after}
        end
        """

        if self.redis:
            result = await self.redis.eval(
                lua_script,
                1,
                redis_key,
                now.timestamp(),
                window_start.timestamp(),
                max_requests,
                window_seconds,
            )
            allowed = result[0]
            remaining = result[1]
        elif self._cache_backend is not None:
            # CacheBackendProtocol-backed fixed-window distributed counter
            limiter_key = f"{key}:{max_requests}:{window_seconds}"
            if limiter_key not in self._cache_limiters:
                self._cache_limiters[limiter_key] = CacheBackendLimiter(
                    cache=self._cache_backend,
                    window_size=window_seconds,
                    max_requests=max_requests,
                )
            cache_limiter = self._cache_limiters[limiter_key]
            allowed, remaining = await cache_limiter.try_acquire(key)
            result = [0, window_seconds] if not allowed else [1, remaining]
        else:
            # In-memory fallback
            limiter_key = f"{key}:{max_requests}:{window_seconds}"
            if limiter_key not in self._memory_limiters:
                self._memory_limiters[limiter_key] = MemoryLimiter(
                    window_size=window_seconds,
                    max_requests=max_requests,
                )

            limiter = self._memory_limiters[limiter_key]
            allowed = await limiter.try_acquire()
            remaining = max_requests - limiter.current_requests

            if not allowed:
                retry_after = window_seconds
                result = [0, retry_after]
            else:
                result = [1, remaining]

        if not allowed:
            retry_after = int(result[1])

            logger.warning(
                "security.rate_limit_exceeded",
                key=key,
                max_requests=max_requests,
                window_seconds=window_seconds,
                retry_after=retry_after,
            )

            raise RateLimitError(details={"retry_after": retry_after})

        remaining = result[1]

        # Add rate limit headers
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = max_requests
        request.state.rate_limit_reset = int(
            (now + timedelta(seconds=window_seconds)).timestamp()
        )

        logger.debug(
            "rate_limit.check_passed",
            key=key,
            remaining=remaining,
            limit=max_requests,
        )

    def _get_rate_limit_key(
        self,
        request: Request,
        scope: Literal["user", "ip", "endpoint"],
    ) -> str:
        """Get rate limit key based on scope.

        Args:
            request: Starlette request.
            scope: Rate limit scope.

        Returns:
            Rate limit key.
        """
        if scope == "user":
            # Use user ID if authenticated
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                return f"user:{user_id}"
            # Fall back to IP
            return f"ip:{self._get_client_ip(request)}"

        if scope == "ip":
            return f"ip:{self._get_client_ip(request)}"

        if scope == "endpoint":
            # Per-endpoint limit
            path = request.url.path
            method = request.method
            return f"endpoint:{method}:{path}"

        raise ValueError(f"Invalid scope: {scope}")

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address.

        The ``X-Forwarded-For`` header is read **only** when the direct
        peer address (``request.client.host``) is in the instance's
        ``trusted_proxies`` set.  Trusting the header unconditionally
        makes IP-based rate limits trivially spoofable by any client
        that sets the header itself.

        Args:
            request: Starlette request.

        Returns:
            Client IP address (string).
        """
        direct_ip = request.client.host if request.client else None

        # Only honour X-Forwarded-For when the request arrives from a
        # known trusted proxy and the header is actually present.
        if self._trusted_proxies is not None and direct_ip in self._trusted_proxies:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()

        return direct_ip or "unknown"


def rate_limit(
    max_requests: int,
    window_seconds: int,
    scope: Literal["user", "ip", "endpoint"] = "user",
    limiter: WebRateLimiterProtocol | None = None,
) -> Callable:
    """Decorator for rate limiting endpoints.

    Enforces rate limits using the provided ``limiter`` instance (constructor injection).
    The ``limiter`` must be explicitly passed; no runtime container resolution is performed.

    If no limiter is provided, the endpoint executes without rate limiting and a warning
    is logged.

    Args:
        max_requests: Maximum requests per window.
        window_seconds: Time window in seconds.
        scope: Rate limit scope (user, ip, or endpoint).
        limiter: Required pre-constructed :class:`WebRateLimiterProtocol` instance.
            Must be injected at decoration time.

    Returns:
        Decorator function.

    Example:
        >>> my_limiter = RateLimiter(redis_client=redis)
        >>> @app.post("/api/upload")
        >>> @rate_limit(max_requests=5, window_seconds=60, limiter=my_limiter)
        >>> async def upload_file(request: Request):
        ...     return await process_upload()
    """
    _injected_limiter = limiter  # captured once at decoration time

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # ── 1. Locate the request object ───────────────────────────────
            request: Request | None = None
            for arg in args:
                if (
                    hasattr(arg, "scope")
                    and hasattr(arg, "app")
                    and "method" in arg.scope
                ):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                logger.warning(
                    "rate_limit_skipped_no_request",
                    endpoint=func.__name__,
                )
                return await func(*args, **kwargs)

            # ── 2. Resolve the limiter (only via explicit injection) ─
            resolved_limiter: WebRateLimiterProtocol | None = _injected_limiter

            if resolved_limiter is None:
                logger.warning(
                    "rate_limit_skipped_no_limiter",
                    endpoint=func.__name__,
                    reason="no limiter explicitly injected; use rate_limit(limiter=...) to provide one",
                )
                return await func(*args, **kwargs)

            # ── 3. Enforce the rate limit ───────────────────────────────────
            await resolved_limiter.check_rate_limit(
                request=request,
                max_requests=max_requests,
                window_seconds=window_seconds,
                scope=scope,
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class RateLimitMiddleware:
    """Middleware to add rate limit headers to all responses.

    Example:
        >>> app.add_middleware(RateLimitMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        rate_limiter: RateLimiter | None = None,
        config: Any | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            app: ASGI application.
            rate_limiter: Rate limiter instance (optional).
            config: ``RateLimitConfig`` driving per-path rules and defaults.
                When ``enabled`` and a limiter is present, ``__call__``
                enforces the matched rule (or the default limit) instead of
                only stamping headers.
        """
        self.app = app
        self.rate_limiter = rate_limiter
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process request and add rate limit headers.

        Args:
            scope: ASGI scope
            receive: ASGI receive
            send: ASGI send
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # ── Enforce before forwarding ─────────────────────────────────────
        # The existing check_rate_limit() algorithm (Redis Lua / cache /
        # in-memory) is the single enforcement engine. A breached request
        # gets the standard 429 + Retry-After response (RateLimitError is
        # caught here because middleware raises bypass Starlette's inner
        # ExceptionMiddleware on supported versions and would surface as 500).
        if self.rate_limiter is not None and self.config is not None and self.config.enabled:
            request = Request(scope, receive)
            if self.config.whitelist_ips and request.client and request.client.host in self.config.whitelist_ips:
                pass  # whitelisted — skip enforcement (D2)
            else:
                rule = self.config.get_rule(request.url.path)
                if rule is not None:
                    max_requests, window_seconds = rule.requests, rule.window
                else:
                    max_requests = self.config.default_limit
                    window_seconds = self.config.default_window
                try:
                    await self.rate_limiter.check_rate_limit(
                        request,
                        max_requests=max_requests,
                        window_seconds=window_seconds,
                        scope="user",
                    )
                except RateLimitError as exc:
                    response = _rate_limit_429_response(exc)
                    await response(scope, receive, send)
                    return

        async def send_with_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Add rate limit headers if available (stored in request.state)
                # scope["state"] is a plain dict in Starlette; State is a wrapper
                state = scope.get("state")
                if isinstance(state, dict):
                    remaining = state.get("rate_limit_remaining")
                    limit = state.get("rate_limit_limit")
                    reset = state.get("rate_limit_reset")
                elif state is not None:
                    remaining = getattr(state, "rate_limit_remaining", None)
                    limit = getattr(state, "rate_limit_limit", None)
                    reset = getattr(state, "rate_limit_reset", None)
                else:
                    remaining = limit = reset = None

                if remaining is not None:
                    headers.append((b"x-ratelimit-remaining", str(remaining).encode()))
                if limit is not None:
                    headers.append((b"x-ratelimit-limit", str(limit).encode()))
                if reset is not None:
                    headers.append((b"x-ratelimit-reset", str(reset).encode()))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_headers)
