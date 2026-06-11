"""Exceptions for the lexigram.http module.

All exceptions derive from :class:`HTTPClientError` which itself derives from
:class:`InfrastructureError` so they propagate as infrastructure failures.

Result-aware callers should use the Result-returning verb methods on
:class:`~lexigram.http.client.HTTPClient` and match on
:class:`HTTPStatusError` (4xx/5xx) vs. :class:`HTTPConnectionError` /
:class:`HTTPTimeoutError` (transport failures) rather than catching
exceptions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.exceptions import InfrastructureError

if TYPE_CHECKING:
    from lexigram.contracts.web import HttpResponse


class HTTPClientError(InfrastructureError):
    """Base exception for all HTTP client errors."""

    _code: str = "LEX_ERR_HTTP_001"


class HTTPConnectionError(HTTPClientError):
    """Raised when a connection to a remote host fails."""

    _code: str = "LEX_ERR_HTTP_002"


class HTTPTimeoutError(HTTPClientError):
    """Raised when a connection or request times out."""

    _code: str = "LEX_ERR_HTTP_003"


class HTTPInterceptorError(HTTPClientError):
    """Raised when a request/response interceptor fails."""

    _code: str = "LEX_ERR_HTTP_004"


class HTTPCircuitOpenError(HTTPClientError):
    """Raised when the circuit breaker is open and requests are rejected."""

    _code: str = "LEX_ERR_HTTP_005"


class HTTPRetryExhaustedError(HTTPClientError):
    """Raised when all retry attempts for a request have been exhausted."""

    _code: str = "LEX_ERR_HTTP_006"


class HTTPStatusError(HTTPClientError):
    """Raised (or returned as an Err) when the server responds with 4xx/5xx.

    Callers using the Result-based verb methods receive this as
    ``Err(HTTPStatusError(...))``; callers using the raw
    :meth:`~lexigram.http.client.HTTPClient.request` method receive
    a plain :class:`~lexigram.contracts.web.HttpResponse` with the
    non-2xx status code.

    Attributes:
        status: HTTP status code (4xx or 5xx).
        response: The full :class:`~lexigram.contracts.web.HttpResponse`
            that was received.
    """

    _code: str = "LEX_ERR_HTTP_007"

    def __init__(
        self,
        status: int,
        response: HttpResponse,
        message: str | None = None,
    ) -> None:
        self.status = status
        self.response = response
        super().__init__(message or f"HTTP {status}: {response.url}")

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status={self.status!r}, url={self.response.url!r})"
        )


class HTTPUnsafeURLError(HTTPClientError):
    """Raised when a request URL fails the SSRF safety gate."""

    _code: str = "LEX_ERR_HTTP_008"


__all__ = [
    "HTTPCircuitOpenError",
    "HTTPClientError",
    "HTTPConnectionError",
    "HTTPInterceptorError",
    "HTTPRetryExhaustedError",
    "HTTPStatusError",
    "HTTPTimeoutError",
    "HTTPUnsafeURLError",
]
