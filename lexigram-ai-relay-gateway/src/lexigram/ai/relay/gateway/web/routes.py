"""Inbound relay HTTP routes for the gateway web layer.

Each route owns one inbound wire format (OpenAI Chat, OpenAI Responses,
Claude, Gemini) and serves it through a shared endpoint.  The gateway
implementation is resolved at request time from the request-scoped DI
container.  Buffered results return JSON; streaming results return SSE
frames in the client's own protocol; failures render in the inbound
protocol's error envelope with safe, filtered headers.

Passthrough routes (``POST /v1/embeddings``, ``/v1/rerank``,
``/v1/moderations``, the ``/v1/audio/*`` and ``/v1/images/*`` routes)
serve non-chat endpoint kinds through ``PassthroughService`` with the
same request resolution, header filtering, and error envelope machinery,
without any wire-format conversion.  Job-relay routes (``POST
/v1/videos`` and ``GET /v1/videos/{job_id}``) serve submit-then-poll
endpoint kinds through ``JobPassthroughService`` with the same envelope
machinery.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from functools import partial
from typing import Any, TypeAlias

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.job_passthrough import JobPassthroughService
from lexigram.ai.relay.gateway.web.audio_endpoints import (
    AUDIO_ROUTE_TABLE,
    audio_speech_endpoint,
    audio_transcriptions_endpoint,
    audio_translations_endpoint,
)
from lexigram.ai.relay.gateway.web.image_endpoints import (
    IMAGE_ROUTE_TABLE,
    build_image_routes,
)
from lexigram.ai.relay.gateway.web.shared import (
    ResolvePassthrough,
    _error_response,
    _parse_body,
    _safe_headers,
    auth_guard,
)
from lexigram.ai.relay.gateway.web.sse import SSEEncoder
from lexigram.contracts.ai.relay import (
    RelayAuthVerifierProtocol,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayProtocol,
    RelayGatewayRequest,
    RelayWireEvent,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.identity.ambient import new_uuid

__all__ = ["RELAY_ROUTE_PATHS", "build_routes", "relay_endpoint"]

ResolveGateway: TypeAlias = Callable[[Request], Awaitable[RelayGatewayProtocol]]
"""Resolver of a gateway implementation from a Starlette request."""

ResolveJobPassthrough: TypeAlias = Callable[[Request], Awaitable[JobPassthroughService]]
"""Resolver of a job passthrough service from a Starlette request."""

_ROUTE_TABLE: tuple[tuple[str, RelayFormat], ...] = (
    ("/v1/chat/completions", RelayFormat.OPENAI_CHAT),
    ("/v1/responses", RelayFormat.OPENAI_RESPONSES),
    ("/v1/messages", RelayFormat.CLAUDE),
    ("/v1beta/models/{model}:generateContent", RelayFormat.GEMINI),
)
"""Inbound path to wire format ownership per route."""

_PASSTHROUGH_ROUTE_TABLE: tuple[tuple[str, str], ...] = (
    ("/v1/embeddings", "embeddings"),
    ("/v1/rerank", "rerank"),
    ("/v1/moderations", "moderation"),
)
"""Inbound path to endpoint kind for passthrough routes."""

_JOB_ROUTE_TABLE: tuple[tuple[str, str], ...] = (("/v1/videos", "video_generation"),)
"""Inbound submit path to endpoint kind for job-relay routes."""

_JOB_STATUS_PATH = "/v1/videos/{job_id}"
"""Inbound poll path for the registered job-relay endpoint kinds."""

_AUDIO_HANDLERS = {
    "audio_speech": audio_speech_endpoint,
    "audio_transcriptions": audio_transcriptions_endpoint,
    "audio_translations": audio_translations_endpoint,
}
"""Endpoint kind to handler for the audio passthrough routes."""

RELAY_ROUTE_PATHS: tuple[str, ...] = tuple(
    path
    for path, _ in (
        *_ROUTE_TABLE,
        *_PASSTHROUGH_ROUTE_TABLE,
        *AUDIO_ROUTE_TABLE,
        *IMAGE_ROUTE_TABLE,
    )
)
"""Inbound relay paths registered by ``build_routes``, in route order."""


async def _resolve_verifier(request: Request) -> RelayAuthVerifierProtocol | None:
    """Resolve the verifier when auth is required, else ``None``."""
    container: Any = getattr(request.state, "container", None)
    if container is None:
        return None
    config = await container.resolve_optional(RelayGatewayConfig)
    if config is None or not config.require_auth:
        return None
    return await container.resolve_optional(RelayAuthVerifierProtocol)


def _with_auth_guard(
    handler: Callable[..., Awaitable[Response]],
) -> Callable[..., Awaitable[Response]]:
    """Wrap a route handler so auth runs first, preserving the open default."""

    async def guarded(request: Request) -> Response:
        verifier = await _resolve_verifier(request)
        return await auth_guard(request, verifier, handler)

    return guarded


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


async def job_submit_endpoint(
    kind: str,
    resolve_job_passthrough: ResolveJobPassthrough,
    request: Request,
) -> Response:
    """Serve one job-relay submit request in its own wire format.

    The body is read exactly once and forwarded verbatim: no format
    inference happens, so the request carries the conventional
    ``OPENAI_CHAT`` source marker and no channel hint.  Video is an
    OpenAI-shaped submit/poll convention, so failures render in the
    OpenAI error envelope through the same machinery as the passthrough
    routes.  The job passthrough service is resolved per request, never
    cached.

    Args:
        kind: The endpoint kind owned by this route.
        resolve_job_passthrough: Resolver of the job passthrough
            service.
        request: The Starlette request being served.

    Returns:
        The upstream JSON verbatim (with the id rewritten to the
        gateway-issued job id), ``204`` when the result carries no
        payload, or the OpenAI error envelope for gateway failures.
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
    service = await resolve_job_passthrough(request)
    result = await service.submit(kind, gateway_request)
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


