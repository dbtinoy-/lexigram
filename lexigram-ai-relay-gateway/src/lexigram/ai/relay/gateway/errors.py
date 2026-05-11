"""Gateway error mapping helpers for the relay gateway service.

Converts engine-level ``RelayError`` values into gateway-level
``RelayGatewayError`` values and re-attaches request ids to registry and
upstream errors that were produced without one.
"""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.governance import RelayBillingError
from lexigram.contracts.ai.relay.gateway import (
    RelayGatewayError,
    RelayGatewayErrorCode,
)

__all__ = [
    "auth_denied",
    "billing_error_to_gateway",
    "conversion_error_to_gateway",
    "with_request_id",
]


def conversion_error_to_gateway(
    error: RelayError, request_id: str
) -> RelayGatewayError:
    """Map a converter engine error to a gateway error.

    Args:
        error: The ``RelayError`` returned by the converter engine. Its
            message is a domain message and is safe to propagate.
        request_id: Caller-supplied request id stamped on the result.

    Returns:
        A ``RelayGatewayError`` classified from the engine error code:
        malformed/unsupported payloads map to ``INVALID_REQUEST`` (400);
        every other engine failure maps to ``CONVERSION_FAILED`` (500).
        The error is never retryable.
    """
    if error.code in {
        RelayErrorCode.MALFORMED_PAYLOAD.value,
        RelayErrorCode.UNSUPPORTED_FORMAT.value,
        RelayErrorCode.UNSUPPORTED_FEATURE.value,
    }:
        code = RelayGatewayErrorCode.INVALID_REQUEST
        status_code = 400
    else:
        code = RelayGatewayErrorCode.CONVERSION_FAILED
        status_code = 500
    return RelayGatewayError(
        code=code,
        message=error.message,
        status_code=status_code,
        request_id=request_id,
        retryable=False,
    )


def auth_denied(request_id: str) -> RelayGatewayError:
    """Build the gateway error for an authorization denial.

    Args:
        request_id: Caller-supplied request id stamped on the result.

    Returns:
        An ``AUTH_DENIED`` gateway error (403, never retryable).
    """
    return RelayGatewayError(
        code=RelayGatewayErrorCode.AUTH_DENIED,
        message="authorization denied",
        status_code=403,
        request_id=request_id,
        retryable=False,
    )


def billing_error_to_gateway(
    error: RelayBillingError, request_id: str
) -> RelayGatewayError:
    """Map a billing admission error to a gateway error.

    Args:
        error: The ``RelayBillingError`` returned by the billing
            pipeline. Its message is redaction-safe and propagated.
        request_id: Caller-supplied request id stamped on the result.

    Returns:
        A ``RelayGatewayError`` classified from the billing error code:
        quota denials map to ``QUOTA_EXCEEDED`` (429, retryable); every
        other billing failure maps to ``BILLING_FAILED`` (500, never
        retryable).
    """
    if error.code == "quota_exhausted":
        return RelayGatewayError(
            code=RelayGatewayErrorCode.QUOTA_EXCEEDED,
            message=error.message,
            status_code=429,
            request_id=request_id,
            retryable=True,
        )
    return RelayGatewayError(
        code=RelayGatewayErrorCode.BILLING_FAILED,
        message=error.message,
        status_code=500,
        request_id=request_id,
        retryable=False,
    )


def with_request_id(error: RelayGatewayError, request_id: str) -> RelayGatewayError:
    """Return *error* with the given request id when it has none.

    Errors produced by the channel registry carry an empty request id;
    this attaches the caller's id without disturbing errors that already
    carry one (the adapter always stamps its own).

    Args:
        error: The gateway error to normalize.
        request_id: Request id to attach when *error* carries none.

    Returns:
        *error* unchanged when its request id is non-empty, otherwise a
        new ``RelayGatewayError`` copying code, message, status code,
        and retryability with the given request id.
    """
    if error.request_id:
        return error
    return RelayGatewayError(
        code=error.code,
        message=error.message,
        status_code=error.status_code,
        request_id=request_id,
        retryable=error.retryable,
    )
