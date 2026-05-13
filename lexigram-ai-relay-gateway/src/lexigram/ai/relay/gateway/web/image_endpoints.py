"""Image passthrough routes for the relay gateway web layer.

``POST /v1/images/generations`` and ``POST /v1/images/edits`` serve
image endpoint kinds through the same ``PassthroughService`` as the
embeddings route: same request resolution, header filtering, and OpenAI
error envelope machinery, with no wire-format conversion.  Generations
bodies are JSON and forward encoded unchanged; edits bodies are
``multipart/form-data`` and forward byte-for-byte with the ``model``
form field lifted into the gateway request so channel selection and
model-suffix substitution work without ever parsing the body as JSON.
Responses pass through verbatim: decoded JSON when the upstream returned
JSON, raw bytes otherwise, ``204`` when the result carries neither.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from lexigram.ai.relay.gateway.passthrough import RelayPassthroughBody
from lexigram.ai.relay.gateway.web.routes import (
    ResolvePassthrough,
    _error_response,
    _parse_body,
    _safe_headers,
)
from lexigram.contracts.ai.relay import (
    JsonValue,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.identity.ambient import new_uuid

__all__ = [
    "IMAGE_ROUTE_PATHS",
    "IMAGE_ROUTE_TABLE",
    "build_image_routes",
    "image_endpoint",
]

IMAGE_ROUTE_TABLE: tuple[tuple[str, str], ...] = (
    ("/v1/images/generations", "image_generation"),
    ("/v1/images/edits", "image_edit"),
)
"""Inbound path to endpoint kind for image passthrough routes."""

IMAGE_ROUTE_PATHS: tuple[str, ...] = tuple(path for path, _ in IMAGE_ROUTE_TABLE)
"""Inbound image paths registered by ``build_image_routes``."""

_FORM_FIELD_HEADER_MARKER = b'name="'
_FORM_FIELD_HEADER_SUFFIX = b'"'
"""Multipart ``Content-Disposition`` attribute delimiters used by the model read."""

_MULTIPART_MEDIA_TYPE = "multipart/form-data"


async def image_endpoint(
    kind: str,
    resolve_passthrough: ResolvePassthrough,
    request: Request,
) -> Response:
    """Serve one inbound image request in its own wire format.

    The body is read exactly once.  Generations bodies are JSON and
    parse exactly once, like ``passthrough_endpoint``; edits bodies are
    ``multipart/form-data`` and travel verbatim with the ``model`` form
    field lifted into the gateway request, so a raw multipart body can
    never be mistaken for JSON.  The service is resolved per request,
    never cached. Image endpoints are OpenAI-shaped by convention, so
    failures render in the OpenAI error envelope.

    Args:
        kind: The image endpoint kind owned by this route.
        resolve_passthrough: Resolver of the passthrough service.
        request: The Starlette request being served.

    Returns:
        The upstream payload JSON verbatim, the upstream binary body
        verbatim, ``204`` when the result carries neither, or the OpenAI
        error envelope for gateway failures.
    """
    raw = await request.body()
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    content_type = request.headers.get("content-type", "application/json")
    if _is_multipart(content_type):
        boundary = _multipart_boundary(content_type)
        model_value = _multipart_model_value(raw, boundary) if boundary else None
        if not model_value:
            return _model_required_error(request_id)
        payload: Mapping[str, JsonValue] | RelayPassthroughBody = (
            RelayPassthroughBody.raw(raw, content_type)
        )
    else:
        body = _parse_body(raw, RelayFormat.OPENAI_CHAT, request_id)
        if isinstance(body, Response):
            return body
        model_value = body.get("model")
        if not isinstance(model_value, str) or not model_value:
            return _model_required_error(request_id)
        payload = body
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
        payload=payload,
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
    if ok_result.body:
        headers = {**headers, "content-type": ok_result.content_type}
        return Response(
            content=ok_result.body,
            status_code=ok_result.status_code,
            headers=headers,
        )
    return Response(status_code=204, headers=headers)


def build_image_routes(
    resolve_passthrough: ResolvePassthrough,
) -> list[Route]:
    """Build the image passthrough POST routes bound to a service resolver.

    Args:
        resolve_passthrough: Async callable resolving a
            ``PassthroughService`` from the request; wired to
            request-time DI by the contributor.

    Returns:
        One ``Route`` per image path, in ``IMAGE_ROUTE_PATHS`` order.
    """
    return [
        Route(
            path,
            partial(image_endpoint, kind, resolve_passthrough),
            methods=["POST"],
        )
        for path, kind in IMAGE_ROUTE_TABLE
    ]


def _is_multipart(content_type: str) -> bool:
    """Tell whether a content-type header denotes multipart form data.

    Args:
        content_type: A content-type header value.

    Returns:
        ``True`` for a ``multipart/form-data`` media type with or
        without parameters; ``False`` otherwise.
    """
    media_type = content_type.partition(";")[0].strip().lower()
    return media_type == _MULTIPART_MEDIA_TYPE


def _multipart_boundary(content_type: str) -> str | None:
    """Extract the ``boundary`` parameter from a content-type header.

    Args:
        content_type: The raw content-type header value.

    Returns:
        The boundary token without surrounding quotes, or ``None`` when
        the header carries no boundary parameter.
    """
    for parameter in content_type.split(";"):
        key, separator, raw_value = parameter.strip().partition("=")
        if separator and key.lower() == "boundary":
            return raw_value.strip().strip('"')
    return None


def _multipart_model_value(body: bytes, boundary: str) -> str | None:
    """Read the ``model`` form field's value from a multipart body.

    A narrow boundary-aware read (not a general multipart parser): the
    body is split on the ``--<boundary>`` framing marker and the first
    part whose ``Content-Disposition`` header carries ``name="model"``
    has its value character returned; every check mirrors
    ``rewrite_multipart_form_field`` so both functions agree on the
    same parts.

    Args:
        body: The raw ``multipart/form-data`` body bytes.
        boundary: The boundary token from the content-type header.

    Returns:
        The ``model`` field value, or ``None`` when the body has no
        model part (or no boundary marker at all).
    """
    marker = b"--" + boundary.encode("utf-8")
    target = _FORM_FIELD_HEADER_MARKER + b"model" + _FORM_FIELD_HEADER_SUFFIX
    segments = body.split(marker)
    if len(segments) < 2:
        return None
    for index in range(1, len(segments) - 1):
        part = segments[index]
        separator = part.find(b"\r\n\r\n")
        if separator < 0:
            continue
        headers = part[2:separator].lower()
        if target not in headers:
            continue
        value_start = separator + 4
        value_end = len(part) - 2 if part.endswith(b"\r\n") else len(part)
        value = part[value_start:value_end]
        if not value:
            return None
        return value.decode("utf-8", errors="replace")
    return None


def _model_required_error(request_id: str) -> Response:
    """Build the 400 OpenAI envelope for a missing image model field.

    Args:
        request_id: Request id stamped on the error.

    Returns:
        The ``INVALID_REQUEST`` envelope with status 400.
    """
    return _error_response(
        RelayFormat.OPENAI_CHAT,
        RelayGatewayError(
            code=RelayGatewayErrorCode.INVALID_REQUEST,
            message="model is required",
            status_code=400,
            request_id=request_id,
        ),
    )
