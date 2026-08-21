"""Status-phase pipeline for the job-relay passthrough lifecycle.

``JobStatusPipeline`` polls a previously submitted job on the channel
that owns it: endpoint-kind validation, authorization, record lookup
with TTL eviction, channel affinity, and id rewriting.  Billing never
runs here — only the submit phase charges.  The public
``JobPassthroughService`` facade in
:mod:`lexigram.ai.relay.gateway.job_passthrough` wraps this pipeline
with request logging and unexpected-error containment.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.errors import auth_denied, with_request_id
from lexigram.ai.relay.gateway.job_registry import RelayJobRegistry
from lexigram.ai.relay.gateway.job_support import (
    JOB_ENDPOINT_PATHS,
    call_upstream,
    job_not_found_error,
    job_url,
    malformed_error,
    unsupported_kind_error,
)
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayGatewayResult,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger

__all__ = ["JobStatusPipeline"]

logger = get_logger(__name__)


class JobStatusPipeline:
    """Ordered status pipeline: validate, authorize, resolve, poll.

    Channel affinity holds across the pipeline: the channel is read
    from the stored job record, never re-selected, and the upstream
    job id from the record is inserted into the poll path.

    Args:
        registry: Channel registry; consulted only to re-resolve the
            recorded channel's static configuration at poll time.
        job_registry: Job record store providing channel affinity and
            TTL eviction on lookup.
        upstream: HTTP transport adapter; handles credential injection
            per channel through its configured provider.
        authorizer: Optional authorization check before dispatch; when
            ``None`` authorization is skipped.
    """

    def __init__(
        self,
        registry: RelayChannelRegistry,
        job_registry: RelayJobRegistry,
        upstream: HTTPUpstreamAdapter,
        *,
        authorizer: AuthorizerProtocol | None = None,
    ) -> None:
        self._registry = registry
        self.job_registry = job_registry
        self._upstream = upstream
        self._authorizer = authorizer

    async def dispatch(
        self,
        kind: str,
        gateway_job_id: str,
        request: RelayGatewayRequest,
    ) -> tuple[Result[RelayGatewayResult, RelayGatewayError], str]:
        """Run the ordered status pipeline for one job.

        Unknown, expired, and channel-gone records all map to the same
        not-found family as an unserved model.

        Args:
            kind: The endpoint kind the job was submitted through.
            gateway_job_id: The gateway-issued job id returned by the
                submit phase.
            request: The gateway request; only identity and request id
                are used.

        Returns:
            ``tuple`` of the pipeline result and the polled channel
            name, ``""`` when no record or channel was found.
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
        record = self.job_registry.get(gateway_job_id)
        if record is None:
            return (
                Err(job_not_found_error(gateway_job_id, request.request_id)),
                "",
            )
        if self._authorizer is not None and record.submitted_by != request.tenant_id:
            return (
                Err(job_not_found_error(gateway_job_id, request.request_id)),
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
        upstream_response = await call_upstream(
            self._upstream,
            "GET",
            job_url(
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
            return Err(malformed_error(request.request_id)), channel.name
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
