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
from time import monotonic
from typing import Any, TypeAlias

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from lexigram.ai.relay.gateway.catalog import ModelCatalogService
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.job_passthrough import JobPassthroughService
from lexigram.ai.relay.gateway.logging import RelayRequestLogger
from lexigram.ai.relay.gateway.ratelimit import RelayRateLimiter
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
    _REQUIRE_AUTH_MISCONFIGURED,
    ResolvePassthrough,
    _error_response,
    _parse_body,
    _RequireAuthMisconfigured,
    _safe_headers,
    _status_for,
    auth_guard,
    log_request,
    rate_limit_guard,
)
from lexigram.ai.relay.gateway.web.sse import SSEEncoder
from lexigram.contracts.ai.relay import (
    RelayAuthVerifierProtocol,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayProtocol,
    RelayGatewayRequest,
    RelayRateLimitCounterProtocol,
    RelayRequestLogStoreProtocol,
    RelayWireEvent,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.identity.ambient import new_uuid

__all__ = [
    "MODEL_ROUTE_PATHS",
    "RELAY_ROUTE_PATHS",
    "build_routes",
    "relay_endpoint",
]

ResolveGateway: TypeAlias = Callable[[Request], Awaitable[RelayGatewayProtocol]]
"""Resolver of a gateway implementation from a Starlette request."""

ResolveJobPassthrough: TypeAlias = Callable[[Request], Awaitable[JobPassthroughService]]
"""Resolver of a job passthrough service from a Starlette request."""

ResolveModelCatalog: TypeAlias = Callable[[Request], Awaitable[ModelCatalogService]]
"""Resolver of the model catalog service from a Starlette request."""

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

_MODEL_LIST_PATHS: tuple[str, ...] = ("/v1/models", "/v1beta/models")
"""Inbound model-list paths; ``/v1beta/models`` is always Gemini."""
_MODEL_DETAIL_PATHS: tuple[str, ...] = (
    "/v1/models/{model}",
    "/v1beta/models/{model}",
)
"""Inbound model-detail paths; ``/v1beta/models/{model}`` is Gemini."""

MODEL_ROUTE_PATHS: tuple[str, ...] = (
    *_MODEL_LIST_PATHS,
    *_MODEL_DETAIL_PATHS,
)
"""Inbound model-list and detail paths registered by ``build_routes``.

The gemini ``/v1beta/models/{model}:generateContent`` relay path mounts
alongside these without colliding because the detail path is a distinct
pattern.
"""

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


async def _resolve_verifier(
    request: Request,
) -> RelayAuthVerifierProtocol | _RequireAuthMisconfigured | None:
    """Resolve the verifier when auth is required, else ``None``.

    ``None`` means auth is explicitly off (no config, or
    ``require_auth=False``).  When auth is required but no verifier is
    bound, the ``_RequireAuthMisconfigured`` sentinel is returned so
    ``auth_guard`` fails closed instead of passing through silently.
    """
    container: Any = getattr(request.state, "container", None)
    if container is None:
        return None
    config = await container.resolve_optional(RelayGatewayConfig)
    if config is None or not config.require_auth:
        return None
    verifier = await container.resolve_optional(RelayAuthVerifierProtocol)
    if verifier is None:
        return _REQUIRE_AUTH_MISCONFIGURED
    return verifier


async def _resolve_limiter(request: Request) -> RelayRateLimiter | None:
    """Build the limiter from config when rules are set, else ``None``.

    The counter comes from the container; an unbound counter leaves the
    limiter inert (pass-through), and an empty ``rate_limits`` map
    disables the guard entirely — today's behavior either way.
    """
    container: Any = getattr(request.state, "container", None)
    if container is None:
        return None
    config = await container.resolve_optional(RelayGatewayConfig)
    if config is None or not config.rate_limits:
        return None
    counter = await container.resolve_optional(RelayRateLimitCounterProtocol)
    return RelayRateLimiter(rules=config.rate_limits, counter=counter)


async def _resolve_logger(request: Request) -> RelayRequestLogger | None:
    """Resolve the request-log emitter, or ``None`` when no store is bound."""
    container: Any = getattr(request.state, "container", None)
    if container is None:
        return None
    store = await container.resolve_optional(RelayRequestLogStoreProtocol)
    if store is None:
        return None
    return RelayRequestLogger(store=store)


def _dispatch_latency_ms(started: float) -> int:
    """Round the monotonic dispatch span to whole milliseconds."""
    return round((monotonic() - started) * 1000)


_SOURCE_KIND: dict[RelayFormat, str] = {
    RelayFormat.OPENAI_CHAT: "chat",
    RelayFormat.OPENAI_RESPONSES: "responses",
    RelayFormat.CLAUDE: "messages",
    RelayFormat.GEMINI: "generateContent",
}
"""Wire format to request-log endpoint-kind label."""


async def _log_dispatch(
    request: Request,
    source: RelayFormat,
    model: str,
    status_code: int,
    error_code: str,
    started: float,
) -> None:
    """Emit the terminal dispatch entry through the resolved logger."""
    logger = await _resolve_logger(request)
    if logger is None:
        return
    log_request(
        request,
        logger,
        kind=_SOURCE_KIND[source],
        status=_status_for(status_code),
        model=model,
        error_code=error_code,
        latency_ms=_dispatch_latency_ms(started),
    )


def _with_auth_guard(
    handler: Callable[..., Awaitable[Response]],
) -> Callable[..., Awaitable[Response]]:
    """Wrap a route handler so auth and rate limiting run first.

    Auth is on by default; pass-through only happens when auth is
    explicitly opted out (``require_auth=False``) or no gateway config
    is present.
    """

    async def guarded(request: Request) -> Response:
        verifier = await _resolve_verifier(request)
        limiter = await _resolve_limiter(request)

        async def inner(req: Request) -> Response:
            blocked = await rate_limit_guard(req, limiter)
            if blocked is not None:
                return blocked
            return await handler(req)

        return await auth_guard(request, verifier, inner)

    return guarded


async def models_endpoint(
    forced_format: RelayFormat | None,
    resolve_catalog: ResolveModelCatalog,
    request: Request,
) -> Response:
    """Serve the model-list route in the client's wire protocol.

    ``/v1beta/models`` forces the Gemini shape; ``/v1/models`` sniffs the
    request for Google (``x-goog-api-key`` header or ``key`` query
    param) and Anthropic (``anthropic-version`` or ``x-api-key`` without
    the Google markers) conventions and falls back to the OpenAI shape.
    The catalog is resolved per request, never cached; responses carry
    the gateway's request-id and trace-id headers.

    Args:
        forced_format: Wire format to always use, or ``None`` to sniff
            the request headers.
        resolve_catalog: Resolver of the model catalog service.
        request: The Starlette request being served.

    Returns:
        The protocol-appropriate model list JSON.
    """
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    wire_format = forced_format or _model_list_format(request)
    catalog = await resolve_catalog(request)
    if wire_format == RelayFormat.GEMINI:
        payload: dict[str, Any] = catalog.list_gemini()
    elif wire_format == RelayFormat.CLAUDE:
        payload = catalog.list_claude()
    else:
        payload = catalog.list_openai()
    return JSONResponse(
        content=payload, headers=_safe_headers({}, request_id, trace_id)
    )


async def model_detail_endpoint(
    gemini: bool,
    resolve_catalog: ResolveModelCatalog,
    request: Request,
) -> Response:
    """Serve the model-detail route in the client's wire protocol.

    ``/v1beta/models/{model}`` renders the Gemini shape and
    ``/v1/models/{model}`` renders the OpenAI shape.  An alias no enabled
    channel serves renders the inbound error envelope with
    ``MODEL_NOT_FOUND``.

    Args:
        gemini: Whether the route is the ``/v1beta`` Gemini variant.
        resolve_catalog: Resolver of the model catalog service.
        request: The Starlette request being served.

    Returns:
        The protocol-appropriate model detail JSON, or the ``MODEL_NOT_FOUND``
        error envelope for unknown aliases.
    """
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    alias = request.path_params.get("model")
    if not isinstance(alias, str) or not alias:
        return _error_response(
            RelayFormat.GEMINI if gemini else RelayFormat.OPENAI_CHAT,
            RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message="model is required",
                status_code=400,
                request_id=request_id,
            ),
        )
    source = RelayFormat.GEMINI if gemini else RelayFormat.OPENAI_CHAT
    catalog = await resolve_catalog(request)
    payload = catalog.gemini_detail(alias) if gemini else catalog.openai_detail(alias)
    if payload is None:
        return _error_response(
            source,
            RelayGatewayError(
                code=RelayGatewayErrorCode.MODEL_NOT_FOUND,
                message=f"model {alias!r} is not served",
                status_code=404,
                request_id=request_id,
            ),
        )
    return JSONResponse(
        content=payload, headers=_safe_headers({}, request_id, trace_id)
    )


