"""Inbound relay HTTP routes for the gateway web layer.

Each route owns one inbound wire format (OpenAI Chat, OpenAI Responses,
Claude, Gemini) and serves it through a shared endpoint.  The gateway
implementation is resolved at request time from the request-scoped DI
container.  Buffered results return JSON; streaming results return SSE
frames in the client's own protocol; failures render in the inbound
protocol's error envelope with safe, filtered headers.

Passthrough routes (currently ``POST /v1/embeddings``) serve non-chat
endpoint kinds through ``PassthroughService`` with the same request
resolution, header filtering, and error envelope machinery, without any
wire-format conversion.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from functools import partial
from typing import Any, TypeAlias

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from lexigram.ai.relay.gateway.passthrough import PassthroughService
from lexigram.ai.relay.gateway.web.sse import SSEEncoder
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayProtocol,
    RelayGatewayRequest,
    RelayWireEvent,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.identity.ambient import new_uuid
from lexigram.serialization import loads

__all__ = ["RELAY_ROUTE_PATHS", "build_routes", "relay_endpoint"]

ResolveGateway: TypeAlias = Callable[[Request], Awaitable[RelayGatewayProtocol]]
"""Resolver of a gateway implementation from a Starlette request."""

ResolvePassthrough: TypeAlias = Callable[[Request], Awaitable[PassthroughService]]
"""Resolver of a passthrough service from a Starlette request."""

_ROUTE_TABLE: tuple[tuple[str, RelayFormat], ...] = (
    ("/v1/chat/completions", RelayFormat.OPENAI_CHAT),
    ("/v1/responses", RelayFormat.OPENAI_RESPONSES),
    ("/v1/messages", RelayFormat.CLAUDE),
    ("/v1beta/models/{model}:generateContent", RelayFormat.GEMINI),
)
"""Inbound path to wire format ownership per route."""

_PASSTHROUGH_ROUTE_TABLE: tuple[tuple[str, str], ...] = (
    ("/v1/embeddings", "embeddings"),
)
"""Inbound path to endpoint kind for passthrough routes."""

RELAY_ROUTE_PATHS: tuple[str, ...] = tuple(
    path for path, _ in (*_ROUTE_TABLE, *_PASSTHROUGH_ROUTE_TABLE)
)
"""Inbound relay paths registered by ``build_routes``, in route order."""

_HOP_BY_HOP_HEADERS: frozenset[str] = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
"""Hop-by-hop headers that must never be relayed to clients."""

_ERROR_TYPE_MAP: dict[int, tuple[str, str, str]] = {
    400: ("invalid_request_error", "invalid_request_error", "INVALID_ARGUMENT"),
    401: ("authentication_error", "authentication_error", "UNAUTHENTICATED"),
    403: ("permission_denied_error", "permission_denied_error", "PERMISSION_DENIED"),
    404: ("invalid_request_error", "not_found_error", "NOT_FOUND"),
    409: ("conflict_error", "conflict_error", "FAILED_PRECONDITION"),
    429: ("rate_limit_error", "rate_limit_error", "RESOURCE_EXHAUSTED"),
    499: ("cancelled_error", "cancelled_error", "CANCELLED"),
    502: ("server_error", "api_error", "INTERNAL"),
    504: ("server_error", "api_error", "DEADLINE_EXCEEDED"),
}
"""Per-status error type names for the OpenAI, Claude, and Google families."""

_DEFAULT_ERROR_TYPES: tuple[str, str, str] = ("server_error", "api_error", "INTERNAL")
"""Error type names for every unmapped status code (including 500)."""


async def relay_endpoint(
    source: RelayFormat,
    resolve_gateway: ResolveGateway,
    request: Request,
) -> Response:
    """Serve one inbound relay request in the client's wire protocol.

    The body is read exactly once, the request id falls back to a
    generated uuid when the middleware did not set one, and identity
    comes from the auth middleware's normalized user dict.  The gateway
    is resolved per request, never cached.

    Args:
        source: The inbound wire format owned by this route.
        resolve_gateway: Resolver of the gateway implementation.
        request: The Starlette request being served.

    Returns:
        The protocol-appropriate response: JSON for buffered results,
        an SSE ``StreamingResponse`` for streaming results, ``204`` for
        results with neither payload nor stream, or the inbound error
        envelope for gateway failures.
    """
    raw = await request.body()
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    body = _parse_body(raw, source, request_id)
    if isinstance(body, Response):
        return body
    stream = bool(body.get("stream", False))
    model_value: Any = (
        request.path_params.get("model") if source == RelayFormat.GEMINI else None
    )
    if not isinstance(model_value, str) or not model_value:
        model_value = body.get("model")
    if not isinstance(model_value, str) or not model_value:
        return _error_response(
            source,
            RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message="model is required",
                status_code=400,
                request_id=request_id,
            ),
        )
    user = getattr(request.state, "user", None)
    tenant_id = ""
    if isinstance(user, dict):
        tenant = user.get("tenant_id") or user.get("tenant")
        if isinstance(tenant, str):
            tenant_id = tenant
    gateway_request = RelayGatewayRequest(
        request_id=request_id,
        tenant_id=tenant_id,
        source=source,
        model=model_value,
        stream=stream,
        payload=body,
        headers=dict(request.headers.items()),
        channel=None,
    )
    gateway = await resolve_gateway(request)
    result = await gateway.handle(gateway_request)
    if result.is_err():
        return _error_response(source, result.unwrap_err())
    ok_result = result.unwrap()
    headers = _safe_headers(ok_result.headers, request_id, trace_id)
    if ok_result.stream is not None:
        return _streaming_response(source, ok_result.stream, headers)
    if ok_result.payload is not None:
        return JSONResponse(
            content=ok_result.payload,
            status_code=ok_result.status_code,
            headers=headers,
        )
    return Response(status_code=204, headers=headers)


async def passthrough_endpoint(
    kind: str,
    resolve_passthrough: ResolvePassthrough,
    request: Request,
) -> Response:
    """Serve one inbound passthrough request in its own wire format.

    The body is read exactly once and forwarded verbatim: no format
    inference happens, so the request carries the conventional
    ``OPENAI_CHAT`` source marker and no channel hint.  The passthrough
    service is resolved per request, never cached.  Embeddings is an
    OpenAI-shaped endpoint by convention, so failures render in the
    OpenAI error envelope through the same machinery as the chat routes.

    Args:
        kind: The endpoint kind owned by this route.
        resolve_passthrough: Resolver of the passthrough service.
        request: The Starlette request being served.

    Returns:
        The upstream JSON verbatim, ``204`` when the result carries
        neither payload nor stream, or the OpenAI error envelope for
        gateway failures.
    """
    raw = await request.body()
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    body = _parse_body(raw, RelayFormat.OPENAI_CHAT, request_id)
    if isinstance(body, Response):
        return body
    model_value = body.get("model")
    if not isinstance(model_value, str) or not model_value:
        return _error_response(
            RelayFormat.OPENAI_CHAT,
            RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message="model is required",
                status_code=400,
                request_id=request_id,
            ),
        )
    user = getattr(request.state, "user", None)
    tenant_id = ""
    if isinstance(user, dict):
        tenant = user.get("tenant_id") or user.get("tenant")
        if isinstance(tenant, str):
            tenant_id = tenant
    gateway_request = RelayGatewayRequest(
        request_id=request_id,
        tenant_id=tenant_id,
        source=RelayFormat.OPENAI_CHAT,
        model=model_value,
        stream=False,
        payload=body,
        headers=dict(request.headers.items()),
        channel=None,
    )
    service = await resolve_passthrough(request)
    result = await service.handle(kind, gateway_request)
    if result.is_err():
        return _error_response(RelayFormat.OPENAI_CHAT, result.unwrap_err())
    ok_result = result.unwrap()
    headers = _safe_headers(ok_result.headers, request_id, trace_id)
    if ok_result.payload is not None:
        return JSONResponse(
            content=ok_result.payload,
            status_code=ok_result.status_code,
            headers=headers,
        )
    return Response(status_code=204, headers=headers)


def build_routes(
    resolve_gateway: ResolveGateway,
    *,
    resolve_passthrough: ResolvePassthrough | None = None,
) -> list[Route]:
    """Build the relay POST routes bound to gateway resolvers.

    Args:
        resolve_gateway: Async callable resolving a ``RelayGatewayProtocol``
            from the request; wired to request-time DI by the contributor.
        resolve_passthrough: Optional async callable resolving a
            ``PassthroughService`` from the request; when provided, the
            passthrough routes (e.g. ``/v1/embeddings``) are appended.

    Returns:
        One ``Route`` per inbound relay format, in ``RELAY_ROUTE_PATHS``
        order.
    """
    routes = [
        Route(
            path,
            partial(relay_endpoint, source, resolve_gateway),
            methods=["POST"],
        )
        for path, source in _ROUTE_TABLE
    ]
    if resolve_passthrough is not None:
        routes.extend(
            Route(
                path,
                partial(passthrough_endpoint, kind, resolve_passthrough),
                methods=["POST"],
            )
            for path, kind in _PASSTHROUGH_ROUTE_TABLE
        )
    return routes


def _parse_body(
    raw: bytes, source: RelayFormat, request_id: str
) -> dict[str, Any] | Response:
    """Decode the request body, returning a 400 response when malformed.

    Args:
        raw: The raw request body bytes.
        source: The inbound wire format for the error envelope.
        request_id: Request id stamped on the error.

    Returns:
        The decoded JSON object, or a 400 ``INVALID_REQUEST`` response
        for malformed JSON, non-object roots, and empty bodies.
    """
    try:
        decoded = loads(raw)
    except (TypeError, ValueError):
        return _error_response(
            source,
            RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message="malformed JSON body",
                status_code=400,
                request_id=request_id,
            ),
        )
    if not isinstance(decoded, dict):
        return _error_response(
            source,
            RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message="request body must be a JSON object",
                status_code=400,
                request_id=request_id,
            ),
        )
    return decoded


def _safe_headers(
    headers: Mapping[str, str], request_id: str, trace_id: str
) -> dict[str, str]:
    """Filter result headers and stamp request metadata.

    Drops ``set-cookie`` and all hop-by-hop headers case-insensitively,
    keeps everything else, and always adds ``x-request-id`` plus
    ``x-trace-id`` when a trace id was provided.

    Args:
        headers: The result headers to filter.
        request_id: Request id stamped as ``x-request-id``.
        trace_id: Trace id stamped as ``x-trace-id`` when non-empty.

    Returns:
        The safe header dict.
    """
    safe: dict[str, str] = {}
    for key, value in headers.items():
        lowered = key.lower()
        if lowered == "set-cookie" or lowered in _HOP_BY_HOP_HEADERS:
            continue
        safe[key] = value
    safe["x-request-id"] = request_id
    if trace_id:
        safe["x-trace-id"] = trace_id
    return safe


def _streaming_response(
    source: RelayFormat,
    stream: AsyncIterator[RelayWireEvent],
    headers: dict[str, str],
) -> StreamingResponse:
    """Build the SSE response, framing events in the client's protocol.

    Args:
        source: The client's wire format; frames follow its syntax.
        stream: The gateway's normalized event stream.
        headers: Safe headers; ``cache-control`` and ``connection`` are
            added here.

    Returns:
        A ``text/event-stream`` streaming response over the framed
        events, with the protocol terminator emitted exactly once.
    """
    headers["cache-control"] = "no-cache"
    headers["connection"] = "keep-alive"
    encoder = SSEEncoder(source)

    async def frames() -> AsyncIterator[bytes]:
        terminal_event: RelayWireEvent | None = None
        async for event in stream:
            if event.terminal:
                terminal_event = event
            yield encoder.encode(event)
            if event.terminal:
                break
        final = encoder.encode_terminal(source, terminal_event)
        if final:
            yield final

    return StreamingResponse(frames(), media_type="text/event-stream", headers=headers)


def _error_types(status_code: int) -> tuple[str, str, str]:
    """Map an HTTP status to per-protocol error type names.

    Args:
        status_code: The gateway error's status code.

    Returns:
        ``(openai_type, claude_type, google_status)`` for the status;
        the server-error triple for unmapped statuses.
    """
    return _ERROR_TYPE_MAP.get(status_code, _DEFAULT_ERROR_TYPES)


def _error_response(source: RelayFormat, error: RelayGatewayError) -> Response:
    """Build the inbound-protocol error envelope for a gateway error.

    Never includes request payloads, headers, or tracebacks; only the
    safe error fields the protocol documents.

    Args:
        source: The inbound wire format determining the envelope shape.
        error: The gateway error to render.

    Returns:
        A JSON response with the protocol's error envelope and the
        error's status code.
    """
    openai_type, claude_type, google_status = _error_types(error.status_code)
    if source == RelayFormat.OPENAI_CHAT:
        envelope: dict[str, Any] = {
            "error": {
                "message": error.message,
                "type": openai_type,
                "code": error.code,
                "request_id": error.request_id,
            }
        }
    elif source == RelayFormat.OPENAI_RESPONSES:
        envelope = {
            "error": {
                "message": error.message,
                "type": openai_type,
                "code": error.code,
            }
        }
    elif source == RelayFormat.CLAUDE:
        envelope = {
            "type": "error",
            "error": {"type": claude_type, "message": error.message},
        }
    else:
        envelope = {
            "error": {
                "code": error.status_code,
                "message": error.message,
                "status": google_status,
            }
        }
    return JSONResponse(content=envelope, status_code=error.status_code)
