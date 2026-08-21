"""Submit-phase pipeline for the job-relay passthrough lifecycle.

``JobSubmitPipeline`` runs the ordered submit dependencies for one
job-relay request: endpoint-kind validation, authorization, channel
selection, billing admission, upstream forwarding through credential
injection, job-record storage, and single settlement.  The public
``JobPassthroughService`` facade in
:mod:`lexigram.ai.relay.gateway.job_passthrough` wraps this pipeline
with request logging and unexpected-error containment.
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
from lexigram.ai.relay.gateway.job_support import (
    JOB_ENDPOINT_PATHS,
    call_upstream,
    job_url,
    malformed_error,
    missing_id_error,
    unsupported_kind_error,
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
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger

__all__ = ["JobSubmitPipeline"]

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class JobPayloadCarrier:
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


class JobSubmitPipeline:
    """Ordered submit pipeline: validate, authorize, select, bill, send.

    The pipeline is stateless across requests except for the injected
    job registry, into which every successful submit stores a
    ``RelayJobRecord`` mapping the gateway-issued id to the upstream's
    job id and owning channel.

    Args:
        registry: Deterministic channel selector.
        job_registry: Job record store providing channel affinity.
        upstream: HTTP transport adapter; handles credential injection
            per channel through its configured provider.
        config: Static gateway configuration (model suffixes).
        authorizer: Optional authorization check before dispatch; when
            ``None`` authorization is skipped.
        billing: Optional billing lifecycle; when ``None`` jobs run
            without admission control or settlement.
        clock: Callable returning the current monotonic time, stamped
            on created job records.
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
        self._registry = registry
        self.job_registry = job_registry
        self._upstream = upstream
        self._config = config
        self._authorizer = authorizer
        self._billing = billing
        self._clock = clock

    async def dispatch(
        self,
        kind: str,
        request: RelayGatewayRequest,
    ) -> tuple[Result[RelayGatewayResult, RelayGatewayError], str]:
        """Run the ordered submit pipeline for one job.

        Billing is admitted and settled exactly once, here; a
        subsequent status call never re-charges.

        Args:
            kind: The endpoint kind being served (e.g.
                ``"video_generation"``).
            request: The gateway request; the body is forwarded to the
                selected channel's submit path verbatim.

        Returns:
            ``tuple`` of the pipeline result and the selected channel
            name.  The channel name is ``""`` when selection failed
            before a channel was chosen.
        """
        if kind not in JOB_ENDPOINT_PATHS:
            return Err(unsupported_kind_error(request.request_id)), ""
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
        upstream_response = await call_upstream(
            self._upstream,
            "POST",
            job_url(kind, channel),
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
            return Err(malformed_error(request.request_id)), channel.name
        upstream_job_id = self._extract_job_id(resp.payload)
        if upstream_job_id is None:
            if billing is not None and reservation is not None:
                await self._settle_failed(billing, reservation)
            return Err(missing_id_error(request.request_id)), channel.name
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
        carrier = JobPayloadCarrier(dict(request.payload))
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
