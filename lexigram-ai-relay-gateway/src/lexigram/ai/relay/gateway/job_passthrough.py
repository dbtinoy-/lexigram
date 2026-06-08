"""Job-relay passthrough lifecycle for job-based media generation.

``JobPassthroughService`` relays endpoint kinds whose upstream protocol is
submit-then-poll (starting with video generation) through the same
channel-selection, authorization, billing-admission/settlement, and
credential-injection pipeline as ``PassthroughService``, plus channel
affinity across the two or more HTTP calls of one job.

``submit`` selects a channel by endpoint kind, reserves and settles
billing once, forwards the caller's body to the channel's submit path,
and stores a :class:`RelayJobRecord` mapping a gateway-issued job id to
the upstream's own job id and the owning channel.  The submit response
has its ``id`` field rewritten to the gateway-issued id, so the caller
never observes the upstream job id or which channel served it.
``status`` looks the record up (evicting TTL-expired records), routes the
poll to the *same* channel through the same credential injection as the
submit, authorizes the caller but never re-bills, and rewrites the
response ``id`` back to the gateway-issued id.  Records live in an
in-memory registry: a gateway process restart loses in-flight job
mappings, and a caller polling a lost or expired job receives the same
``MODEL_NOT_FOUND``-family error as an unknown id.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
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
from lexigram.ai.relay.gateway.job_registry import RelayJobRecord, RelayJobRegistry
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

__all__ = ["JobPassthroughService"]

logger = get_logger(__name__)

_JOB_ENDPOINT_PATHS: dict[str, str] = {
    "video_generation": "/v1/videos",
}
"""Endpoint kinds to upstream submit path segments served by job relay.

Every registered kind uses the OpenAI-shaped ``/v1/<kind>`` submit path;
the status poll for a record reuses its stored kind's path.  Music
generation is deliberately absent: no ``lexigram-multimedia-music``
provider exists to relay to (see the async job-relay plan).
"""


@dataclass(frozen=True, slots=True)
class _JobPayloadCarrier:
    """Billing-admission carrier for a job-relay request body.

    Identical in purpose to the passthrough carrier: the body is not a
    chat wire DTO, so prompt estimation counts the serialized body and
    the output budget is reserved as zero.  The carrier quacks like a
    ``RelayRequestPayload`` at the only call site the billing pipeline
    uses (``to_dict``).
    """

    body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return the job-relay request body.

        Returns:
            A shallow copy of the forwarded request body.
        """
        return dict(self.body)


