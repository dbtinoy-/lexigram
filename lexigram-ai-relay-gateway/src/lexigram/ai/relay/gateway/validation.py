"""Request validation for the relay gateway service.

``validate_gateway_request`` is the boundary check run by
``RelayGatewayService.handle`` before any dependency runs; malformed
requests short-circuit with ``Err(RelayGatewayError)`` (400) instead of
allowing malformed data to fail downstream.
"""

from __future__ import annotations

from collections.abc import Mapping

from lexigram.contracts.ai.relay import RelayGatewayError, RelayGatewayRequest
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode

__all__ = ["validate_gateway_request"]


def validate_gateway_request(
    request: RelayGatewayRequest,
) -> RelayGatewayError | None:
    """Reject malformed gateway requests before the pipeline runs.

    Args:
        request: The gateway request to validate.

    Returns:
        ``None`` when the request is well-formed, otherwise the
        ``INVALID_REQUEST`` gateway error describing the defect.
    """
    if not isinstance(request.request_id, str) or not request.request_id:
        message = "request_id is required"
        return RelayGatewayError(
            code=RelayGatewayErrorCode.INVALID_REQUEST,
            message=message,
            status_code=400,
            request_id=getattr(request, "request_id", None) or "",
        )
    if not isinstance(request.tenant_id, str) or not request.tenant_id:
        message = "tenant_id is required"
        return RelayGatewayError(
            code=RelayGatewayErrorCode.INVALID_REQUEST,
            message=message,
            status_code=400,
            request_id=request.request_id,
        )
    if not isinstance(request.model, str) or not request.model:
        message = "model is required"
        return RelayGatewayError(
            code=RelayGatewayErrorCode.INVALID_REQUEST,
            message=message,
            status_code=400,
            request_id=request.request_id,
        )
    if not isinstance(request.source, str) or not request.source:
        message = "source is required"
        return RelayGatewayError(
            code=RelayGatewayErrorCode.INVALID_REQUEST,
            message=message,
            status_code=400,
            request_id=request.request_id,
        )
    if not isinstance(request.payload, Mapping) or not request.payload:
        message = "payload must be a non-empty object"
        return RelayGatewayError(
            code=RelayGatewayErrorCode.INVALID_REQUEST,
            message=message,
            status_code=400,
            request_id=request.request_id,
        )
    messages = request.payload.get("messages")
    if messages is not None:
        if not isinstance(messages, list):
            message = "payload messages must be a list"
            return RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message=message,
                status_code=400,
                request_id=request.request_id,
            )
        if any(not isinstance(entry, Mapping) for entry in messages):
            message = "payload messages entries must be objects"
            return RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message=message,
                status_code=400,
                request_id=request.request_id,
            )
    if not isinstance(request.headers, Mapping):
        message = "headers must be an object"
        return RelayGatewayError(
            code=RelayGatewayErrorCode.INVALID_REQUEST,
            message=message,
            status_code=400,
            request_id=request.request_id,
        )
    return None
