"""Relay gateway request lifecycle (buffered and streaming).

``RelayGatewayService`` orchestrates one request through the
dependencies: authorization, channel selection, billing admission, request
conversion, the protected upstream call, response conversion, billing
settlement, and result metadata assembly.  Streaming requests run the
same preflight and then consume the upstream SSE stream lazily through
the stream session, settling billing exactly once when the stream ends.

The pipeline's specialized concerns live in focused modules:

- :mod:`lexigram.ai.relay.gateway.validation` — request boundary checks.
- :mod:`lexigram.ai.relay.gateway.operations.billing` — admission and
  settlement lifecycle.
- :mod:`lexigram.ai.relay.gateway.operations.upstream` — endpoint URLs,
  model resolution, upstream calls, and failover accounting.
- :mod:`lexigram.ai.relay.gateway.operations.telemetry` — structured
  request events.

Provider authentication headers are out of scope until Task 7.
``config.provider_options`` are intentionally not merged into
``RelayOptions`` yet because no mapping schema exists.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
import time
from typing import Literal, cast

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.errors import (
    auth_denied,
    conversion_error_to_gateway,
    unexpected_error,
    with_request_id,
)
from lexigram.ai.relay.gateway.operations import billing as billing_ops
from lexigram.ai.relay.gateway.operations import telemetry
from lexigram.ai.relay.gateway.operations import upstream as upstream_ops
from lexigram.ai.relay.gateway.operations.failover import RelayFailoverTracker
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.ai.relay.gateway.stream import UpstreamEventParser, relay_stream
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.ai.relay.gateway.validation import validate_gateway_request
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.governance import (
    RelayBillingProtocol,
    RelayUsageReservation,
)
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
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger

__all__ = ["RelayGatewayService", "validate_gateway_request"]

logger = get_logger(__name__)


class RelayGatewayService:
    """Relay request lifecycle (buffered and streaming).

    The service is stateless between requests and never touches request
    headers, payloads, or upstream details in error messages; errors are
    always safe ``RelayGatewayError`` values.

    Attributes:
        _converter: Engine implementing ``RelayConverterProtocol``.
        _codec: Wire DTO codec.
        _registry: Deterministic channel selector.
        _upstream: HTTP transport adapter.
        _config: Gateway configuration (channel table and model suffixes).
        _authorizer: Optional authorization check before dispatch.
        _billing: Optional billing lifecycle; when ``None`` admission and
            settlement are skipped.
        _media_resolver: Optional URL-media resolver threaded into the
            conversion context.
        _streams: Optional registry of active streams used to expose
            in-flight streams and cancel handles to operators; ``None``
            disables stream registration (but not streaming itself).
        _failover: Optional consecutive-failure tracker; when ``None``
            upstream failures never affect runtime selection state.
    """

    def __init__(
        self,
        converter: RelayConverterProtocol,
        codec: RelayPayloadCodec,
        registry: RelayChannelRegistry,
        upstream: HTTPUpstreamAdapter,
        config: RelayGatewayConfig,
        *,
        authorizer: AuthorizerProtocol | None = None,
        billing: RelayBillingProtocol | None = None,
        media_resolver: MediaResolverProtocol | None = None,
        streams: RelayStreamRegistry | None = None,
        failover: RelayFailoverTracker | None = None,
    ) -> None:
        """Bind the service to its dependencies.

        Args:
            converter: Conversion engine for request/response payloads.
            codec: Wire DTO decoder/encoder.
            registry: Channel selection registry.
            upstream: Upstream transport adapter.
            config: Static gateway configuration.
            authorizer: Optional authorizer; when ``None`` authorization
                is skipped.
            billing: Optional billing lifecycle; when ``None`` the
                gateway runs without admission control or settlement.
            media_resolver: Optional URL-media resolver placed on the
                conversion context; ``None`` disables media resolution.
            streams: Optional stream registry for operator visibility
                and forced cancellation; ``None`` keeps streaming
                functional without registry bookkeeping.
            failover: Optional consecutive-failure tracker; when ``None``
                upstream failures never affect runtime selection state.
        """
        self._converter = converter
        self._codec = codec
        self._registry = registry
        self._upstream = upstream
        self._config = config
        self._authorizer = authorizer
        self._billing = billing
        self._media_resolver = media_resolver
        self._streams = streams
        self._failover = failover

    async def handle(
        self, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Run the buffered or streaming relay lifecycle for one request.

        Dependencies run in fixed order: authorize, select channel,
        reserve billing capacity, convert request, then either call
        upstream, decode, convert response back, and settle (buffered),
        or create the stream session and hand back a lazy stream that
        consumes upstream events and settles when exhausted (streaming).
        Any preflight failure short-circuits the pipeline.

        Args:
            request: The gateway request.

        Returns:
            ``Ok(RelayGatewayResult)`` on success, or
            ``Err(RelayGatewayError)`` on the first failure.  Unexpected
            exceptions from dependencies never escape: they are logged
            and mapped to a generic ``CONVERSION_FAILED`` error.
        """
        started = time.monotonic()
        validation_error = validate_gateway_request(request)
        if validation_error is not None:
            logger.warning(
                "relay_gateway_invalid_request",
                request_id=request.request_id,
                error=validation_error.message,
            )
            telemetry.log_request_completed(request, "", validation_error, started)
            return Err(validation_error)
        logger.info(
            "relay_gateway_request_accepted",
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            source=request.source,
            model=request.model,
            stream=request.stream,
        )
        try:
            if request.stream:
                result, channel_name = await self._handle_streaming(request)
            else:
                result, channel_name = await self._dispatch(request)
        except Exception as exc:
            logger.warning(
                "relay_gateway_unexpected_error",
                request_id=request.request_id,
                error=str(exc),
            )
            error = unexpected_error(request.request_id)
            telemetry.log_request_completed(request, "", error, started)
            return Err(error)
        if result.is_err():
            telemetry.log_request_completed(
                request, channel_name, result.unwrap_err(), started
            )
            return result
        outcome = result.unwrap()
        telemetry.log_request_completed(
            request,
            channel_name,
            outcome,
            started,
            target=outcome.metadata.target if outcome.metadata else "",
            loss_codes=outcome.metadata.loss_codes if outcome.metadata else (),
        )
        return result

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