class JobPassthroughService:
    """Submit/poll relay lifecycle with per-job channel affinity.

    The service is stateful in exactly one dimension: it stores the
    channel name and upstream job id of every submitted job in the
    injected ``RelayJobRegistry`` so subsequent polls route to the same
    channel, and it never includes payloads or upstream details in error
    messages; errors are always safe ``RelayGatewayError`` values.

    Attributes:
        job_registry: Stores the channel-affinity mapping for in-flight
            jobs; also evicts TTL-expired records on lookup.
        _registry: Deterministic channel selector.
        _upstream: HTTP transport adapter; handles credential injection
            per channel through its configured provider.
        _config: Gateway configuration (channel table, model suffixes,
            and the job TTL).
        _authorizer: Optional authorization check before dispatch.
        _billing: Optional billing lifecycle; when ``None`` jobs run
            without admission control or settlement.
    """

    def __init__(
        self,
        registry: RelayChannelRegistry,
        job_registry: RelayJobRegistry,
        upstream: HTTPUpstreamAdapter,
        config: RelayGatewayConfig,
        *,
        authorizer: AuthorizerProtocol | None = None,
        billing: RelayBillingProtocol | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Bind the service to its dependencies.

        Args:
            registry: Channel selection registry.
            job_registry: Job record store providing channel affinity
                and TTL eviction.
            upstream: Upstream transport adapter; handles credential
                injection per channel through its configured provider.
            config: Static gateway configuration.
            authorizer: Optional authorizer; when ``None`` authorization
                is skipped.
            billing: Optional billing lifecycle; when ``None`` jobs run
                without admission control or settlement.
            clock: Callable returning the current monotonic time,
                stamped on created job records.  Defaults to
                ``time.monotonic``; tests inject a fake consistent with
                the job registry's.
        """
        self.job_registry = job_registry
        self._registry = registry
        self._upstream = upstream
        self._config = config
        self._authorizer = authorizer
        self._billing = billing
        self._clock = clock

    async def submit(
        self, kind: str, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Submit a job: authorize, select, reserve, forward, record.

        Runs the ordered dependency pipeline, then stores a
        ``RelayJobRecord`` mapping the gateway-issued job id to the
        upstream's job id and the owning channel, and returns the
        upstream response with its ``id`` field rewritten to the
        gateway-issued id.  Billing is admitted and settled exactly once,
        here; a subsequent ``status`` call never re-charges.

        Args:
            kind: The endpoint kind being served (e.g.
                ``"video_generation"``).
            request: The gateway request; the body is forwarded to the
                selected channel's submit path verbatim.

        Returns:
            ``Ok(RelayGatewayResult)`` carrying the id-rewritten upstream
            response on success, or ``Err(RelayGatewayError)`` on the
            first failure.  Unexpected exceptions never escape: they are
            logged and mapped to a generic ``CONVERSION_FAILED`` error.
        """
        started = time.monotonic()
        logger.info(
            "relay_job_submit_accepted",
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            endpoint=kind,
            model=request.model,
        )
        try:
            result, channel_name = await self._dispatch_submit(kind, request)
        except Exception as exc:
            logger.warning(
                "relay_job_submit_unexpected_error",
                request_id=request.request_id,
                endpoint=kind,
                error=str(exc),
            )
            result = Err(self._unexpected_error(request.request_id))
            channel_name = ""
        outcome: RelayGatewayResult | RelayGatewayError = (
            result.unwrap_err() if result.is_err() else result.unwrap()
        )
        self._log_request_completed(
            request, kind, "submit", channel_name, outcome, started
        )
        return result

    async def status(
        self, kind: str, gateway_job_id: str, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Poll a submitted job on the channel that owns it.

        Looks up the job record by the gateway-issued id (silently
        evicting TTL-expired records), authorizes the caller, and polls
        the owning channel's status path with the stored upstream job id
        — the record's channel is reused, never re-selected.  The
        response ``id`` is rewritten back to the gateway-issued id.
        Billing never runs here: only ``submit`` charges.

        Args:
            kind: The endpoint kind the job was submitted through.
            gateway_job_id: The gateway-issued job id returned by
                ``submit``.
            request: The gateway request; only identity and request id
                are used.

        Returns:
            ``Ok(RelayGatewayResult)`` carrying the id-rewritten status
            response on success, or ``Err(RelayGatewayError)``.  Unknown
            and TTL-expired job ids both map to the same
            ``MODEL_NOT_FOUND``-family error ``select_for_endpoint``
            produces for an unmatched model.  Unexpected exceptions
            never escape: they are logged and mapped to a generic
            ``CONVERSION_FAILED`` error.
        """
        started = time.monotonic()
        logger.info(
            "relay_job_status_accepted",
            request_id=request.request_id,
            endpoint=kind,
        )
        try:
            result, channel_name = await self._dispatch_status(
                kind, gateway_job_id, request
            )
        except Exception as exc:
            logger.warning(
                "relay_job_status_unexpected_error",
                request_id=request.request_id,
                endpoint=kind,
                error=str(exc),
            )
            result = Err(self._unexpected_error(request.request_id))
            channel_name = ""
        outcome: RelayGatewayResult | RelayGatewayError = (
            result.unwrap_err() if result.is_err() else result.unwrap()
        )
        self._log_request_completed(
            request, kind, "status", channel_name, outcome, started
        )
        return result

    async def _dispatch_submit(
        self,
        kind: str,
        request: RelayGatewayRequest,
    ) -> tuple[Result[RelayGatewayResult, RelayGatewayError], str]:
        """Run the ordered submit pipeline for one job.

        Returns:
            ``tuple`` of the pipeline result and the selected channel
            name.  The channel name is ``""`` when selection failed
            before a channel was chosen.
        """
        if kind not in _JOB_ENDPOINT_PATHS:
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
            "relay_job_channel_selected",
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
        upstream_response = await self._call_upstream(
            "POST",
            self._job_url(kind, channel),
            channel,
            outbound,
            request,
        )
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
            return Err(self._malformed_error(request.request_id)), channel.name
        upstream_job_id = self._extract_job_id(resp.payload)
        if upstream_job_id is None:
            if billing is not None and reservation is not None:
                await self._settle_failed(billing, reservation)
            return Err(self._missing_id_error(request.request_id)), channel.name
        gateway_job_id = self.job_registry.put(
            RelayJobRecord(
                channel_name=channel.name,
                upstream_job_id=upstream_job_id,
                endpoint_kind=kind,
                submitted_by=request.tenant_id,
                created_at=self._clock(),
            )
        )
        rewritten = dict(resp.payload or {})
        rewritten["id"] = gateway_job_id
        if billing is not None and reservation is not None:
            await self._settle(
                billing,
                reservation,
                self._usage_from_response(rewritten),
                status="completed",
            )
        return (
            Ok(
                RelayGatewayResult(
                    status_code=resp.status_code,
                    headers={**resp.headers, "x-request-id": request.request_id},
                    payload=rewritten,
                    stream=None,
                    metadata=None,
                )
            ),
            channel.name,
        )

    async def _dispatch_status(
        self,
        kind: str,
        gateway_job_id: str,
        request: RelayGatewayRequest,
    ) -> tuple[Result[RelayGatewayResult, RelayGatewayError], str]:
        """Run the ordered status pipeline for one job.

        Channel affinity holds here: the channel is read from the stored
        record, never re-selected, and the upstream job id from the
        record is inserted into the poll path.  Unknown, expired, and
        channel-gone records all map to the same not-found family as an
        unserved model.

        Returns:
            ``tuple`` of the pipeline result and the polled channel
            name, ``""`` when no record or channel was found.
        """
        if kind not in _JOB_ENDPOINT_PATHS:
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
        record = self.job_registry.get(gateway_job_id)
        if record is None:
            return (
                Err(self._job_not_found_error(gateway_job_id, request.request_id)),
                "",
            )
        if self._authorizer is not None and record.submitted_by != request.tenant_id:
            return (
                Err(self._job_not_found_error(gateway_job_id, request.request_id)),
                "",
            )
        channel = self._channel_by_name(record.channel_name)
        if channel is None:
            logger.warning(
                "relay_job_channel_missing",
                request_id=request.request_id,
                job_id=gateway_job_id,
                channel=record.channel_name,
            )
            return (
                Err(
                    RelayGatewayError(
                        code=RelayGatewayErrorCode.MODEL_NOT_FOUND,
                        message="no relay channel available for this job",
                        status_code=404,
                        request_id=request.request_id,
                        retryable=False,
                    )
                ),
                "",
            )
        upstream_response = await self._call_upstream(
            "GET",
            self._job_url(
                record.endpoint_kind,
                channel,
                job_id=record.upstream_job_id,
            ),
            channel,
            {},
            request,
        )
        if upstream_response.is_err():
            return (
                Err(
                    with_request_id(upstream_response.unwrap_err(), request.request_id)
                ),
                channel.name,
            )
        resp = upstream_response.unwrap()
        if resp.payload is None:
            return (
                Err(self._malformed_error(request.request_id)),
                channel.name,
            )
        rewritten = dict(resp.payload)
        if "id" in rewritten:
            rewritten["id"] = gateway_job_id
        return (
            Ok(
                RelayGatewayResult(
                    status_code=resp.status_code,
                    headers={**resp.headers, "x-request-id": request.request_id},
                    payload=rewritten,
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
        """Reserve billing capacity before the upstream submit call.

        The job-relay body is wrapped in a transparent carrier so the
        shared billing pipeline can estimate prompt tokens from the
        serialized body; the output budget is unknown and reserved as
        zero.  Billing denials fail the submit and are classified
        through :func:`billing_error_to_gateway`.

        Args:
            request: The job submit request being dispatched.
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
        carrier = _JobPayloadCarrier(dict(request.payload))
        admitted = await billing.pre_consume(
            request.request_id,
            scope,
            cast("RelayRequestPayload", carrier),
        )
        if admitted.is_err():
            error = admitted.unwrap_err()
            logger.warning(
                "relay_job_billing_denied",
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

        Settlement failures are logged and never propagate: the
        response path has already completed by the time accounting runs.

        Args:
            billing: The billing lifecycle to settle through.
            reservation: The reservation granted by ``pre_consume``.
            usage: The usage extracted from the upstream submit response,
                or ``None`` when the response omits it.
            status: Terminal lifecycle status of the job attempt.
        """
        result = RelayConvertResult[Any](
            value=None,
            source=RelayFormat.OPENAI_CHAT,
            target=RelayFormat.OPENAI_CHAT,
            converter_id="job_passthrough",
            quality=ConversionQuality.GOOD,
            usage=usage,
        )
        settled = await billing.settle(reservation, result, status=status)
        if settled.is_err():
            error = settled.unwrap_err()
            logger.warning(
                "relay_job_settle_failed",
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
        """Settle a failed submit attempt without usage.

        Args:
            billing: The billing lifecycle to settle through.
            reservation: The reservation granted by ``pre_consume``.
        """
        await self._settle(billing, reservation, None, status="failed")

    async def _call_upstream(
        self,
        method: str,
        url: str,
        channel: RelayChannel,
        payload: dict[str, Any] | None,
        request: RelayGatewayRequest,
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Send one upstream call through the channel's credential injection.

        Uses the same ``HTTPUpstreamAdapter`` as the chat path, so
        channel-credential injection applies unchanged.  The status poll
        carries no body.

        Args:
            method: HTTP method of the call (``"POST"`` for submit,
                ``"GET"`` for status).
            url: Fully-resolved upstream URL.
            channel: The channel the call is pinned to.
            payload: The JSON body to send, or ``None`` for body-less
                calls.
            request: The originating gateway request.

        Returns:
            ``Ok(UpstreamResponse)`` or ``Err`` as returned by the
            adapter; the adapter already normalizes transport failures.
        """
        logger.info(
            "relay_job_upstream_started",
            request_id=request.request_id,
            channel=channel.name,
            method=method,
            url=url,
        )
        upstream = await self._upstream.request(
            UpstreamRequest(
                request_id=request.request_id,
                method=method,
                url=url,
                headers={"content-type": "application/json"}
                if method == "POST"
                else {},
                payload=payload if payload is not None else {},
                timeout_seconds=channel.timeout_seconds,
                channel_name=channel.name,
            )
        )
        if upstream.is_err():
            err = upstream.unwrap_err()
            logger.warning(
                "relay_job_upstream_failed",
                request_id=request.request_id,
                channel=channel.name,
                code=err.code,
                status_code=err.status_code,
                error=str(err),
            )
        return upstream

    def _channel_by_name(self, name: str) -> RelayChannel | None:
        """Return the configured channel with *name*, or ``None`` when gone.

        Args:
            name: Channel name stored on a job record.

        Returns:
            The matching channel from the registry's static table, or
            ``None`` when the channel was removed from configuration
            since the job was submitted.
        """
        for channel in self._registry.channels:
            if channel.name == name:
                return channel
        return None

    def _job_url(
        self,
        kind: str,
        channel: RelayChannel,
        *,
        job_id: str | None = None,
    ) -> str:
        """Build the upstream URL for a job call on *channel*.

        Args:
            kind: The endpoint kind selecting the path segment; only
                registered kinds reach this call.
            channel: The channel the call is pinned to.
            job_id: The upstream job id to append for status polls;
                ``None`` for the submit path.

        Returns:
            ``<channel base>/v1/<kind>`` for submits, and the same path
            with ``/<job_id>`` appended for status polls.
        """
        base = channel.upstream_base_url.rstrip("/")
        url = f"{base}{_JOB_ENDPOINT_PATHS[kind]}"
        if job_id is not None:
            url = f"{url}/{job_id}"
        return url

    @staticmethod
    def _extract_job_id(payload: Mapping[str, Any]) -> str | None:
        """Extract the upstream job id from a submit response body.

        Args:
            payload: The upstream submit response body.

        Returns:
            The non-empty string ``id`` field, or ``None`` when absent
            or not a non-empty string — the caller treats that as a
            mapping error rather than recording a null job id.
        """
        job_id = payload.get("id")
        if isinstance(job_id, str) and job_id:
            return job_id
        return None

    @staticmethod
    def _missing_id_error(request_id: str) -> RelayGatewayError:
        """Build the mapping error for a submit response without a job id."""
        return RelayGatewayError(
            code=RelayGatewayErrorCode.UPSTREAM_MALFORMED,
            message="upstream submit response missing job id",
            status_code=502,
            request_id=request_id,
            retryable=False,
        )

    @staticmethod
    def _job_not_found_error(gateway_job_id: str, request_id: str) -> RelayGatewayError:
        """Build the not-found error for an unknown or expired job id."""
        return RelayGatewayError(
            code=RelayGatewayErrorCode.MODEL_NOT_FOUND,
            message=f"no relay job found for id {gateway_job_id}",
            status_code=404,
            request_id=request_id,
            retryable=False,
        )

    @staticmethod
    def _malformed_error(request_id: str) -> RelayGatewayError:
        """Build the gateway error for a malformed upstream response body."""
        return RelayGatewayError(
            code=RelayGatewayErrorCode.UPSTREAM_MALFORMED,
            message="malformed upstream response",
            status_code=502,
            request_id=request_id,
            retryable=False,
        )

    @staticmethod
    def _usage_from_response(payload: Mapping[str, Any]) -> RelayUsage | None:
        """Extract normalized usage from an OpenAI-shaped response body.

        Args:
            payload: The upstream submit response body.

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
        phase: str,
        channel_name: str,
        outcome: RelayGatewayResult | RelayGatewayError,
        started: float,
    ) -> None:
        """Emit the terminal completed event for any outcome.

        Args:
            request: The original gateway request.
            kind: The endpoint kind that was served.
            phase: ``"submit"`` or ``"status"``.
            channel_name: Selected channel name (or ``""`` when unknown).
            outcome: The success result or the error that ended the flow.
            started: Monotonic start time used to compute the duration.
        """
        logger.info(
            "relay_job_request_completed",
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            endpoint=kind,
            phase=phase,
            channel=channel_name,
            status_code=outcome.status_code,
            code=outcome.code if isinstance(outcome, RelayGatewayError) else "OK",
            duration_ms=round((time.monotonic() - started) * 1000, 2),
        )
