from __future__ import annotations

"""Model-catalog endpoints for the relay gateway's list and detail routes."""

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from lexigram.ai.relay.gateway.web.routes.common import ResolveModelCatalog
from lexigram.ai.relay.gateway.web.shared import _error_response, _safe_headers
from lexigram.contracts.ai.relay import RelayFormat, RelayGatewayError
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.identity.ambient import new_uuid


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
