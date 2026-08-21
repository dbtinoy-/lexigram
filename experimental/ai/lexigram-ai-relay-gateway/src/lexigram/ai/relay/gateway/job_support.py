"""Shared primitives for the job-relay passthrough lifecycle.

Stateless building blocks used by both phases of the job relay: the
endpoint-kind table, the upstream call helper with credential-injection
logging, URL construction, and the safe gateway-error builders.  Split
out of :mod:`lexigram.ai.relay.gateway.job_passthrough` so the submit
and status pipelines stay focused on their ordered dependency pipelines.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayGatewayError,
    RelayGatewayRequest,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.core.result import Result
from lexigram.logging import get_logger

__all__ = [
    "JOB_ENDPOINT_PATHS",
    "call_upstream",
    "job_not_found_error",
    "job_url",
    "malformed_error",
    "missing_id_error",
    "unexpected_error",
    "unsupported_kind_error",
]

logger = get_logger(__name__)

JOB_ENDPOINT_PATHS: dict[str, str] = {
    "video_generation": "/v1/videos",
}
"""Endpoint kinds to upstream submit path segments served by job relay.

Every registered kind uses the OpenAI-shaped ``/v1/<kind>`` submit path;
the status poll for a record reuses its stored kind's path.  Music
generation is deliberately absent: no ``lexigram-multimedia-music``
provider exists to relay to (see the async job-relay plan).
"""


async def call_upstream(
    upstream: HTTPUpstreamAdapter,
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
        upstream: The transport adapter shared by both job phases.
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
    result = await upstream.request(
        UpstreamRequest(
            request_id=request.request_id,
            method=method,
            url=url,
            headers={"content-type": "application/json"} if method == "POST" else {},
            payload=payload if payload is not None else {},
            timeout_seconds=channel.timeout_seconds,
            channel_name=channel.name,
        )
    )
    if result.is_err():
        err = result.unwrap_err()
        logger.warning(
            "relay_job_upstream_failed",
            request_id=request.request_id,
            channel=channel.name,
            code=err.code,
            status_code=err.status_code,
            error=str(err),
        )
    return result


def job_url(
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
    url = f"{base}{JOB_ENDPOINT_PATHS[kind]}"
    if job_id is not None:
        url = f"{url}/{job_id}"
    return url


def unsupported_kind_error(request_id: str) -> RelayGatewayError:
    """Build the 400 error for an endpoint kind outside the job table."""
    return RelayGatewayError(
        code=RelayGatewayErrorCode.INVALID_REQUEST,
        message="unsupported endpoint kind",
        status_code=400,
        request_id=request_id,
        retryable=False,
    )


def missing_id_error(request_id: str) -> RelayGatewayError:
    """Build the mapping error for a submit response without a job id."""
    return RelayGatewayError(
        code=RelayGatewayErrorCode.UPSTREAM_MALFORMED,
        message="upstream submit response missing job id",
        status_code=502,
        request_id=request_id,
        retryable=False,
    )


def job_not_found_error(gateway_job_id: str, request_id: str) -> RelayGatewayError:
    """Build the not-found error for an unknown or expired job id."""
    return RelayGatewayError(
        code=RelayGatewayErrorCode.MODEL_NOT_FOUND,
        message=f"no relay job found for id {gateway_job_id}",
        status_code=404,
        request_id=request_id,
        retryable=False,
    )


def malformed_error(request_id: str) -> RelayGatewayError:
    """Build the gateway error for a malformed upstream response body."""
    return RelayGatewayError(
        code=RelayGatewayErrorCode.UPSTREAM_MALFORMED,
        message="malformed upstream response",
        status_code=502,
        request_id=request_id,
        retryable=False,
    )


def unexpected_error(request_id: str) -> RelayGatewayError:
    """Build the generic error for unexpected dependency failures."""
    return RelayGatewayError(
        code=RelayGatewayErrorCode.CONVERSION_FAILED,
        message="Unexpected relay gateway failure",
        status_code=500,
        request_id=request_id,
        retryable=False,
    )
