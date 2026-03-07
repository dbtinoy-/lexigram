"""Audio passthrough endpoints for the relay gateway web layer.

The three OpenAI-shaped audio endpoints — speech synthesis, audio
transcription, and audio translation — are served through
``PassthroughService`` exactly like the generic passthrough routes, with
two differences: transcription/translation submissions arrive as
``multipart/form-data`` (raw bytes with the model lifted from the
``model`` form field and the body forwarded byte-for-byte) and upstream
audio responses are returned as their raw body bytes verbatim instead of
being dropped.  JSON submissions (speech) keep the decoded-object path
with ``RelayPassthroughBody.json``; multipart submissions carry their
original content type so the provider sees the boundary untouched.
Failures render in the OpenAI error envelope through the same machinery
as the other passthrough routes.

This module owns its route table and endpoint handlers only; mounting
them to the web contributor is handled by the routes coordinator.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, TypeAlias

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from lexigram.ai.relay.gateway.passthrough import (
    PassthroughService,
    RelayPassthroughBody,
    RelayPassthroughResult,
    rewrite_multipart_form_field,
)
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.identity.ambient import new_uuid
from lexigram.serialization import loads

__all__ = [
    "AUDIO_ROUTE_TABLE",
    "audio_speech_endpoint",
    "audio_transcriptions_endpoint",
    "audio_translations_endpoint",
]

ResolvePassthrough: TypeAlias = Callable[[Request], Awaitable[PassthroughService]]

AUDIO_ROUTE_TABLE: tuple[tuple[str, str], ...] = (
    ("/v1/audio/speech", "audio_speech"),
    ("/v1/audio/transcriptions", "audio_transcriptions"),
    ("/v1/audio/translations", "audio_translations"),
)
"""Inbound path to endpoint kind for the audio passthrough routes."""

_MULTIPART_MEDIA_TYPE = "multipart/form-data"

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

_ERROR_TYPE_MAP: dict[int, str] = {
    400: "invalid_request_error",
    401: "authentication_error",
    403: "permission_denied_error",
    404: "invalid_request_error",
    409: "conflict_error",
    429: "rate_limit_error",
    499: "cancelled_error",
    502: "server_error",
    504: "server_error",
}
"""Per-status OpenAI error type names for the audio error envelope."""

_FORM_FIELD_HEADER_MARKER = b'name="'
_FORM_FIELD_HEADER_SUFFIX = b'"'
"""Multipart ``Content-Disposition`` attribute delimiters used by field lookups."""


def _content_type(request: Request) -> str:
    """Return the request's content-type header value or empty string."""
    return request.headers.get("content-type", "")


def _is_multipart(content_type: str) -> bool:
    """Tell whether a content-type value denotes ``multipart/form-data``.

    Args:
        content_type: A content-type header value.

    Returns:
        ``True`` for the ``multipart/form-data`` media type regardless
        of parameters (e.g. the boundary).
    """
    return content_type.partition(";")[0].strip().lower() == _MULTIPART_MEDIA_TYPE


def _multipart_boundary(content_type: str) -> str | None:
    """Extract the ``boundary`` parameter from a content-type header.

    Args:
        content_type: The raw content-type header value.

    Returns:
        The boundary token without surrounding quotes, or ``None`` when
        the multipart header carries no boundary parameter.
    """
    for parameter in content_type.split(";"):
        key, separator, raw_value = parameter.strip().partition("=")
        if separator and key.lower() == "boundary" and raw_value.strip('"'):
            return raw_value.strip().strip('"')
    return None


