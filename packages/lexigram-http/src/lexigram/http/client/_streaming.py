"""Multipart upload and response-streaming methods."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Coroutine, Iterable

    from lexigram.contracts.web.sse import ServerSentEvent
    from lexigram.http.client.http_client import HTTPClient  # noqa: F401
    from lexigram.result import Result  # noqa: F401

from lexigram.contracts.infra.resilience import (
    CircuitBreakerProtocol,
    RetryPolicyProtocol,
)
from lexigram.contracts.web import HttpResponse, InterceptorProtocol
from lexigram.contracts.web.sse import ServerSentEvent
from lexigram.http.config import HTTPClientConfig
from lexigram.http.exceptions import (
    HTTPClientError,
    HTTPConnectionError,
)
from lexigram.logging import get_logger
from lexigram.result import Result

logger = get_logger(__name__)

_CIRCUIT_OPEN_CODE = "LEX_ERR_RES_009"
_RETRY_EXHAUSTED_CODE = "LEX_ERR_RES_008"



class _HTTPStreamingMixin:
    request: Callable[..., Coroutine[Any, Any, HttpResponse]]
    _request_result: Callable[
        ..., Coroutine[Any, Any, Result[HttpResponse, HTTPClientError]]
    ]
    _assert_url_safe: Callable[..., Coroutine[Any, Any, None]]
    start: Callable[..., Coroutine[Any, Any, None]]
    stop: Callable[..., Coroutine[Any, Any, None]]
    _config: Any
    _pool: Any
    _metrics: Any
    """See :class:`HTTPClient`."""
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

        await self._assert_url_safe(url)

        async with self._pool._session.request(method, url, **kwargs) as resp:

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

        await self._assert_url_safe(url)

        headers = dict(kwargs.pop("headers", {}))
        headers.setdefault("Accept", "text/event-stream")
        headers.setdefault("Cache-Control", "no-cache")

        async with self._pool._session.request(
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
        client = cls(  # type: ignore[call-arg]
            config=config,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
            interceptors=interceptors,
        )
        await client.start()
        try:
            yield client  # type: ignore[misc]
        finally:
            await client.stop()
