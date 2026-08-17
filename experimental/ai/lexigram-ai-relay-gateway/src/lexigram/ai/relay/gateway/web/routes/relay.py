from __future__ import annotations

"""The relay endpoint serving chat, responses, messages and generateContent routes."""

from collections.abc import AsyncIterator
from time import monotonic
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from lexigram.ai.relay.gateway.web.routes.common import ResolveGateway, _log_dispatch
from lexigram.ai.relay.gateway.web.shared import (
    _error_response,
    _parse_body,
    _safe_headers,
)
from lexigram.ai.relay.gateway.web.sse import SSEEncoder
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayWireEvent,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.identity.ambient import new_uuid


async def relay_endpoint(
    source: RelayFormat,
    resolve_gateway: ResolveGateway,
    request: Request,
) -> Response:
    """Serve one inbound relay request in the client's wire protocol.

    The body is read exactly once, the request id falls back to a
    generated uuid when the middleware did not set one, and identity
    comes from the auth middleware's normalized user dict.  The gateway
    is resolved per request, never cached.  Finished dispatches are
    emitted through the request-log emitter (metadata only, best-effort).

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
    started = monotonic()
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
        error = result.unwrap_err()
        response = _error_response(source, error)
        await _log_dispatch(
            request, source, model_value, response.status_code, error.code, started
        )
        return response
    ok_result = result.unwrap()
    headers = _safe_headers(ok_result.headers, request_id, trace_id)
    if ok_result.stream is not None:
        response = _streaming_response(source, ok_result.stream, headers)
    elif ok_result.payload is not None:
        response = JSONResponse(
            content=ok_result.payload,
            status_code=ok_result.status_code,
            headers=headers,
        )
    else:
        response = Response(status_code=204, headers=headers)
    await _log_dispatch(request, source, model_value, response.status_code, "", started)
    return response


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
