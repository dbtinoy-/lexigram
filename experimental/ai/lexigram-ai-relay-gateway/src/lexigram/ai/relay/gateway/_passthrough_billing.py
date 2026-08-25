"""Billing admission and settlement for the passthrough relay path.

Wraps the shared ``RelayBillingProtocol`` lifecycle for endpoint kinds
that bypass the chat conversion engine: bodies are carried transparently
for prompt estimation, output budget is unknown (reserved as zero), and
settlement never fails the response.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from lexigram.ai.relay.gateway.errors import billing_error_to_gateway
from lexigram.ai.relay.gateway.passthrough_body import _as_relay_body
from lexigram.contracts.ai.governance import (
    RelayBillingProtocol,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    JsonValue,
    RelayChannel,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayRequestPayload,
    RelayUsage,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["PassthroughBilling", "PassthroughPayloadCarrier"]


@dataclass(frozen=True, slots=True)
class PassthroughPayloadCarrier:
    """Billing-admission carrier for a passthrough request body.

    Passthrough bodies do not belong to any chat wire DTO, so the
    shared billing pipeline receives a transparent carrier: prompt
    estimation counts the serialized body (same estimate function as the
    chat path) and the requested output budget is unknown, so zero is
    reserved. The carrier quacks like a ``RelayRequestPayload`` at the
    only call site the billing pipeline uses (``to_dict``).
    """

    body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return the passthrough body.

        Returns:
            A shallow copy of the forwarded request body.
        """
        return dict(self.body)


class PassthroughBilling:
    """Billing collaborator for the passthrough pipeline.

    Args:
        billing: The shared billing lifecycle to admit and settle through.
    """

    def __init__(self, billing: RelayBillingProtocol) -> None:
        """Bind the collaborator to the billing lifecycle.

        Args:
            billing: The billing lifecycle to reserve and settle through.
        """
        self._billing = billing

    async def reserve(
        self,
        request: RelayGatewayRequest,
        channel: RelayChannel,
    ) -> Result[RelayUsageReservation, RelayGatewayError]:
        """Reserve billing capacity before the upstream call.

        The passthrough body is wrapped in a transparent carrier so the
        shared billing pipeline can estimate prompt tokens from the
        serialized body; the output budget is unknown and reserved as
        zero.  Billing denials short-circuit the pipeline and are
        classified through :func:`billing_error_to_gateway`.

        Args:
            request: The passthrough request being dispatched.
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
        body = _as_relay_body(request.payload)
        body_data = body.data
        if isinstance(body_data, Mapping):
            carrier_body: dict[str, JsonValue] = dict(body_data)
        else:
            carrier_body = {}
        carrier = PassthroughPayloadCarrier(carrier_body)
        admitted = await self._billing.pre_consume(
            request.request_id,
            scope,
            cast("RelayRequestPayload", carrier),
        )
        if admitted.is_err():
            error = admitted.unwrap_err()
            logger.warning(
                "relay_passthrough_billing_denied",
                request_id=request.request_id,
                channel=channel.name,
                code=error.code,
                error=error.message,
            )
            return Err(billing_error_to_gateway(error, request.request_id))
        return Ok(admitted.unwrap())

    async def settle_completed(
        self,
        reservation: RelayUsageReservation,
        usage: RelayUsage | None,
    ) -> None:
        """Settle a completed attempt, recording extracted usage if any.

        Args:
            reservation: The reservation granted by ``pre_consume``.
            usage: The usage extracted from the upstream response, or
                ``None`` when the response omits it.
        """
        await self._settle(reservation, usage, status="completed")

    async def settle_failed(self, reservation: RelayUsageReservation) -> None:
        """Settle a failed attempt without usage through the billing pipeline.

        Args:
            reservation: The reservation granted by ``pre_consume``.
        """
        await self._settle(reservation, None, status="failed")

    async def _settle(
        self,
        reservation: RelayUsageReservation,
        usage: RelayUsage | None,
        *,
        status: Literal["completed", "failed", "cancelled", "truncated"],
    ) -> None:
        """Settle the reservation exactly once without failing the response.

        Settlement failures are logged and never propagate: the response
        path has already completed by the time accounting runs.

        Args:
            reservation: The reservation granted by ``pre_consume``.
            usage: The usage extracted from the upstream response, or
                ``None`` when the response omits it.
            status: Terminal lifecycle status of the attempt.
        """
        result = RelayConvertResult[Any](
            value=None,
            source=RelayFormat.OPENAI_CHAT,
            target=RelayFormat.OPENAI_CHAT,
            converter_id="passthrough",
            quality=ConversionQuality.GOOD,
            usage=usage,
        )
        settled = await self._billing.settle(reservation, result, status=status)
        if settled.is_err():
            error = settled.unwrap_err()
            logger.warning(
                "relay_passthrough_settle_failed",
                request_id=reservation.request_id,
                status=status,
                code=error.code,
                error=error.message,
            )


def usage_from_response(payload: Mapping[str, Any]) -> RelayUsage | None:
    """Extract normalized usage from an OpenAI-shaped response body.

    Args:
        payload: The upstream response body.

    Returns:
        ``RelayUsage`` when the body carries an integer
        ``prompt_tokens`` count, otherwise ``None`` (the billing
        pipeline records usage as missing).
    """
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    prompt = usage.get("prompt_tokens")
    if not isinstance(prompt, int):
        return None
    completion = usage.get("completion_tokens", 0)
    if not isinstance(completion, int):
        completion = 0
    return RelayUsage(prompt_tokens=prompt, completion_tokens=completion)
