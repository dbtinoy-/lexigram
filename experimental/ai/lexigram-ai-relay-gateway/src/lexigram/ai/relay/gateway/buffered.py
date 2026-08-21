"""Buffered dispatch pipeline for :class:`RelayGatewayService`.

Runs the ordered dependency pipeline for one non-streaming request:
authorization, channel selection with retry/failover, billing admission,
request conversion, the protected upstream call, response decoding and
conversion, billing settlement, and result metadata assembly.
"""

from __future__ import annotations

from typing import cast

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.errors import (
    auth_denied,
    conversion_error_to_gateway,
    with_request_id,
)
from lexigram.ai.relay.gateway.operations import billing as billing_ops
from lexigram.ai.relay.gateway.operations import telemetry
from lexigram.ai.relay.gateway.operations import upstream as upstream_ops
from lexigram.ai.relay.gateway.operations.failover import RelayFailoverTracker
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.governance import RelayBillingProtocol, RelayUsageReservation
from lexigram.contracts.ai.relay import (
    MediaResolverProtocol,
    RelayChannel,
    RelayConversionContext,
    RelayConverterProtocol,
    RelayGatewayError,
    RelayGatewayMetadata,
    RelayGatewayRequest,
    RelayGatewayResult,
    RelayOptions,
    RelayRequestPayload,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger

logger = get_logger(__name__)


class BufferedDispatchMixin:
    """Buffered request pipeline shared into ``RelayGatewayService``.

    Requires the host service to provide the gateway dependencies as
    private attributes (``_converter``, ``_codec``, ``_registry``,
    ``_upstream``, ``_config``, ``_authorizer``, ``_billing``,
    ``_media_resolver``, ``_failover``).
    """

    _converter: RelayConverterProtocol
    _codec: RelayPayloadCodec
    _registry: RelayChannelRegistry
    _upstream: HTTPUpstreamAdapter
    _config: RelayGatewayConfig
    _authorizer: AuthorizerProtocol | None
    _billing: RelayBillingProtocol | None
    _media_resolver: MediaResolverProtocol | None
    _failover: RelayFailoverTracker | None

    async def _dispatch(
        self, request: RelayGatewayRequest
    ) -> tuple[Result[RelayGatewayResult, RelayGatewayError], str]:
        """Run the ordered dependency pipeline for one request.

        Returns:
            ``tuple`` of the pipeline result and the selected channel
            name.  The channel name is ``""`` when selection failed
            before a channel was chosen.
        """
        if self._authorizer is not None:
            allowed = await self._authorizer.authorize(
                user=request.tenant_id,
                action="relay.invoke",
                resource=request.model,
            )
            if not allowed:
                return Err(auth_denied(request.request_id)), ""
        max_attempts = self._config.max_upstream_retries + 1
        tried: set[str] = set()
        last_upstream_error: RelayGatewayError | None = None
        last_channel_name = ""
        last_channel: RelayChannel | None = None
        held_reservation: RelayUsageReservation | None = None
        for attempt in range(1, max_attempts + 1):
            selected = self._registry.select(
                source=request.source,
                model=request.model,
                stream=request.stream,
                preferred=request.channel.name if request.channel else None,
                exclude=frozenset(tried),
            )
            if selected.is_err():
                if last_upstream_error is not None:
                    billing = self._billing
                    if (
                        held_reservation is not None
                        and billing is not None
                        and last_channel is not None
                    ):
                        await billing_ops.settle(
                            billing,
                            held_reservation,
                            billing_ops.empty_settle_result(request, last_channel),
                            status="failed",
                        )
                    return (
                        Err(with_request_id(last_upstream_error, request.request_id)),
                        last_channel_name,
                    )
                return (
                    Err(with_request_id(selected.unwrap_err(), request.request_id)),
                    "",
                )
            channel = selected.unwrap()
            last_channel = channel
            last_channel_name = channel.name
            logger.info(
                "relay_gateway_channel_selected",
                request_id=request.request_id,
                channel=channel.name,
                target_format=channel.target_format,
                model=request.model,
            )
            billing = self._billing
            reservation: RelayUsageReservation | None = None
            if billing is not None:
                admitted = await billing_ops.pre_consume(
                    self._codec, request, billing, channel
                )
                if admitted.is_err():
                    return Err(admitted.unwrap_err()), channel.name
                reservation = admitted.unwrap()
                if held_reservation is not None:
                    await billing.release(held_reservation)
                    held_reservation = None
            outbound_model = upstream_ops.outbound_model(
                self._config, channel, request.model
            )
            context = RelayConversionContext(
                request_id=request.request_id,
                channel_name=channel.name,
                upstream_model=outbound_model,
                options=RelayOptions(),
                media_resolver=self._media_resolver,
            )
            conv = self._converter.convert_request(
                payload=cast("RelayRequestPayload", request.payload),
                source=request.source,
                target=channel.target_format,
                context=context,
            )
            if conv.is_err():
                if reservation is not None and billing is not None:
                    await billing.release(reservation)
                return (
                    Err(
                        conversion_error_to_gateway(
                            conv.unwrap_err(), request.request_id
                        )
                    ),
                    channel.name,
                )
            converted_request = conv.unwrap()
            telemetry.log_conversion_loss(
                request.request_id,
                converted_request.converter_id,
                converted_request.losses,
            )
            upstream_response = await upstream_ops.call_upstream(
                self._upstream,
                channel,
                outbound_model,
                converted_request.value.to_dict(),
                request,
            )
            if upstream_response.is_err():
                upstream_error = upstream_response.unwrap_err()
                if upstream_ops.should_track_upstream_failure(upstream_error.code):
                    upstream_ops.note_failure(self._failover, channel.name)
                if upstream_error.retryable and attempt < max_attempts:
                    tried.add(channel.name)
                    last_upstream_error = upstream_error
                    held_reservation = reservation
                    logger.info(
                        "relay_gateway_upstream_retry",
                        request_id=request.request_id,
                        channel=channel.name,
                        error_code=upstream_error.code,
                        attempt=attempt,
                    )
                    continue
                if reservation is not None and billing is not None:
                    await billing_ops.settle(
                        billing,
                        reservation,
                        billing_ops.empty_settle_result(request, channel),
                        status="failed",
                    )
                return (
                    Err(with_request_id(upstream_error, request.request_id)),
                    channel.name,
                )
            resp = upstream_response.unwrap()
            if resp.payload is None:
                if reservation is not None and billing is not None:
                    await billing_ops.settle(
                        billing,
                        reservation,
                        billing_ops.empty_settle_result(request, channel),
                        status="failed",
                    )
                return (
                    Err(
                        RelayGatewayError(
                            code=RelayGatewayErrorCode.UPSTREAM_MALFORMED,
                            message="malformed upstream response",
                            status_code=502,
                            request_id=request.request_id,
                            retryable=False,
                        )
                    ),
                    channel.name,
                )
            decoded = self._codec.decode_response_payload(
                target=channel.target_format,
                data=dict(resp.payload),
                request_id=request.request_id,
            )
            if decoded.is_err():
                if reservation is not None and billing is not None:
                    await billing_ops.settle(
                        billing,
                        reservation,
                        billing_ops.empty_settle_result(request, channel),
                        status="failed",
                    )
                return Err(decoded.unwrap_err()), channel.name
            back = self._converter.convert_response(
                payload=decoded.unwrap(),
                source=channel.target_format,
                target=request.source,
                context=context,
            )
            if back.is_err():
                if reservation is not None and billing is not None:
                    await billing_ops.settle(
                        billing,
                        reservation,
                        billing_ops.empty_settle_result(request, channel),
                        status="failed",
                    )
                return (
                    Err(
                        conversion_error_to_gateway(
                            back.unwrap_err(), request.request_id
                        )
                    ),
                    channel.name,
                )
            converted = back.unwrap()
            telemetry.log_conversion_loss(
                request.request_id, converted.converter_id, converted.losses
            )
            if reservation is not None and billing is not None:
                await billing_ops.settle(
                    billing, reservation, converted, status="completed"
                )
            upstream_ops.note_success(self._failover, channel.name)
            metadata = RelayGatewayMetadata(
                converter_id=converted.converter_id,
                source=request.source,
                target=channel.target_format,
                quality=converted.quality,
                loss_codes=tuple(loss.reason for loss in converted.losses),
                warnings=converted.warnings,
            )
            return (
                Ok(
                    RelayGatewayResult(
                        status_code=resp.status_code,
                        headers={**resp.headers, "x-request-id": request.request_id},
                        payload=converted.value.to_dict(),
                        stream=None,
                        metadata=metadata,
                    )
                ),
                channel.name,
            )
        error = last_upstream_error or RelayGatewayError(
            code=RelayGatewayErrorCode.CHANNEL_DISABLED,
            message="no channels available",
            status_code=404,
            request_id=request.request_id,
        )
        return Err(with_request_id(error, request.request_id)), last_channel_name


__all__ = ["BufferedDispatchMixin"]