def _extract_multipart_model(body: bytes, boundary: str) -> str | None:
    """Extract the ``model`` form field value from a multipart body.

    Narrow boundary-aware lookup mirroring the passthrough rewrite
    helper: the body is split on the ``--<boundary>`` framing marker and
    the first part whose ``Content-Disposition`` header carries
    ``name="model"`` has its value content read.

    Args:
        body: The raw ``multipart/form-data`` body bytes.
        boundary: The boundary token from the content-type header.

    Returns:
        The model field value, or ``None`` when the body has no
        ``model`` field or no boundary marker.
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
        value_end = len(part) - 2 if part.endswith(b"\r\n") else len(part)
        return part[separator + 4 : value_end].decode("utf-8", "ignore").strip()
    return None


def _parse_json(raw: bytes) -> dict[str, Any] | None:
    """Decode a JSON request body into an object, or ``None`` when malformed.

    Args:
        raw: The raw request body bytes.

    Returns:
        The decoded JSON object, or ``None`` for malformed JSON and
        non-object roots.
    """
    try:
        decoded = loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


def _tenant_id(request: Request) -> str:
    """Read the tenant id from the auth middleware's normalized user dict.

    Args:
        request: The Starlette request being served.

    Returns:
        The ``tenant_id`` (or ``tenant``) value when the state user is a
        dict carrying one, otherwise an empty string.
    """
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        return ""
    tenant = user.get("tenant_id") or user.get("tenant")
    if isinstance(tenant, str):
        return tenant
    return ""


def _error_response(request_id: str, error: RelayGatewayError) -> Response:
    """Build the OpenAI error envelope for a gateway failure.

    Never includes request payloads, headers, or tracebacks; only the
    safe error fields the protocol documents.

    Args:
        request_id: Request id stamped on the error.
        error: The gateway error to render.

    Returns:
        A JSON response with the OpenAI error envelope and the error's
        status code.
    """
    return JSONResponse(
        content={
            "error": {
                "message": error.message,
                "type": _ERROR_TYPE_MAP.get(error.status_code, "server_error"),
                "code": error.code,
                "request_id": request_id,
            }
        },
        status_code=error.status_code,
    )


def _invalid_request(request_id: str, message: str) -> Response:
    """Build a 400 OpenAI error envelope for a malformed request.

    Args:
        request_id: Request id stamped on the error.
        message: Safe error message.

    Returns:
        A 400 JSON response with the OpenAI error envelope.
    """
    return _error_response(
        request_id,
        RelayGatewayError(
            code=RelayGatewayErrorCode.INVALID_REQUEST,
            message=message,
            status_code=400,
            request_id=request_id,
        ),
    )


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


def _render_result(
    ok_result: RelayPassthroughResult,
    request_id: str,
    trace_id: str,
) -> Response:
    """Render a passthrough result as JSON or verbatim raw bytes.

    JSON responses keep their decoded payload through the ``payload``
    accessor; non-JSON responses (e.g. ``audio/mpeg``) ride in ``body``
    uninterpreted with their content type.

    Args:
        ok_result: The successful passthrough result.
        request_id: Request id stamped as ``x-request-id``.
        trace_id: Trace id stamped as ``x-trace-id`` when non-empty.

    Returns:
        ``JSONResponse`` for JSON results, a raw ``Response`` carrying
        the body bytes for audio results, or ``204`` when the result has
        neither payload nor body.
    """
    headers = _safe_headers(ok_result.headers, request_id, trace_id)
    if ok_result.payload is not None:
        return JSONResponse(
            content=ok_result.payload,
            status_code=ok_result.status_code,
            headers=headers,
        )
    if ok_result.body:
        headers.setdefault(
            "content-type", ok_result.content_type or "application/octet-stream"
        )
        return Response(
            content=ok_result.body,
            status_code=ok_result.status_code,
            headers=headers,
        )
    return Response(status_code=204, headers=headers)


async def _handle_audio(
    kind: str,
    resolve_passthrough: ResolvePassthrough,
    request: Request,
) -> Response:
    """Serve one audio passthrough request.

    The request body is read exactly once and shaped into a
    ``RelayPassthroughBody``: decoded JSON for JSON submissions, or raw
    bytes with the content type intact for ``multipart/form-data``
    submissions (with the ``model`` field rewritten from the extracted
    value).  The passthrough service is resolved per request, never
    cached.

    Args:
        kind: The endpoint kind owned by this route.
        resolve_passthrough: Resolver of the passthrough service.
        request: The Starlette request being served.

    Returns:
        The upstream payload rendered (JSON or raw audio bytes), or the
        OpenAI error envelope for gateway failures and malformed
        requests.
    """
    raw = await request.body()
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    content_type = _content_type(request)
    if _is_multipart(content_type):
        boundary = _multipart_boundary(content_type)
        if boundary is None:
            return _invalid_request(
                request_id, "multipart body must declare a boundary"
            )
        model = _extract_multipart_model(raw, boundary)
        if model is None or not model:
            return _invalid_request(request_id, "model is required")
        payload = RelayPassthroughBody.raw(
            rewrite_multipart_form_field(raw, boundary, "model", model),
            content_type,
        )
    else:
        decoded = _parse_json(raw)
        if decoded is None:
            return _invalid_request(request_id, "malformed JSON body")
        model = decoded.get("model")
        if not isinstance(model, str) or not model:
            return _invalid_request(request_id, "model is required")
        payload = RelayPassthroughBody.json(decoded)
    gateway_request = RelayGatewayRequest(
        request_id=request_id,
        tenant_id=_tenant_id(request),
        source=RelayFormat.OPENAI_CHAT,
        model=model,
        stream=False,
        payload=payload,
        headers=dict(request.headers.items()),
        channel=None,
    )
    service = await resolve_passthrough(request)
    result = await service.handle(kind, gateway_request)
    if result.is_err():
        return _error_response(request_id, result.unwrap_err())
    ok_result = result.unwrap()
    return _render_result(ok_result, request_id, trace_id)


async def audio_speech_endpoint(
    resolve_passthrough: ResolvePassthrough,
    request: Request,
) -> Response:
    """Serve ``POST /v1/audio/speech``.

    JSON submissions (``{model, input, voice}``) forward decoded with
    the model resolved from the body; the upstream ``audio/mpeg``
    response returns verbatim.

    Args:
        resolve_passthrough: Resolver of the passthrough service.
        request: The Starlette request being served.

    Returns:
        The upstream payload rendered (JSON or raw audio), or the OpenAI
        error envelope for failures.
    """
    return await _handle_audio("audio_speech", resolve_passthrough, request)


async def audio_transcriptions_endpoint(
    resolve_passthrough: ResolvePassthrough,
    request: Request,
) -> Response:
    """Serve ``POST /v1/audio/transcriptions``.

    Multipart submissions forward raw bytes with a boundary-aware
    ``model`` field rewrite; JSON submissions follow the decoded path.

    Args:
        resolve_passthrough: Resolver of the passthrough service.
        request: The Starlette request being served.

    Returns:
        The upstream payload rendered as JSON or raw audio bytes, or the
        OpenAI error envelope for failures.
    """
    return await _handle_audio("audio_transcriptions", resolve_passthrough, request)


async def audio_translations_endpoint(
    resolve_passthrough: ResolvePassthrough,
    request: Request,
) -> Response:
    """Serve ``POST /v1/audio/translations``.

    Multipart submissions forward raw with the model lifted from the
    ``model`` form field; JSON submissions follow the decoded path.

    Args:
        resolve_passthrough: Resolver of the passthrough service.
        request: The Starlette request being served.

    Returns:
        The upstream payload rendered as JSON or raw audio bytes, or the
        OpenAI error envelope for failures.
    """
    return await _handle_audio("audio_translations", resolve_passthrough, request)
