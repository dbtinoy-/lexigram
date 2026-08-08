"""Request telemetry events for the relay gateway service.

Terminal and intermediate request events are emitted as structured
structlog events with the request id threaded through.  No event ever
includes request headers, payloads, or upstream details.
"""

from __future__ import annotations

import time

from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    RelayGatewayRequest,
    RelayGatewayResult,
    RelayLoss,
)
from lexigram.logging import get_logger

__all__ = ["log_conversion_loss", "log_request_completed"]

logger = get_logger(__name__)


def log_conversion_loss(
    request_id: str,
    converter_id: str,
    losses: tuple[RelayLoss, ...] | list[RelayLoss],
) -> None:
    """Emit the conversion-loss event when a conversion recorded losses.

    Args:
        request_id: The gateway request identifier.
        converter_id: The converter that produced the losses.
        losses: Recorded conversion losses.
    """
    if losses:
        logger.info(
            "relay_gateway_conversion_loss",
            request_id=request_id,
            converter_id=converter_id,
            loss_codes=tuple(loss.reason for loss in losses),
        )


def log_request_completed(
    request: RelayGatewayRequest,
    channel_name: str,
    outcome: RelayGatewayResult | RelayGatewayError,
    started: float,
    *,
    target: str = "",
    loss_codes: tuple[str, ...] = (),
) -> None:
    """Emit the terminal request-completed event for any outcome.

    Args:
        request: The original gateway request.
        channel_name: Selected channel name (or ``""`` when unknown).
        outcome: The success result or the error that ended the flow.
        started: Monotonic start time used to compute the duration.
        target: Target format name (success path only).
        loss_codes: Conversion loss codes (success path only).
    """
    logger.info(
        "relay_gateway_request_completed",
        request_id=request.request_id,
        tenant_id=request.tenant_id,
        channel=channel_name,
        source=request.source,
        target=target,
        status_code=outcome.status_code,
        code=outcome.code if isinstance(outcome, RelayGatewayError) else "OK",
        duration_ms=round((time.monotonic() - started) * 1000, 2),
        loss_codes=loss_codes,
    )
