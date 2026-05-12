"""Passthrough relay lifecycle for non-chat endpoint kinds.

``PassthroughService`` relays endpoint kinds that do not fit the
chat-focused conversion engine (starting with embeddings) through the
generalized parts of the chat pipeline — channel selection by endpoint
kind, authorization, billing admission and settlement, and the upstream
HTTP adapter — while skipping ``RelayConverterProtocol`` entirely: the
wire format in is the wire format out, with the model alias
substituted only when the channel config declares a suffix.  The
upstream response is returned verbatim, unvalidated beyond the
adapter's existing malformed-body handling.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import time
from typing import Any, Literal, cast

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.errors import (
    auth_denied,
    billing_error_to_gateway,
    with_request_id,
)
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.governance import (
    RelayBillingProtocol,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayChannel,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayGatewayResult,
    RelayRequestPayload,
    RelayUsage,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger

__all__ = ["PassthroughService"]

logger = get_logger(__name__)

_ENDPOINT_PATHS: dict[str, str] = {
    "embeddings": "/v1/embeddings",
}
"""Endpoint kinds to upstream path segments served by this relay.

Every registered kind uses the OpenAI-shaped ``/v1/<kind>`` path; future
kinds with provider-specific shapes (multipart audio, binary images)
extend this table in their own plans.
"""


@dataclass(frozen=True, slots=True)
class _PassthroughPayloadCarrier:
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


class PassthroughService:
    """Endpoint-kind mapping: call one method, no conversion.

    The service is stateless between requests and never includes
    payloads or upstream details in error messages; errors are always
    safe ``RelayGatewayError`` values.  Authorization, billing, channel
    selection, and upstream transport reuse the chat pipeline's
    dependencies unchanged.

    Attributes:
        _registry: Deterministic channel selector.
        _upstream: HTTP transport adapter.
        _config: Gateway configuration (channel table and model suffixes).
        _authorizer: Optional authorization check before dispatch.
        _billing: Optional billing lifecycle; when ``None`` admission and
            settlement are skipped.
    """

    def __init__(
        self,
        registry: RelayChannelRegistry,
        upstream: HTTPUpstreamAdapter,
        config: RelayGatewayConfig,
        *,
        authorizer: AuthorizerProtocol | None = None,
        billing: RelayBillingProtocol | None = None,
    ) -> None:
        """Bind the service to its dependencies.

        Args:
            registry: Channel selection registry.
            upstream: Upstream transport adapter; handles credential
                injection per channel through its configured provider.
            config: Static gateway configuration.
            authorizer: Optional authorizer; when ``None`` authorization
                is skipped.
            billing: Optional billing lifecycle; when ``None`` the
                passthrough runs without admission control or settlement.
        """
        self._registry = registry
        self._upstream = upstream
        self._config = config
        self._authorizer = authorizer
        self._billing = billing

    async def handle(
        self, kind: str, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Run the passthrough lifecycle for one request.

        Dependencies run in fixed order: authorize, select channel by
        endpoint kind, reserve billing capacity, call upstream with the
        caller's body verbatim, settle billing, assemble result.  Any
        failure short-circuits the pipeline.

        Args:
            kind: The endpoint kind being served (e.g. ``"embeddings"``).
            request: The passthrough gateway request; ``source`` is a
                conventional marker (``OPENAI_CHAT``) and is never used
                for conversion.

        Returns:
            ``Ok(RelayGatewayResult)`` on success, or
            ``Err(RelayGatewayError)`` on the first failure.  Unexpected
            exceptions from dependencies never escape: they are logged
            and mapped to a generic ``CONVERSION_FAILED`` error.
        """
        started = time.monotonic()
        logger.info(
            "relay_passthrough_request_accepted",
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            endpoint=kind,
            model=request.model,
        )
        try:
            result, channel_name = await self._dispatch(kind, request)
        except Exception as exc:
            logger.warning(
                "relay_passthrough_unexpected_error",
                request_id=request.request_id,
                endpoint=kind,
                error=str(exc),
            )
            error = self._unexpected_error(request.request_id)
            self._log_request_completed(request, kind, "", error, started)
            return Err(error)
        if result.is_err():
            self._log_request_completed(
                request, kind, channel_name, result.unwrap_err(), started
            )
            return result
        outcome = result.unwrap()
        self._log_request_completed(request, kind, channel_name, outcome, started)
        return result

    async def _dispatch(
        self,
        kind: str,
        request: RelayGatewayRequest,
    ) -> tuple[Result[RelayGatewayResult, RelayGatewayError], str]:
        """Run the ordered dependency pipeline for one request.

        Returns:
            ``tuple`` of the pipeline result and the selected channel
            name.  The channel name is ``""`` when selection failed
            before a channel was chosen.
        """
        if kind not in _ENDPOINT_PATHS:
            return (
                Err(
                    RelayGatewayError(
                        code=RelayGatewayErrorCode.INVALID_REQUEST,
                        message="unsupported endpoint kind",
                        status_code=400,
                        request_id=request.request_id,
                        retryable=False,
                    )
                ),
                "",
            )
        if self._authorizer is not None:
            allowed = await self._authorizer.authorize(
                user=request.tenant_id,
                action="relay.invoke",
                resource=request.model,
            )
            if not allowed:
                return Err(auth_denied(request.request_id)), ""
        selected = self._registry.select_for_endpoint(
            kind=kind,
            model=request.model,
        )
        if selected.is_err():
            return (
                Err(with_request_id(selected.unwrap_err(), request.request_id)),
                "",
            )
        channel = selected.unwrap()
        logger.info(
            "relay_passthrough_channel_selected",
            request_id=request.request_id,
            endpoint=kind,
            channel=channel.name,
            model=request.model,
        )
        billing = self._billing
        reservation: RelayUsageReservation | None = None
        if billing is not None:
            admitted = await self._reserve(request, billing, channel)
            if admitted.is_err():
                return Err(admitted.unwrap_err()), channel.name
            reservation = admitted.unwrap()
        outbound_model = request.model + self._config.model_suffix.get(channel.name, "")
        outbound = dict(request.payload)
        outbound["model"] = outbound_model
        upstream_response = await self._call_upstream(kind, channel, outbound, request)
        if upstream_response.is_err():
            if billing is not None and reservation is not None:
                await self._settle_failed(billing, reservation)
            return (
                Err(
                    with_request_id(upstream_response.unwrap_err(), request.request_id)
                ),
                channel.name,
            )
        resp = upstream_response.unwrap()
        if resp.payload is None:
            if billing is not None and reservation is not None:
                await self._settle_failed(billing, reservation)
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
        if billing is not None and reservation is not None:
            await self._settle(
                billing,
                reservation,
                self._usage_from_response(resp.payload),
                status="completed",
            )
        return (
            Ok(
                RelayGatewayResult(
                    status_code=resp.status_code,
                    headers={**resp.headers, "x-request-id": request.request_id},
                    payload=resp.payload,
                    stream=None,
                    metadata=None,
                )
            ),
            channel.name,
        )

    async def _reserve(
        self,
        request: RelayGatewayRequest,
        billing: RelayBillingProtocol,
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
        carrier = _PassthroughPayloadCarrier(dict(request.payload))
        admitted = await billing.pre_consume(
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

    async def _settle(
        self,
        billing: RelayBillingProtocol,
        reservation: RelayUsageReservation,
        usage: RelayUsage | None,
        *,
        status: Literal["completed", "failed", "cancelled", "truncated"],
    ) -> None:
        """Settle the reservation exactly once without failing the response.

        Settlement failures are logged and never propagate: the response
        path has already completed by the time accounting runs.

        Args:
            billing: The billing lifecycle to settle through.
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
        settled = await billing.settle(reservation, result, status=status)
        if settled.is_err():
            error = settled.unwrap_err()
            logger.warning(
                "relay_passthrough_settle_failed",
                request_id=reservation.request_id,
                status=status,
                code=error.code,
                error=error.message,
            )

    async def _settle_failed(
        self,
        billing: RelayBillingProtocol,
        reservation: RelayUsageReservation,
    ) -> None:
        """Settle a failed attempt without usage through the billing pipeline.

        Args:
            billing: The billing lifecycle to settle through.
            reservation: The reservation granted by ``pre_consume``.
        """
        await self._settle(billing, reservation, None, status="failed")

    async def _call_upstream(
        self,
        kind: str,
        channel: RelayChannel,
        payload: dict[str, Any],
        request: RelayGatewayRequest,
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Send the passthrough body to the selected channel's endpoint.

        Uses the same ``HTTPUpstreamAdapter`` as the chat path, so
        channel-credential injection applies unchanged.

        Args:
            kind: The endpoint kind being served, selecting the wire path.
            channel: The selected channel.
            payload: The caller's body with the model substituted.
            request: The original gateway request.

        Returns:
            ``Ok(UpstreamResponse)`` or ``Err`` as returned by the
            adapter; the adapter already normalizes transport failures.
        """
        url = self._endpoint_url(kind, channel)
        logger.info(
            "relay_passthrough_upstream_started",
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
                "relay_passthrough_upstream_failed",
                request_id=request.request_id,
                channel=channel.name,
                code=err.code,
                status_code=err.status_code,
                error=str(err),
            )
        return upstream

    def _endpoint_url(self, kind: str, channel: RelayChannel) -> str:
        """Build the endpoint URL for *kind* on *channel*.

        Args:
            kind: The endpoint kind being served.
            channel: The selected channel.

        Returns:
            ``<channel base>/v1/<kind>`` for a registered kind; the
            kind was validated against ``_ENDPOINT_PATHS`` before the
            channel call, so this never misses.
        """
        base = channel.upstream_base_url.rstrip("/")
        return f"{base}{_ENDPOINT_PATHS[kind]}"

    @staticmethod
    def _usage_from_response(payload: Mapping[str, Any]) -> RelayUsage | None:
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

    def _log_request_completed(
        self,
        request: RelayGatewayRequest,
        kind: str,
        channel_name: str,
        outcome: RelayGatewayResult | RelayGatewayError,
        started: float,
    ) -> None:
        """Emit the terminal request-completed event for any outcome.

        Args:
            request: The original gateway request.
            kind: The endpoint kind that was served.
            channel_name: Selected channel name (or ``""`` when unknown).
            outcome: The success result or the error that ended the flow.
            started: Monotonic start time used to compute the duration.
        """
        logger.info(
            "relay_passthrough_request_completed",
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            endpoint=kind,
            channel=channel_name,
            status_code=outcome.status_code,
            code=outcome.code if isinstance(outcome, RelayGatewayError) else "OK",
            duration_ms=round((time.monotonic() - started) * 1000, 2),
        )
