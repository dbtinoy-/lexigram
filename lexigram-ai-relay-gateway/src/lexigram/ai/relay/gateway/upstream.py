"""HTTP upstream transport for the relay gateway.

Sends resolved ``UpstreamRequest`` values to model providers through the
contracts-level ``HTTPClientProtocol`` and maps transport outcomes into
typed ``RelayGatewayError`` or ``Ok(UpstreamResponse)`` results.

The transport protocol keeps ``lexigram-http`` behind the DI boundary:
this module never imports it and classifies failures from stdlib and
contracts-level exceptions only.
"""

from __future__ import annotations

import asyncio

from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.exceptions import InfrastructureError
from lexigram.contracts.web import HTTPClientProtocol, HttpResponse
from lexigram.serialization import loads

__all__ = ["HTTPUpstreamAdapter"]


class HTTPUpstreamAdapter:
    """Sends upstream requests through an injected HTTP client.

    The adapter classifies failures from stdlib and contracts-level
    exceptions only (by design); implementations of
    ``HTTPClientProtocol`` keep transport libraries like
    ``lexigram-http`` behind the DI boundary.

    Attributes:
        _http: The injected HTTP client resolved from DI.
    """

    def __init__(self, http: HTTPClientProtocol) -> None:
        """Bind the adapter to an HTTP client.

        Args:
            http: Any ``HTTPClientProtocol`` implementation driving the
                outbound request.
        """
        self._http = http

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Send *request* upstream and classify the outcome.

        Method, URL, headers, JSON payload, and timeout come straight
        from the ``UpstreamRequest``. 2xx responses are decoded into a
        typed ``UpstreamResponse`` (empty bodies yield a ``None``
        payload); non-2xx responses and transport failures map to
        ``RelayGatewayError`` values that never carry raw bodies,
        headers, or credentials.

        Args:
            request: Fully-resolved upstream request.

        Returns:
            ``Ok(UpstreamResponse)`` for 2xx responses (the response
            headers are preserved verbatim), or ``Err`` classifying
            transport cancellation (``UPSTREAM_CANCELLED``, 499),
            timeouts (``UPSTREAM_TIMEOUT``, 504), generic transport
            failures (``UPSTREAM_FAILED``, 502), malformed 2xx bodies
            (``UPSTREAM_MALFORMED``, 502), and non-2xx responses
            (``UPSTREAM_ERROR`` with a safe public message).
        """
        try:
            response = await self._http.request(
                method=request.method,
                url=request.url,
                headers=dict(request.headers),
                json=request.payload,
                timeout=request.timeout_seconds,
            )
        except asyncio.CancelledError:
            return Err(
                RelayGatewayError(
                    code="UPSTREAM_CANCELLED",
                    message="upstream request cancelled",
                    status_code=499,
                    request_id=request.request_id,
                )
            )
        except TimeoutError:
            return Err(
                RelayGatewayError(
                    code="UPSTREAM_TIMEOUT",
                    message="upstream request timed out",
                    status_code=504,
                    request_id=request.request_id,
                    retryable=True,
                )
            )
        except InfrastructureError:
            return Err(
                RelayGatewayError(
                    code="UPSTREAM_FAILED",
                    message="upstream transport failure",
                    status_code=502,
                    request_id=request.request_id,
                    retryable=True,
                )
            )
        if 200 <= response.status < 300:
            return self._decode_success(request, response)
        return self._decode_error(request, response)

    @staticmethod
    def _decode_success(
        request: UpstreamRequest, response: HttpResponse
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Map a 2xx response to an ``UpstreamResponse``.

        Empty bodies yield a ``None`` payload; non-empty bodies must be a
        JSON object or the response is classified as malformed.
        """
        if not response.body:
            return Ok(
                UpstreamResponse(
                    status_code=response.status,
                    headers=dict(response.headers),
                    payload=None,
                )
            )
        try:
            parsed = loads(response.body)
        except ValueError:
            return Err(
                RelayGatewayError(
                    code="UPSTREAM_MALFORMED",
                    message="malformed upstream response",
                    status_code=502,
                    request_id=request.request_id,
                )
            )
        if not isinstance(parsed, dict):
            return Err(
                RelayGatewayError(
                    code="UPSTREAM_MALFORMED",
                    message="malformed upstream response",
                    status_code=502,
                    request_id=request.request_id,
                )
            )
        return Ok(
            UpstreamResponse(
                status_code=response.status,
                headers=dict(response.headers),
                payload=parsed,
            )
        )

    @staticmethod
    def _decode_error(
        request: UpstreamRequest, response: HttpResponse
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Map a non-2xx response to an ``UPSTREAM_ERROR``.

        The error message is a safe public string extracted from the
        body (``error.message``, ``error``, or ``message`` — first
        present wins); raw bodies, headers, and their keys are never
        propagated.
        """
        message = HTTPUpstreamAdapter._safe_error_message(response)
        status = response.status if 400 <= response.status <= 599 else 502
        return Err(
            RelayGatewayError(
                code="UPSTREAM_ERROR",
                message=message or "upstream request failed",
                status_code=status,
                request_id=request.request_id,
                retryable=response.status >= 500,
            )
        )

    @staticmethod
    def _safe_error_message(response: HttpResponse) -> str | None:
        """Extract a public error message from a non-2xx body.

        Returns:
            The first string found under ``error.message``, ``error``,
            or ``message`` (in that order), or ``None`` when the body is
            empty, not a JSON object, or holds no public message key.
        """
        if not response.body:
            return None
        try:
            parsed = loads(response.body)
        except ValueError:
            return None
        if not isinstance(parsed, dict):
            return None
        error = parsed.get("error")
        if isinstance(error, dict):
            nested = error.get("message")
            if isinstance(nested, str):
                return nested
        elif isinstance(error, str):
            return error
        message = parsed.get("message")
        if isinstance(message, str):
            return message
        return None
