"""Shared request/response helpers for the relay gateway web layer.

Error envelopes, body parsing, and header filtering are common to every
inbound route family (chat relay, passthrough, audio, images, job
relay).  They live here so endpoint modules can share them without
importing from ``routes`` and forming an import cycle.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, TypeAlias

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from lexigram.ai.relay.gateway.passthrough import PassthroughService
from lexigram.ai.relay.gateway.ratelimit import RelayRateLimiter
from lexigram.contracts.ai.relay import (
    RelayAuthError,
    RelayAuthIdentity,
    RelayAuthVerifierProtocol,
    RelayFormat,
    RelayGatewayError,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.serialization import loads

__all__ = [
    "_DEFAULT_ERROR_TYPES",
    "_ERROR_TYPE_MAP",
    "_HOP_BY_HOP_HEADERS",
    "ResolvePassthrough",
    "_error_response",
    "_error_types",
    "_parse_body",
    "_safe_headers",
    "auth_guard",
    "rate_limit_guard",
]

ResolvePassthrough: TypeAlias = Callable[[Request], Awaitable[PassthroughService]]
"""Resolver of a passthrough service from a Starlette request."""

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


async def auth_guard(
    request: Request,
    verifier: RelayAuthVerifierProtocol | None,
    handler: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Guard one inbound relay request with the bound verifier, if any.

    Args:
        request: The inbound Starlette request.
        verifier: The resolved verifier; ``None`` (or a host that has
            not bound one) lets the request through untouched.
        handler: The wrapped route handler.

    Returns:
        The handler's response when no verifier is bound or the caller
        authenticates (identity stored on ``request.state.relay_identity``);
        a 401 authentication-error envelope otherwise.
    """
    if verifier is None:
        return await handler(request)
    result = await verifier.authenticate(request)
    if result.is_err():
        return _auth_error_response(result.unwrap_err())
    request.state.relay_identity = result.unwrap()
    return await handler(request)


def _auth_error_response(err: RelayAuthError) -> JSONResponse:
    """Build the 401 authentication-error envelope."""
    return JSONResponse(
        {
            "error": {
                "type": "authentication_error",
                "code": err.code,
                "message": err.message,
                "param": None,
            }
        },
        status_code=401,
    )


async def rate_limit_guard(
    request: Request, limiter: RelayRateLimiter | None
) -> Response | None:
    """Reject one authenticated request when over its rate-limit budget.

    Composed inside ``auth_guard``'s allow path, so it only sees callers
    that authenticated (``request.state.relay_identity`` set).  The model
    comes from the Gemini path parameter or the request body; a missing
    identity, missing model, or malformed body passes through so the
    handler renders its own 400 for invalid payloads.  ``request.body()``
    is cached by Starlette, so the handler still reads the body once.

    Args:
        request: The inbound Starlette request.
        limiter: The resolved limiter; ``None`` (no rules configured or
            no container) passes the request through untouched.

    Returns:
        ``None`` when the request may proceed; a 429
        ``rate_limit_error`` envelope with ``retry_after_seconds``
        otherwise.
    """
    if limiter is None:
        return None
    identity = getattr(request.state, "relay_identity", None)
    if not isinstance(identity, RelayAuthIdentity):
        return None
    model: Any = request.path_params.get("model")
    if not isinstance(model, str) or not model:
        try:
            body = loads(await request.body())
        except (TypeError, ValueError):
            return None
        if not isinstance(body, dict):
            return None
        model = body.get("model")
        if not isinstance(model, str) or not model:
            return None
    decision = await limiter.check(identity, model)
    if decision is None or decision.allowed:
        return None
    return JSONResponse(
        {
            "error": {
                "type": "rate_limit_error",
                "code": "RATE_LIMITED",
                "retry_after_seconds": decision.ttl_seconds,
            }
        },
        status_code=429,
    )


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
