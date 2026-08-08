"""Upstream invocation helpers for the relay gateway service.

Builds endpoint URLs and outbound model names from channel state, wraps
the upstream HTTP call with structured events, and records consecutive
failures against the failover tracker.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.failover import RelayFailoverTracker
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayUpstreamProtocol,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.core.result import Result
from lexigram.logging import get_logger

__all__ = [
    "call_upstream",
    "note_failure",
    "note_success",
    "outbound_model",
    "should_track_upstream_failure",
    "upstream_url",
]

logger = get_logger(__name__)


def upstream_url(channel: RelayChannel, model: str) -> str:
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


def outbound_model(
    config: RelayGatewayConfig, channel: RelayChannel, alias: str
) -> str:
    """Resolve the upstream model name for *alias* on *channel*.

    The channel's ``model_map`` wins when it carries the alias;
    otherwise the alias is sent as-is.  The channel's configured
    suffix (e.g. ``":thinking"``) is appended after the mapping.

    Args:
        config: Gateway configuration carrying the model suffix table.
        channel: The selected channel.
        alias: The client-visible model alias from the request.

    Returns:
        The model name sent to the channel's upstream.
    """
    return channel.resolve_model(alias) + config.model_suffix.get(channel.name, "")


def should_track_upstream_failure(code: str) -> bool:
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


def note_failure(failover: RelayFailoverTracker | None, channel_name: str) -> None:
    """Count one upstream failure against *channel_name*.

    Args:
        failover: The failover tracker; ``None`` disables accounting.
        channel_name: The channel that failed upstream.
    """
    if failover is not None:
        failover.record_failure(channel_name)


def note_success(failover: RelayFailoverTracker | None, channel_name: str) -> None:
    """Reset *channel_name*'s failures and restore it when banned.

    Args:
        failover: The failover tracker; ``None`` disables accounting.
        channel_name: The channel that succeeded upstream.
    """
    if failover is not None:
        failover.record_success(channel_name)


async def call_upstream(
    upstream: RelayUpstreamProtocol,
    channel: RelayChannel,
    outbound_model: str,
    payload: dict[str, Any],
    request: RelayGatewayRequest,
) -> Result[UpstreamResponse, RelayGatewayError]:
    """Send the converted payload to the selected channel's endpoint.

    Args:
        upstream: The upstream transport adapter.
        channel: The selected channel.
        outbound_model: Model alias with the channel's suffix applied.
        payload: Converted request payload dict.
        request: The original gateway request.

    Returns:
        ``Ok(UpstreamResponse)`` or ``Err`` as returned by the
        adapter; the adapter already normalizes transport failures.
    """
    url = upstream_url(channel, outbound_model)
    logger.info(
        "relay_gateway_upstream_started",
        request_id=request.request_id,
        channel=channel.name,
        method="POST",
        url=url,
    )
    result = await upstream.request(
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
    if result.is_err():
        error = result.unwrap_err()
        logger.warning(
            "relay_gateway_upstream_failed",
            request_id=request.request_id,
            channel=channel.name,
            code=error.code,
            status_code=error.status_code,
            error=str(error),
        )
    return result
