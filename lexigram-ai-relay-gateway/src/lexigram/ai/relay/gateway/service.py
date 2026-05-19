"""Relay gateway request lifecycle (buffered and streaming).

``RelayGatewayService`` orchestrates one request through the
dependencies: authorization, channel selection, billing admission, request
conversion, the protected upstream call, response conversion, billing
settlement, and result metadata assembly.  Streaming requests run the
same preflight and then consume the upstream SSE stream lazily through
the stream session, settling billing exactly once when the stream ends.

Provider authentication headers are out of scope until Task 7.
``config.provider_options`` are intentionally not merged into
``RelayOptions`` yet because no mapping schema exists.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Mapping
import time
from typing import Any, Literal, cast

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.errors import (
    auth_denied,
    billing_error_to_gateway,
    conversion_error_to_gateway,
    with_request_id,
)
from lexigram.ai.relay.gateway.operations.failover import RelayFailoverTracker
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.ai.relay.gateway.stream import UpstreamEventParser, relay_stream
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.governance import (
    RelayBillingProtocol,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    MediaResolverProtocol,
    RelayChannel,
    RelayConversionContext,
    RelayConverterProtocol,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayMetadata,
    RelayGatewayRequest,
    RelayGatewayResult,
    RelayLoss,
    RelayOptions,
    RelayRequestPayload,
    RelayStreamSessionProtocol,
    RelayUpstreamProtocol,
    RelayUsage,
    RelayWireEvent,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger
from lexigram.serialization import dumps

__all__ = ["RelayGatewayService"]

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
            error = self._unexpected_error(request.request_id)
            self._log_request_completed(request, "", error, started)
            return Err(error)
        if result.is_err():
            self._log_request_completed(
                request, channel_name, result.unwrap_err(), started
            )
            return result
        outcome = result.unwrap()
        self._log_request_completed(
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
                        await self._settle(
                            billing,
                            held_reservation,
                            self._empty_settle_result(request, last_channel),
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
                admitted = await self._pre_consume(request, billing, channel)
                if admitted.is_err():
                    return Err(admitted.unwrap_err()), channel.name
                reservation = admitted.unwrap()
                if held_reservation is not None:
                    await billing.release(held_reservation)
                    held_reservation = None
            outbound_model = self._outbound_model(channel, request.model)
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
            self._log_conversion_loss(
                request.request_id,
                converted_request.converter_id,
                converted_request.losses,
            )
            upstream_response = await self._call_upstream(
                channel, outbound_model, converted_request.value.to_dict(), request
            )
            if upstream_response.is_err():
                upstream_error = upstream_response.unwrap_err()
                if self._should_track_upstream_failure(upstream_error.code):
                    self._note_failure(channel.name)
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
                    await self._settle(
                        billing,
                        reservation,
                        self._empty_settle_result(request, channel),
                        status="failed",
                    )
                return (
                    Err(with_request_id(upstream_error, request.request_id)),
                    channel.name,
                )
            resp = upstream_response.unwrap()
            if resp.payload is None:
                if reservation is not None and billing is not None:
                    await self._settle(
                        billing,
                        reservation,
                        self._empty_settle_result(request, channel),
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
                    await self._settle(
                        billing,
                        reservation,
                        self._empty_settle_result(request, channel),
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
                    await self._settle(
                        billing,
                        reservation,
                        self._empty_settle_result(request, channel),
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
            self._log_conversion_loss(
                request.request_id, converted.converter_id, converted.losses
            )
            if reservation is not None and billing is not None:
                await self._settle(billing, reservation, converted, status="completed")
            self._note_success(channel.name)
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
            admitted = await self._pre_consume(request, billing, channel)
            if admitted.is_err():
                return Err(admitted.unwrap_err()), channel.name
            reservation = admitted.unwrap()
        outbound_model = self._outbound_model(channel, request.model)
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
        self._log_conversion_loss(
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
            reservation,
            stream_session,
            context,
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
        url = self._upstream_url(channel, outbound_model)
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
                self._note_success(channel.name)
            elif status in ("failed", "truncated"):
                self._note_failure(channel.name)
            if streams is not None and stream_id is not None:
                streams.unregister(stream_id)
            billing = self._billing
            if billing is not None and reservation is not None:
                settled = self._stream_settle_result(
                    request,
                    channel,
                    converter_id=converted_request.converter_id,
                    session=session,
                )
                await self._settle(billing, reservation, settled, status=status)

    def _stream_settle_result(
        self,
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
            session: The stream session whose snapshot carries the
                settled usage.

        Returns:
            A ``RelayConvertResult`` carrying normalized usage extracted
            from the session snapshot (or no usage when the snapshot
            exposes none).
        """
        usage = self._usage_from_snapshot(session.snapshot())
        return RelayConvertResult(
            value=None,
            source=request.source,
            target=channel.target_format,
            converter_id=converter_id,
            quality=ConversionQuality.GOOD,
            usage=usage,
        )

    @staticmethod
    def _usage_from_snapshot(snapshot: object) -> RelayUsage | None:
        """Extract ``RelayUsage`` from a session snapshot when present.

        Snapshots are opaque; only a ``Mapping`` carrying a ``usage``
        sub-mapping is inspected, accepting either the OpenAI-style
        ``prompt_tokens``/``completion_tokens`` keys or the
        Claude-style ``input_tokens``/``output_tokens`` keys.

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

    async def _pre_consume(
        self,
        request: RelayGatewayRequest,
        billing: RelayBillingProtocol,
        channel: RelayChannel,
    ) -> Result[RelayUsageReservation, RelayGatewayError]:
        """Reserve billing capacity before conversion and upstream I/O.

        The inbound payload is re-decoded into a typed request DTO so the
        billing pipeline can estimate prompt and output budgets; a
        payload that rejects decoding fails the request here, before any
        upstream I/O.  Billing denials short-circuit the pipeline and are
        classified through :func:`billing_error_to_gateway`.

        Args:
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
        dto = self._codec.decode_request(
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

    async def _settle(
        self,
        billing: RelayBillingProtocol,
        reservation: RelayUsageReservation,
        result: RelayConvertResult[Any],
        *,
        status: Literal["completed", "failed", "cancelled", "truncated"],
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

    @staticmethod
    def _empty_settle_result(
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

    def _log_conversion_loss(
        self,
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

    def _log_request_completed(
        self,
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

    async def _call_upstream(
        self,
        channel: RelayChannel,
        outbound_model: str,
        payload: dict[str, Any],
        request: RelayGatewayRequest,
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Send the converted payload to the selected channel's endpoint.

        Args:
            channel: The selected channel.
            outbound_model: Model alias with the channel's suffix applied.
            payload: Converted request payload dict.
            request: The original gateway request.

        Returns:
            ``Ok(UpstreamResponse)`` or ``Err`` as returned by the
            adapter; the adapter already normalizes transport failures.
        """
        url = self._upstream_url(channel, outbound_model)
        logger.info(
            "relay_gateway_upstream_started",
            request_id=request.request_id,
            channel=channel.name,
            method="POST",
            url=url,
        )
        upstream = await self._upstream.request(
            UpstreamRequest(
                request_id=request.request_id,
                method="POST",
                url=url,
                headers={"content-type": "application/json"},
                payload=payload,
                timeout_seconds=channel.timeout_seconds,
                channel_name=channel.name,
            )
        )
        if upstream.is_err():
            err = upstream.unwrap_err()
            logger.warning(
                "relay_gateway_upstream_failed",
                request_id=request.request_id,
                channel=channel.name,
                code=err.code,
                status_code=err.status_code,
                error=str(err),
            )
        return upstream

    def _outbound_model(self, channel: RelayChannel, alias: str) -> str:
        """Resolve the upstream model name for *alias* on *channel*.

        The channel's ``model_map`` wins when it carries the alias;
        otherwise the alias is sent as-is.  The channel's configured
        suffix (e.g. ``":thinking"``) is appended after the mapping.

        Args:
            channel: The selected channel.
            alias: The client-visible model alias from the request.

        Returns:
            The model name sent to the channel's upstream.
        """
        return channel.resolve_model(alias) + self._config.model_suffix.get(
            channel.name, ""
        )

    @staticmethod
    def _should_track_upstream_failure(code: str) -> bool:
        """Return whether *code* counts toward a channel failover ban.

        Transport-level upstream failures count; a cancelled client
        request and a malformed but delivered 2xx body do not.

        Args:
            code: The gateway error code of the failed upstream call.

        Returns:
            ``True`` when the failure should count, ``False`` otherwise.
        """
        return code in {
            "UPSTREAM_ERROR",
            "UPSTREAM_TIMEOUT",
            "UPSTREAM_FAILED",
        }

    def _note_failure(self, channel_name: str) -> None:
        """Count one upstream failure against *channel_name*.

        Args:
            channel_name: The channel that failed upstream.
        """
        if self._failover is not None:
            self._failover.record_failure(channel_name)

    def _note_success(self, channel_name: str) -> None:
        """Reset *channel_name*'s failures and restore it when banned.

        Args:
            channel_name: The channel that succeeded upstream.
        """
        if self._failover is not None:
            self._failover.record_success(channel_name)

    def _upstream_url(self, channel: RelayChannel, model: str) -> str:
        """Build the endpoint URL for *channel*'s target format.

        Args:
            channel: The selected channel.
            model: Outbound model alias (embedded in the Gemini path).

        Returns:
            The standard endpoint path for the channel's target format
            joined onto the channel's base URL.

        Raises:
            ValueError: The channel's target format is not one of the
                four relay wire formats.  Unreachable via registry
                validation.
        """
        base = channel.upstream_base_url.rstrip("/")
        if channel.target_format == RelayFormat.OPENAI_CHAT:
            return f"{base}/v1/chat/completions"
        if channel.target_format == RelayFormat.OPENAI_RESPONSES:
            return f"{base}/v1/responses"
        if channel.target_format == RelayFormat.CLAUDE:
            return f"{base}/v1/messages"
        if channel.target_format == RelayFormat.GEMINI:
            return f"{base}/v1beta/models/{model}:generateContent"
        raise ValueError(f"unsupported target format: {channel.target_format}")

    @staticmethod
    def _unexpected_error(request_id: str) -> RelayGatewayError:
        """Build the generic error for unexpected dependency failures."""
        return RelayGatewayError(
            code=RelayGatewayErrorCode.CONVERSION_FAILED,
            message="Unexpected relay gateway failure",
            status_code=500,
            request_id=request_id,
            retryable=False,
        )
