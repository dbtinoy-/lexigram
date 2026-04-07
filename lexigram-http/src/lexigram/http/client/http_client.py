"""Async HTTP client for lexigram core.

Provides :class:`HTTPClient` — a transport-agnostic, resilience-aware client
backed by ``aiohttp``. All resilience components (retry policy, circuit breaker)
are injected as constructor parameters; no service-locator look-ups are
performed at request time.

Result semantics (verb methods only):
    - Http 2xx response  → ``Ok(HttpResponse)``
    - Http 4xx/5xx response → ``Err(HTTPStatusError)``
    - Connection / timeout failures → ``Err(HTTPConnectionError | HTTPTimeoutError)``
    - Circuit-breaker open or retries exhausted → raised as exceptions
      (infrastructure-level failures; callers should not normally recover).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterable

    from lexigram.contracts.observability.metrics import MetricsRecorderProtocol
    from lexigram.contracts.web.sse import ServerSentEvent

from lexigram.contracts.infra.resilience import (
    CircuitBreakerError as _CoreCircuitBreakerError,
)
from lexigram.contracts.infra.resilience import (
    CircuitBreakerProtocol,
    ResiliencePipelineProtocol,
    RetryPolicyProtocol,
)
from lexigram.contracts.infra.resilience import (
    RetryError as _CoreRetryError,
)
from lexigram.contracts.web import HttpResponse, InterceptorProtocol
from lexigram.contracts.web.sse import ServerSentEvent
from lexigram.http.config import HTTPClientConfig
from lexigram.http.exceptions import (
    HTTPCircuitOpenError,
    HTTPClientError,
    HTTPConnectionError,
    HTTPRetryExhaustedError,
    HTTPStatusError,
    HTTPTimeoutError,
)
from lexigram.http.pool import ConnectionPool
from lexigram.http.types import RequestContext
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)

_CIRCUIT_OPEN_CODE = "LEX_ERR_RES_009"
_RETRY_EXHAUSTED_CODE = "LEX_ERR_RES_008"


def _is_retry_exhausted_error(exc: BaseException) -> bool:
    """Return whether *exc* represents a retry-exhausted failure."""

    return (
        isinstance(exc, _CoreRetryError)
        and getattr(exc, "code", None) == _RETRY_EXHAUSTED_CODE
    )


def _is_circuit_open_error(exc: BaseException) -> bool:
    """Return whether *exc* represents an open-circuit failure."""

    return (
        isinstance(exc, _CoreCircuitBreakerError)
        and getattr(exc, "code", None) == _CIRCUIT_OPEN_CODE
    )


async def _to_http_response(raw: Any, method: str) -> HttpResponse:
    """Convert an ``aiohttp.ClientResponse`` to a framework-owned :class:`HttpResponse`.

    Reads the body eagerly so the response can be used after the connection is
    released back to the pool.

    Args:
        raw: The raw ``aiohttp`` response to convert.
        method: Upper-cased HTTP method of the original request.

    Returns:
        A fully-populated :class:`HttpResponse` instance.
    """
    body = await raw.read()
    text = body.decode(raw.get_encoding() or "utf-8", errors="replace")
    json_data: Any = None
    content_type = raw.headers.get("Content-Type", "")
    if "application/json" in content_type or "text/json" in content_type:
        try:
            json_data = await raw.json(content_type=None)
        except Exception:  # noqa: BLE001 — non-JSON body is not an error
            pass
    return HttpResponse(
        status=raw.status,
        headers=dict(raw.headers),
        body=body,
        text=text,
        json=json_data,
        url=str(raw.url),
        method=method.upper(),
    )


class HTTPClient:
    """Async HTTP client with connection pooling and optional resilience.

    All dependencies are provided at construction time (constructor injection).
    When used through :class:`~lexigram.http.HTTPProvider`, ``retry_policy``
    and ``circuit_breaker`` are resolved from the container and injected here.
    For standalone usage, pass them directly or accept the defaults.

    Args:
        config: Pool and client configuration.  Defaults to
            :class:`~lexigram.http.HTTPClientConfig` with framework defaults.
        pool: Optional pre-configured :class:`ConnectionPool`.  Created from
            *config* when not provided.
        retry_policy: Retry policy for transient failures.  Defaults to a
            :class:`~lexigram.resilience.RetryPolicy` with framework defaults.
        circuit_breaker: Optional circuit breaker; disabled when ``None``.
        interceptors: Zero or more interceptors applied to every request.
        resilience: Optional :class:`ResiliencePipelineProtocol` that combines
            retry, circuit-breaker, bulkhead and timeout into a single
            composable pipeline.  When provided it takes precedence over the
            individual ``retry_policy`` and ``circuit_breaker`` parameters.
        metrics: Optional :class:`~lexigram.contracts.observability.protocols.MetricsRecorderProtocol`
            for emitting ``http.request.duration`` (histogram) and
            ``http.request.status`` (counter) per-request metrics.

    Example:
        >>> config = HTTPClientConfig()
        >>> async with HTTPClient.session_context(config) as client:
        ...     response = await client.get("https://api.example.com/data")
    """

    def __init__(
        self,
        config: HTTPClientConfig | None = None,
        pool: ConnectionPool | None = None,
        retry_policy: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
        interceptors: Iterable[InterceptorProtocol] = (),
        resilience: ResiliencePipelineProtocol | None = None,
        metrics: MetricsRecorderProtocol | None = None,
    ) -> None:
        self._config = config or HTTPClientConfig()
        self._pool = pool or ConnectionPool(
            max_connections=self._config.pool.max_connections,
            max_keepalive_connections=self._config.pool.max_keepalive_connections,
            max_connections_per_host=self._config.pool.max_connections_per_host,
            timeout=self._config.pool.timeout,
            ttl_dns_cache=self._config.pool.ttl_dns_cache,
            force_close=self._config.pool.force_close,
            verify_ssl=getattr(self._config.pool, "verify_ssl", True),
            proxy=self._config.proxy,
            trust_env=self._config.trust_env,
            cookie_jar=self._config.cookie_jar,
        )
        self._resilience = resilience
        self._metrics = metrics
        # Default retry policy: local implementation - no cross-package imports
        if retry_policy is None:
            from lexigram.contracts.infra.resilience import RetryConfig
            from lexigram.http.retry import RetryPolicy

            retry_policy = RetryPolicy(config=RetryConfig())
        self._retry_policy: RetryPolicyProtocol = retry_policy
        self._circuit_breaker = circuit_breaker
        self._interceptors: list[InterceptorProtocol] = list(interceptors)

    @property
    def config(self) -> HTTPClientConfig:
        """Return the client configuration."""
        return self._config

    @property
    def pool(self) -> ConnectionPool:
        """Return the underlying connection pool."""
        return self._pool

    @pool.setter
    def pool(self, value: ConnectionPool) -> None:
        """Replace the connection pool (mainly for testing)."""
        self._pool = value

    async def start(self) -> None:
        """Start the HTTP client and its connection pool."""
        await self._pool.start()

    async def stop(self) -> None:
        """Stop the HTTP client and close the connection pool."""
        await self._pool.stop()

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        """Make an HTTP request with retry and optional circuit-breaker protection.

        .. note::
            **Infrastructure-level method** — this method raises exceptions for
            all failures (circuit open, retries exhausted, connection errors).
            Use the high-level verb methods (:meth:`get`, :meth:`post`, etc.)
            in application/domain code — they return ``Result`` and avoid
            exception-based control flow for expected failures.

            Summary of the two-layer strategy:

            * ``request()`` — infrastructure layer, raises exceptions.
            * ``get()``, ``post()``, etc. — domain layer, return ``Result``.

        Args:
            method: HTTP method (``GET``, ``POST``, etc.)
            url: Target URL.
            **kwargs: Additional keyword arguments forwarded to ``aiohttp``.

        Returns:
            Framework-owned :class:`HttpResponse`.

        Raises:
            HTTPCircuitOpenError: When the circuit breaker is open.
            HTTPRetryExhaustedError: When all retry attempts are exhausted.
            HTTPConnectionError: When the connection cannot be established.
            HTTPTimeoutError: When the request times out.
        """
        # Build typed request context for interceptors
        request_ctx = RequestContext(
            method=method,
            url=url,
            headers=dict(kwargs.get("headers", {})),
        )

        # Run request interceptors
        for interceptor in self._interceptors:
            request_ctx = await interceptor.intercept_request(request_ctx)

        _method = request_ctx.method
        _url = request_ctx.url
        _kwargs = dict(kwargs)
        _kwargs["headers"] = request_ctx.headers

        # Short-circuit immediately when circuit is already open
        if self._circuit_breaker and (
            getattr(self._circuit_breaker.state, "value", self._circuit_breaker.state)
            == "open"
        ):
            raise HTTPCircuitOpenError("Circuit breaker is OPEN")

        async def _execute() -> Any:
            if self._pool._session is None:
                raise RuntimeError(
                    "HTTPClient not started — call await client.start() first"
                )
            # Inject pool-level proxy unless caller overrides it
            if getattr(self._pool, "proxy", None) and "proxy" not in _kwargs:
                _kwargs["proxy"] = self._pool.proxy
            if self._circuit_breaker:
                return await self._circuit_breaker.call(
                    self._pool._session.request,
                    _method,
                    _url,
                    **_kwargs,
                )
            return await self._pool._session.request(_method, _url, **_kwargs)

        try:
            if self._resilience is not None:
                raw = await self._resilience.execute(_execute)
            else:
                raw = await self._retry_policy.execute(_execute)
        except (
            Exception
        ) as exc:  # HTTP client must normalise all resilience library exceptions
            if _is_retry_exhausted_error(exc):
                raise HTTPRetryExhaustedError(str(exc)) from exc
            if _is_circuit_open_error(exc):
                raise HTTPCircuitOpenError(str(exc)) from exc
            raise

        # Run response interceptors
        for interceptor in self._interceptors:
            raw = await interceptor.intercept_response(raw)

        return await _to_http_response(raw, method)

    async def get(
        self, url: str, **kwargs: Any
    ) -> Result[HttpResponse, HTTPClientError]:
        """Perform a GET request.

        Args:
            url: Target URL.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            ``Ok(HttpResponse)`` on 2xx; ``Err(HTTPStatusError)`` on 4xx/5xx;
            ``Err(HTTPConnectionError | HTTPTimeoutError)`` on transport failure.

        Raises:
            HTTPCircuitOpenError: When the circuit breaker is open.
            HTTPRetryExhaustedError: When all retry attempts are exhausted.
        """
        return await self._request_result("GET", url, **kwargs)

    async def post(
        self, url: str, **kwargs: Any
    ) -> Result[HttpResponse, HTTPClientError]:
        """Perform a POST request.

        Args:
            url: Target URL.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            ``Ok(HttpResponse)`` on 2xx; ``Err(HTTPStatusError)`` on 4xx/5xx;
            ``Err(HTTPConnectionError | HTTPTimeoutError)`` on transport failure.

        Raises:
            HTTPCircuitOpenError: When the circuit breaker is open.
            HTTPRetryExhaustedError: When all retry attempts are exhausted.
        """
        return await self._request_result("POST", url, **kwargs)

    async def put(
        self, url: str, **kwargs: Any
    ) -> Result[HttpResponse, HTTPClientError]:
        """Perform a PUT request.

        Args:
            url: Target URL.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            ``Ok(HttpResponse)`` on 2xx; ``Err(HTTPStatusError)`` on 4xx/5xx;
            ``Err(HTTPConnectionError | HTTPTimeoutError)`` on transport failure.

        Raises:
            HTTPCircuitOpenError: When the circuit breaker is open.
            HTTPRetryExhaustedError: When all retry attempts are exhausted.
        """
        return await self._request_result("PUT", url, **kwargs)

    async def delete(
        self, url: str, **kwargs: Any
    ) -> Result[HttpResponse, HTTPClientError]:
        """Perform a DELETE request.

        Args:
            url: Target URL.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            ``Ok(HttpResponse)`` on 2xx; ``Err(HTTPStatusError)`` on 4xx/5xx;
            ``Err(HTTPConnectionError | HTTPTimeoutError)`` on transport failure.

        Raises:
            HTTPCircuitOpenError: When the circuit breaker is open.
            HTTPRetryExhaustedError: When all retry attempts are exhausted.
        """
        return await self._request_result("DELETE", url, **kwargs)

    async def patch(
        self, url: str, **kwargs: Any
    ) -> Result[HttpResponse, HTTPClientError]:
        """Perform a PATCH request.

        Args:
            url: Target URL.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            ``Ok(HttpResponse)`` on 2xx; ``Err(HTTPStatusError)`` on 4xx/5xx;
            ``Err(HTTPConnectionError | HTTPTimeoutError)`` on transport failure.

        Raises:
            HTTPCircuitOpenError: When the circuit breaker is open.
            HTTPRetryExhaustedError: When all retry attempts are exhausted.
        """
        return await self._request_result("PATCH", url, **kwargs)

    async def head(
        self, url: str, **kwargs: Any
    ) -> Result[HttpResponse, HTTPClientError]:
        """Perform a HEAD request.

        Args:
            url: Target URL.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            ``Ok(HttpResponse)`` on 2xx; ``Err(HTTPStatusError)`` on 4xx/5xx;
            ``Err(HTTPConnectionError | HTTPTimeoutError)`` on transport failure.

        Raises:
            HTTPCircuitOpenError: When the circuit breaker is open.
            HTTPRetryExhaustedError: When all retry attempts are exhausted.
        """
        return await self._request_result("HEAD", url, **kwargs)

    async def _request_result(
        self, method: str, url: str, **kwargs: Any
    ) -> Result[HttpResponse, HTTPClientError]:
        """Shared Result-returning implementation for all verb methods.

        Calls the raw :meth:`request` transport method and maps the outcome:
        - 2xx → ``Ok(HttpResponse)``
        - 4xx/5xx → ``Err(HTTPStatusError)``
        - Connection / timeout failures → ``Err(HTTPConnectionError | HTTPTimeoutError)``
        - Circuit-breaker open / retries exhausted → raised as-is (infrastructure)

        Args:
            method: HTTP method string.
            url: Target URL.
            **kwargs: Forwarded to :meth:`request`.
        """
        start = time.monotonic()
        try:
            response = await self.request(method, url, **kwargs)
        except HTTPConnectionError as exc:
            logger.debug(
                "http.client.connection_error", method=method, url=url, error=str(exc)
            )
            if self._metrics is not None:
                self._metrics.increment(
                    "http.request.status",
                    tags={"method": method.upper(), "status": "connection_error"},
                )
            return Err(exc)
        except HTTPTimeoutError as exc:
            logger.debug("http.client.timeout", method=method, url=url, error=str(exc))
            if self._metrics is not None:
                self._metrics.increment(
                    "http.request.status",
                    tags={"method": method.upper(), "status": "timeout"},
                )
            return Err(exc)
        # HTTPCircuitOpenError and HTTPRetryExhaustedError propagate as exceptions.
        finally:
            duration = time.monotonic() - start
            if self._metrics is not None:
                self._metrics.histogram(
                    "http.request.duration",
                    duration,
                    tags={"method": method.upper()},
                )

        if response.status >= 400:
            logger.debug(
                "http.client.error_response",
                method=method,
                url=url,
                status=response.status,
            )
            if self._metrics is not None:
                self._metrics.increment(
                    "http.request.status",
                    tags={"method": method.upper(), "status": str(response.status)},
                )
            return Err(HTTPStatusError(status=response.status, response=response))
        if self._metrics is not None:
            self._metrics.increment(
                "http.request.status",
                tags={"method": method.upper(), "status": str(response.status)},
            )
        return Ok(response)

    async def post_multipart(
        self,
        url: str,
        fields: dict[str, str | bytes | tuple[str, bytes, str]],
        **kwargs: Any,
    ) -> Result[HttpResponse, HTTPClientError]:
        """Upload multipart/form-data.

        Builds an ``aiohttp.FormData`` payload from *fields* and POSTs it.
        Each value can be:

        * ``str`` — sent as a plain text field
        * ``bytes`` — sent as a file-like binary field (filename inferred from
          the field name)
        * ``(filename, data, content_type)`` — full control over the part
          headers

        Args:
            url: Target URL.
            fields: Mapping of field names to values.  See above for supported
                value types.
            **kwargs: Additional keyword arguments forwarded to :meth:`request`.

        Returns:
            ``Ok(HttpResponse)`` on 2xx; ``Err(...)`` on failure.

        Example::

            result = await client.post_multipart(
                "https://api.example.com/upload",
                fields={
                    "description": "My file",
                    "file": ("report.pdf", pdf_bytes, "application/pdf"),
                },
            )
        """
        import aiohttp

        form = aiohttp.FormData()
        for name, value in fields.items():
            if isinstance(value, str):
                form.add_field(name, value)
            elif isinstance(value, bytes):
                form.add_field(name, value, filename=name)
            else:
                filename, data, content_type = value
                form.add_field(name, data, filename=filename, content_type=content_type)

        return await self._request_result("POST", url, data=form, **kwargs)

    @asynccontextmanager
    async def stream(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> AsyncIterator[AsyncIterator[bytes]]:
        """Async context manager that streams the response body as raw bytes chunks.

        Unlike :meth:`request`, this method does not buffer the entire response
        body in memory — suitable for large file downloads or chunked responses.

        Args:
            method: HTTP method (``GET``, ``POST``, etc.)
            url: Target URL.
            **kwargs: Additional keyword arguments forwarded to ``aiohttp``.

        Yields:
            An :class:`~collections.abc.AsyncIterator` of ``bytes`` chunks.

        Raises:
            HTTPConnectionError: When the connection cannot be established.
            HTTPTimeoutError: When the request times out.

        Example::

            async with client.stream("GET", large_file_url) as chunks:
                async for chunk in chunks:
                    await file.write(chunk)
        """
        if self._pool._session is None:
            raise HTTPConnectionError("HTTPClient not started. Call start() first.")

        async with self._pool._session.request(method, url, **kwargs) as resp:  # type: ignore[attr-defined]

            async def _iter_chunks() -> AsyncIterator[bytes]:
                async for chunk, _ in resp.content.iter_chunks():
                    if chunk:
                        yield chunk

            yield _iter_chunks()

    @asynccontextmanager
    async def sse(
        self,
        url: str,
        **kwargs: Any,
    ) -> AsyncIterator[AsyncIterator[ServerSentEvent]]:
        """Async context manager that consumes a Server-Sent Events (SSE) stream.

        Opens a persistent ``GET`` connection and parses the ``text/event-stream``
        response into :class:`~lexigram.contracts.web.sse.ServerSentEvent` objects.

        Args:
            url: SSE endpoint URL.
            **kwargs: Additional keyword arguments forwarded to ``aiohttp``.

        Yields:
            An :class:`~collections.abc.AsyncIterator` of
            :class:`~lexigram.contracts.web.sse.ServerSentEvent` objects.

        Raises:
            HTTPConnectionError: When the connection cannot be established.

        Example::

            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            async with client.sse("https://api.example.com/events") as events:
                async for event in events:
                    logger.info("sse_event", event_type=event.event, data=event.data)
        """
        if self._pool._session is None:
            raise HTTPConnectionError("HTTPClient not started. Call start() first.")

        headers = dict(kwargs.pop("headers", {}))
        headers.setdefault("Accept", "text/event-stream")
        headers.setdefault("Cache-Control", "no-cache")

        async with self._pool._session.request(  # type: ignore[attr-defined]
            "GET", url, headers=headers, **kwargs
        ) as resp:

            async def _parse_sse() -> AsyncIterator[ServerSentEvent]:
                event_type = "message"
                data_lines: list[str] = []
                event_id: str | None = None

                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8").rstrip("\n").rstrip("\r")
                    if not line:
                        if data_lines:
                            yield ServerSentEvent(
                                data="\n".join(data_lines),
                                event=event_type,
                                event_id=event_id,
                            )
                        event_type = "message"
                        data_lines = []
                        event_id = None
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].lstrip(" "))
                    elif line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("id:"):
                        event_id = line[3:].strip()

            yield _parse_sse()

    @classmethod
    @asynccontextmanager
    async def session_context(
        cls,
        config: HTTPClientConfig | None = None,
        retry_policy: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
        interceptors: Iterable[InterceptorProtocol] = (),
    ) -> AsyncIterator[HTTPClient]:
        """Async context manager that starts and stops the client automatically.

        Args:
            config: Optional :class:`HTTPClientConfig`; framework defaults apply.
            retry_policy: Optional retry policy; framework default when ``None``.
            circuit_breaker: Optional circuit breaker; disabled when ``None``.
            interceptors: Zero or more interceptors.

        Yields:
            A started :class:`HTTPClient` instance.

        Example:
            >>> async with HTTPClient.session_context() as client:
            ...     response = await client.get("https://api.example.com")
        """
        client = cls(
            config=config,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
            interceptors=interceptors,
        )
        await client.start()
        try:
            yield client
        finally:
            await client.stop()


__all__ = ["HTTPClient"]
