"""Relay gateway request lifecycle (buffered and streaming).

``RelayGatewayService`` orchestrates one request through the
dependencies: authorization, channel selection, billing admission, request
conversion, the protected upstream call, response conversion, billing
settlement, and result metadata assembly.  Streaming requests run the
same preflight and then consume the upstream SSE stream lazily through
the stream session, settling billing exactly once when the stream ends.

The pipeline's specialized concerns live in focused modules:

- :mod:`lexigram.ai.relay.gateway.validation` — request boundary checks.
- :mod:`lexigram.ai.relay.gateway.buffered` — buffered dispatch pipeline.
- :mod:`lexigram.ai.relay.gateway.streaming` — streaming preflight and
  lazy stream consumption with exactly-once settlement.
- :mod:`lexigram.ai.relay.gateway.operations.billing` — admission and
  settlement lifecycle.
- :mod:`lexigram.ai.relay.gateway.operations.upstream` — endpoint URLs,
  model resolution, upstream calls, and failover accounting.
- :mod:`lexigram.ai.relay.gateway.operations.telemetry` — structured
  request events.

``config.provider_options`` are intentionally not merged into
``RelayOptions`` yet because no mapping schema exists.
"""

from __future__ import annotations

import time

from lexigram.ai.relay.gateway.buffered import BufferedDispatchMixin
from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.errors import unexpected_error
from lexigram.ai.relay.gateway.operations import telemetry
from lexigram.ai.relay.gateway.operations.failover import RelayFailoverTracker
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.ai.relay.gateway.streaming import StreamingMixin
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.ai.relay.gateway.validation import validate_gateway_request
from lexigram.contracts.ai.governance import RelayBillingProtocol
from lexigram.contracts.ai.relay import (
    MediaResolverProtocol,
    RelayConverterProtocol,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayGatewayResult,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Result
from lexigram.logging import get_logger

__all__ = ["RelayGatewayService", "validate_gateway_request"]

logger = get_logger(__name__)


class RelayGatewayService(BufferedDispatchMixin, StreamingMixin):
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