async def job_status_endpoint(
    kind: str,
    resolve_job_passthrough: ResolveJobPassthrough,
    request: Request,
) -> Response:
    """Serve one job-relay status poll against a gateway-issued job id.

    The job id comes from the path, not the body: status polls carry no
    payload, so the gateway request built here carries an empty payload
    and model, and only identity and request id are meaningful.  The
    status call authorizes but never re-runs the billing pipeline, and
    failures render in the OpenAI error envelope like the other
    sighted routes.

    Args:
        kind: The endpoint kind owned by this route.
        resolve_job_passthrough: Resolver of the job passthrough
            service.
        request: The Starlette request being served.

    Returns:
        The upstream status JSON verbatim (with the id rewritten back to
        the gateway-issued job id), ``204`` when the result carries no
        payload, or the OpenAI error envelope for gateway failures.
    """
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    job_id = request.path_params.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        return _error_response(
            RelayFormat.OPENAI_CHAT,
            RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message="job_id is required",
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
        model="",
        stream=False,
        payload={},
        headers=dict(request.headers.items()),
        channel=None,
    )
    service = await resolve_job_passthrough(request)
    result = await service.status(kind, job_id, gateway_request)
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
    resolve_job_passthrough: ResolveJobPassthrough | None = None,
) -> list[Route]:
    """Build the relay POST routes bound to gateway resolvers.

    Args:
        resolve_gateway: Async callable resolving a ``RelayGatewayProtocol``
            from the request; wired to request-time DI by the contributor.
        resolve_passthrough: Optional async callable resolving a
            ``PassthroughService`` from the request; when provided, the
            passthrough routes (e.g. ``/v1/embeddings``), the audio
            routes (``/v1/audio/*``), and the image routes
            (``/v1/images/*``) are appended.
        resolve_job_passthrough: Optional async callable resolving a
            ``JobPassthroughService`` from the request; when provided,
            the job-relay routes (``POST /v1/videos`` and
            ``GET /v1/videos/{job_id}``) are appended.

    Returns:
        One ``Route`` per inbound relay format, in ``RELAY_ROUTE_PATHS``
        order, followed by the passthrough, audio, and image routes when
        their resolver is provided and the job-relay routes when theirs
        is.
    """
    routes = [
        Route(
            path,
            _with_auth_guard(partial(relay_endpoint, source, resolve_gateway)),
            methods=["POST"],
        )
        for path, source in _ROUTE_TABLE
    ]
    if resolve_passthrough is not None:
        routes.extend(
            Route(
                path,
                _with_auth_guard(
                    partial(passthrough_endpoint, kind, resolve_passthrough)
                ),
                methods=["POST"],
            )
            for path, kind in _PASSTHROUGH_ROUTE_TABLE
        )
        routes.extend(
            Route(
                path,
                _with_auth_guard(partial(_AUDIO_HANDLERS[kind], resolve_passthrough)),
                methods=["POST"],
            )
            for path, kind in AUDIO_ROUTE_TABLE
        )
        guarded_image_routes = [
            Route(
                route.path,
                _with_auth_guard(route.endpoint),
                methods=route.methods or ["POST"],
            )
            for route in build_image_routes(resolve_passthrough)
        ]
        routes.extend(guarded_image_routes)
    if resolve_job_passthrough is not None:
        routes.extend(
            Route(
                path,
                _with_auth_guard(
                    partial(job_submit_endpoint, kind, resolve_job_passthrough)
                ),
                methods=["POST"],
            )
            for path, kind in _JOB_ROUTE_TABLE
        )
        routes.extend(
            Route(
                _JOB_STATUS_PATH,
                _with_auth_guard(
                    partial(job_status_endpoint, kind, resolve_job_passthrough)
                ),
                methods=["GET"],
            )
            for _, kind in _JOB_ROUTE_TABLE
        )
    return routes


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
