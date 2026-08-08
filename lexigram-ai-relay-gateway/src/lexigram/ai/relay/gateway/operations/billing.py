"""Billing lifecycle helpers for the relay gateway service.

Admission control reserves capacity before conversion and upstream I/O;
settlement runs exactly once per attempt after the terminal outcome is
known.  Settlement failures are logged and never fail the response.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.errors import billing_error_to_gateway
from lexigram.contracts.ai.governance import (
    RelayBillingProtocol,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayChannel,
    RelayConvertResult,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayStreamSessionProtocol,
    RelayUsage,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger
from lexigram.serialization import dumps

__all__ = [
    "StreamStatus",
    "empty_settle_result",
    "pre_consume",
    "settle",
    "stream_settle_result",
    "usage_from_snapshot",
]

logger = get_logger(__name__)

StreamStatus = Literal["completed", "failed", "cancelled", "truncated"]


def usage_from_snapshot(snapshot: object) -> RelayUsage | None:
    """Extract ``RelayUsage`` from a session snapshot when present.

    Snapshots are opaque; only a ``Mapping`` carrying a ``usage``
    sub-mapping is inspected, accepting either the OpenAI-style
    ``prompt_tokens``/``completion_tokens`` keys or the Claude-style
    ``input_tokens``/``output_tokens`` keys.

    Args:
        snapshot: The session snapshot returned by
            ``RelayStreamSessionProtocol.snapshot``.

    Returns:
        A normalized ``RelayUsage`` when the snapshot exposes one,
        else ``None`` (settlement then records no usage).
    """
    if not isinstance(snapshot, Mapping):
        return None
    usage = snapshot.get("usage")
    if not isinstance(usage, Mapping):
        return None
    prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion = usage.get("completion_tokens", usage.get("output_tokens"))
    if not isinstance(prompt, int) or not isinstance(completion, int):
        return None
    return RelayUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
    )


def empty_settle_result(
    request: RelayGatewayRequest, channel: RelayChannel
) -> RelayConvertResult[Any]:
    """Build the usage-free result settled for failed attempts.

    Args:
        request: The gateway request being dispatched.
        channel: The selected channel.

    Returns:
        A ``RelayConvertResult`` carrying no usage so the billing
        pipeline records an attempted-but-unbilled attempt.
    """
    return RelayConvertResult(
        value=None,
        source=request.source,
        target=channel.target_format,
        converter_id="",
        quality=ConversionQuality.GOOD,
    )


def stream_settle_result(
    request: RelayGatewayRequest,
    channel: RelayChannel,
    *,
    converter_id: str,
    session: RelayStreamSessionProtocol,
) -> RelayConvertResult[Any]:
    """Build the settled result from the stream session snapshot.

    Args:
        request: The gateway request being settled.
        channel: The selected channel.
        converter_id: Converter that produced the stream session.
        session: The stream session whose snapshot carries the settled
            usage.

    Returns:
        A ``RelayConvertResult`` carrying normalized usage extracted
        from the session snapshot (or no usage when the snapshot
        exposes none).
    """
    usage = usage_from_snapshot(session.snapshot())
    return RelayConvertResult(
        value=None,
        source=request.source,
        target=channel.target_format,
        converter_id=converter_id,
        quality=ConversionQuality.GOOD,
        usage=usage,
    )


async def pre_consume(
    codec: RelayPayloadCodec,
    request: RelayGatewayRequest,
    billing: RelayBillingProtocol,
    channel: RelayChannel,
) -> Result[RelayUsageReservation, RelayGatewayError]:
    """Reserve billing capacity before conversion and upstream I/O.

    The inbound payload is re-decoded into a typed request DTO so the
    billing pipeline can estimate prompt and output budgets; a payload
    that rejects decoding fails the request here, before any upstream
    I/O.  Billing denials short-circuit the pipeline and are classified
    through :func:`billing_error_to_gateway`.

    Args:
        codec: Wire DTO decoder used to re-decode the inbound payload.
        request: The gateway request being dispatched.
        billing: The billing lifecycle to reserve through.
        channel: The selected channel.

    Returns:
        ``Ok(reservation)`` when admission is proven, or
        ``Err(RelayGatewayError)`` carrying the classified failure.
    """
    scope = RelayUsageScope(
        tenant_id=request.tenant_id,
        model=request.model,
        channel=channel.name,
    )
    dto = codec.decode_request(
        source=request.source,
        raw=dumps(dict(request.payload)),
        request_id=request.request_id,
    )
    if dto.is_err():
        return Err(dto.unwrap_err())
    admitted = await billing.pre_consume(request.request_id, scope, dto.unwrap())
    if admitted.is_err():
        error = admitted.unwrap_err()
        logger.warning(
            "relay_gateway_billing_denied",
            request_id=request.request_id,
            channel=channel.name,
            code=error.code,
            error=error.message,
        )
        return Err(billing_error_to_gateway(error, request.request_id))
    return Ok(admitted.unwrap())


async def settle(
    billing: RelayBillingProtocol,
    reservation: RelayUsageReservation,
    result: RelayConvertResult[Any],
    *,
    status: StreamStatus,
) -> None:
    """Settle the reservation exactly once without failing the response.

    Settlement failures are logged and never propagate: the response
    path has already completed by the time accounting runs.

    Args:
        billing: The billing lifecycle to settle through.
        reservation: The reservation granted by ``pre_consume``.
        result: The conversion result carrying settled usage, or an
            empty result when the attempt produced no billable usage.
        status: Terminal lifecycle status of the attempt.
    """
    settled = await billing.settle(reservation, result, status=status)
    if settled.is_err():
        error = settled.unwrap_err()
        logger.warning(
            "relay_gateway_settle_failed",
            request_id=reservation.request_id,
            status=status,
            code=error.code,
            error=error.message,
        )