def _model_list_format(request: Request) -> RelayFormat:
    """Sniff the wire format for a model-list request.

    Google conventions win (``x-goog-api-key`` header or ``key`` query
    param), then Anthropic (``anthropic-version`` header), then OpenAI by
    default.

    Args:
        request: The Starlette request being served.

    Returns:
        The wire format whose list shape the response should use.
    """
    if "x-goog-api-key" in request.headers or "key" in request.query_params:
        return RelayFormat.GEMINI
    if "anthropic-version" in request.headers:
        return RelayFormat.CLAUDE
    return RelayFormat.OPENAI_CHAT


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
    started = monotonic()
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
        error = result.unwrap_err()
        response = _error_response(RelayFormat.OPENAI_CHAT, error)
        await _log_kind_dispatch(
            request, kind, model_value, response.status_code, error.code, started
        )
        return response
    ok_result = result.unwrap()
    headers = _safe_headers(ok_result.headers, request_id, trace_id)
    if ok_result.payload is not None:
        response = JSONResponse(
            content=ok_result.payload,
            status_code=ok_result.status_code,
            headers=headers,
        )
    else:
        response = Response(status_code=204, headers=headers)
    await _log_kind_dispatch(
        request, kind, model_value, response.status_code, "", started
    )
    return response


async def _log_kind_dispatch(
    request: Request,
    kind: str,
    model: str,
    status_code: int,
    error_code: str,
    started: float,
) -> None:
    """Emit a terminal dispatch entry for passthrough and job routes."""
    logger = await _resolve_logger(request)
    if logger is None:
        return
    log_request(
        request,
        logger,
        kind=kind,
        status=_status_for(status_code),
        model=model,
        error_code=error_code,
        latency_ms=_dispatch_latency_ms(started),
    )


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
    started = monotonic()
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
        error = result.unwrap_err()
        response = _error_response(RelayFormat.OPENAI_CHAT, error)
        await _log_kind_dispatch(
            request, kind, model_value, response.status_code, error.code, started
        )
        return response
    ok_result = result.unwrap()
    headers = _safe_headers(ok_result.headers, request_id, trace_id)
    if ok_result.payload is not None:
        response = JSONResponse(
            content=ok_result.payload,
            status_code=ok_result.status_code,
            headers=headers,
        )
    else:
        response = Response(status_code=204, headers=headers)
    await _log_kind_dispatch(
        request, kind, model_value, response.status_code, "", started
    )
    return response


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
    resolve_model_catalog: ResolveModelCatalog | None = None,
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
        resolve_model_catalog: Optional async callable resolving a
            ``ModelCatalogService`` from the request; when provided, the
            model-list and model-detail routes (``GET /v1/models``,
            ``GET /v1beta/models``, and their detail variants) are
            appended.

    Returns:
        One ``Route`` per inbound relay format, in ``RELAY_ROUTE_PATHS``
        order, followed by the passthrough, audio, image, job-relay, and
        model-catalog routes when their resolver is provided.
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
    if resolve_model_catalog is not None:
        routes.append(
            Route(
                "/v1beta/models",
                _with_auth_guard(
                    partial(models_endpoint, RelayFormat.GEMINI, resolve_model_catalog)
                ),
                methods=["GET"],
            )
        )
        routes.append(
            Route(
                "/v1/models",
                _with_auth_guard(partial(models_endpoint, None, resolve_model_catalog)),
                methods=["GET"],
            )
        )
        routes.append(
            Route(
                "/v1beta/models/{model}",
                _with_auth_guard(
                    partial(model_detail_endpoint, True, resolve_model_catalog)
                ),
                methods=["GET"],
            )
        )
        routes.append(
            Route(
                "/v1/models/{model}",
                _with_auth_guard(
                    partial(model_detail_endpoint, False, resolve_model_catalog)
                ),
                methods=["GET"],
            )
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
