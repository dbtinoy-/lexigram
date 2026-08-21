"""Streaming pipeline for :class:`RelayGatewayService`.

Preflight (authorization, channel selection, billing admission, request
conversion, stream-session creation) completes before the first frame is
delivered; upstream I/O happens lazily as the returned stream is
consumed by the caller.  Billing settles exactly once when the stream
ends — completed, cancelled, truncated, or failed.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Literal, cast

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
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.ai.relay.gateway.stream import UpstreamEventParser, relay_stream
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.governance import RelayBillingProtocol, RelayUsageReservation
from lexigram.contracts.ai.relay import (
    MediaResolverProtocol,
    RelayChannel,
    RelayConversionContext,
    RelayConverterProtocol,
    RelayConvertResult,
    RelayGatewayError,
    RelayGatewayMetadata,
    RelayGatewayRequest,
    RelayGatewayResult,
    RelayOptions,
    RelayRequestPayload,
    RelayStreamSessionProtocol,
    RelayUpstreamProtocol,
    RelayWireEvent,
    UpstreamRequest,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger

logger = get_logger(__name__)


class StreamingMixin:
    """Streaming request pipeline shared into ``RelayGatewayService``.

    Requires the host service to provide the gateway dependencies as
    private attributes (``_converter``, ``_codec``, ``_registry``,
    ``_upstream``, ``_config``, ``_authorizer``, ``_billing``,
    ``_media_resolver``, ``_streams``, ``_failover``).
    """

    _converter: RelayConverterProtocol
    _codec: RelayPayloadCodec
    _registry: RelayChannelRegistry
    _upstream: HTTPUpstreamAdapter
    _config: RelayGatewayConfig
    _authorizer: AuthorizerProtocol | None
    _billing: RelayBillingProtocol | None
    _media_resolver: MediaResolverProtocol | None
    _streams: RelayStreamRegistry | None
    _failover: RelayFailoverTracker | None

    async def _handle_streaming(
        self, request: RelayGatewayRequest
    ) -> tuple[Result[RelayGatewayResult, RelayGatewayError], str]:
        """Run the streaming preflight and return a lazy stream result.

        Authorization, channel selection, billing admission, request
        conversion, and stream-session creation all complete before the
        first frame is delivered; upstream I/O happens lazily as the
        returned stream is consumed by the caller.

        Returns:
            ``tuple`` of the pipeline result (whose ``stream`` holds the
            lazy ``AsyncIterator`` on success) and the selected channel
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
        selected = self._registry.select(
            source=request.source,
            model=request.model,
            stream=True,
            preferred=request.channel.name if request.channel else None,
        )
        if selected.is_err():
            return (
                Err(with_request_id(selected.unwrap_err(), request.request_id)),
                "",
            )
        channel = selected.unwrap()
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
                Err(conversion_error_to_gateway(conv.unwrap_err(), request.request_id)),
                channel.name,
            )
        converted_request = conv.unwrap()
        session = self._converter.new_stream_session(
            source=request.source,
            target=channel.target_format,
            context=context,
        )
        if session.is_err():
            if reservation is not None and billing is not None:
                await billing.release(reservation)
            return (
                Err(
                    conversion_error_to_gateway(
                        session.unwrap_err(), request.request_id
                    )
                ),
                channel.name,
            )
        stream_session = session.unwrap()
        telemetry.log_conversion_loss(
            request.request_id,
            converted_request.converter_id,
            converted_request.losses,
        )
        metadata = RelayGatewayMetadata(
            converter_id=converted_request.converter_id,
            source=request.source,
            target=channel.target_format,
            quality=converted_request.quality,
            loss_codes=tuple(loss.reason for loss in converted_request.losses),
            warnings=converted_request.warnings,
        )
        stream = self._stream_events(
            request,
            channel,
            outbound_model,
            converted_request,
            reservation=reservation,
            session=stream_session,
            context=context,
        )
        return (
            Ok(
                RelayGatewayResult(
                    status_code=200,
                    headers={"x-request-id": request.request_id},
                    payload=None,
                    stream=stream,
                    metadata=metadata,
                )
            ),
            channel.name,
        )

    async def _stream_events(
        self,
        request: RelayGatewayRequest,
        channel: RelayChannel,
        outbound_model: str,
        converted_request: RelayConvertResult[RelayRequestPayload],
        *,
        reservation: RelayUsageReservation | None,
        session: RelayStreamSessionProtocol,
        context: RelayConversionContext,
    ) -> AsyncIterator[RelayWireEvent]:
        """Consume the upstream stream and settle the reservation once.

        Each consumer pull forwards exactly one upstream chunk through
        the session; cancellation, truncation, and malformed framing
        follow the ``relay_stream`` lifecycle.  The ``finally`` block
        runs when the consumer ends the stream (completion, disconnect,
        or error) and settles billing exactly once from the session
        snapshot.

        Yields:
            Normalized ``RelayWireEvent`` values framed by the stream
            session.
        """
        streams = self._streams
        stream_id: str | None = None
        cancel_handle: asyncio.Event | None = None
        if streams is not None:
            stream_id, cancel_handle = streams.register(
                channel=channel.name,
                model=outbound_model,
                request_id=request.request_id,
            )
        parser = UpstreamEventParser(
            session=session,
            source=channel.target_format,
            request_id=request.request_id,
        )
        url = upstream_ops.upstream_url(channel, outbound_model)
        payload = (
            converted_request.value.to_dict()
            if converted_request.value is not None
            else {}
        )
        logger.info(
            "relay_gateway_stream_started",
            request_id=request.request_id,
            channel=channel.name,
            method="POST",
            url=url,
        )
        upstream_request = UpstreamRequest(
            request_id=request.request_id,
            method="POST",
            url=url,
            headers={"content-type": "application/json"},
            payload=dict(payload),
            timeout_seconds=channel.timeout_seconds,
            channel_name=channel.name,
        )
        truncated = False
        stream_iter: AsyncGenerator[RelayWireEvent, None] | None = None
        try:
            stream_iter = cast(
                "AsyncGenerator[RelayWireEvent, None]",
                relay_stream(
                    cast(
                        "RelayUpstreamProtocol",
                        self._upstream,
                    ),
                    upstream_request,
                    parser,
                    cancel_handle=cancel_handle,
                ),
            )
            try:
                async for wire in stream_iter:
                    yield wire
            except (RelayGatewayError, RelayError) as error:
                logger.warning(
                    "relay_gateway_stream_malformed",
                    request_id=request.request_id,
                    channel=channel.name,
                    error=str(error),
                )
                truncated = True
                raise
        finally:
            if stream_iter is not None:
                await stream_iter.aclose()
            if truncated:
                status: Literal["completed", "failed", "cancelled", "truncated"] = (
                    "truncated"
                )
            elif parser.cancelled:
                status = "cancelled"
            elif parser.truncated:
                status = "truncated"
            else:
                status = "completed"
            if status == "completed":
                upstream_ops.note_success(self._failover, channel.name)
            elif status in ("failed", "truncated"):
                upstream_ops.note_failure(self._failover, channel.name)
            if streams is not None and stream_id is not None:
                streams.unregister(stream_id)
            billing = self._billing
            if billing is not None and reservation is not None:
                settled = billing_ops.stream_settle_result(
                    request,
                    channel,
                    converter_id=converted_request.converter_id,
                    session=session,
                )
                await billing_ops.settle(billing, reservation, settled, status=status)


__all__ = ["StreamingMixin"]
