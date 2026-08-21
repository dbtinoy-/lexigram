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

Implementation lives in three focused modules:

- :mod:`lexigram.ai.relay.gateway.job_support` — shared primitives:
  endpoint-kind table, upstream call helper, URL construction, and
  safe gateway-error builders.
- :mod:`lexigram.ai.relay.gateway.job_submit_service` — the ordered
  submit pipeline (authorize, select, reserve, forward, record,
  settle).
- :mod:`lexigram.ai.relay.gateway.job_status_service` — the ordered
  status pipeline (authorize, resolve record, poll owning channel).

This module keeps the public ``JobPassthroughService`` surface so
existing imports keep resolving unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
import time

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.job_registry import RelayJobRegistry
from lexigram.ai.relay.gateway.job_status_service import JobStatusPipeline
from lexigram.ai.relay.gateway.job_submit_service import JobSubmitPipeline
from lexigram.ai.relay.gateway.job_support import unexpected_error
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.governance import RelayBillingProtocol
from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    RelayGatewayRequest,
    RelayGatewayResult,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Result
from lexigram.logging import get_logger

__all__ = ["JobPassthroughService"]

logger = get_logger(__name__)


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
        _submit: Submit-phase pipeline.
        _status: Status-phase pipeline.
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
        self._submit = JobSubmitPipeline(
            registry,
            job_registry,
            upstream,
            config,
            authorizer=authorizer,
            billing=billing,
            clock=clock,
        )
        self._status = JobStatusPipeline(
            registry,
            job_registry,
            upstream,
            authorizer=authorizer,
        )

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
            result, channel_name = await self._submit.dispatch(kind, request)
        except Exception as exc:
            logger.warning(
                "relay_job_submit_unexpected_error",
                request_id=request.request_id,
                endpoint=kind,
                error=str(exc),
            )
            result = Err(unexpected_error(request.request_id))
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
            result, channel_name = await self._status.dispatch(
                kind, gateway_job_id, request
            )
        except Exception as exc:
            logger.warning(
                "relay_job_status_unexpected_error",
                request_id=request.request_id,
                endpoint=kind,
                error=str(exc),
            )
            result = Err(unexpected_error(request.request_id))
            channel_name = ""
        outcome: RelayGatewayResult | RelayGatewayError = (
            result.unwrap_err() if result.is_err() else result.unwrap()
        )
        self._log_request_completed(
            request, kind, "status", channel_name, outcome, started
        )
        return result

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
