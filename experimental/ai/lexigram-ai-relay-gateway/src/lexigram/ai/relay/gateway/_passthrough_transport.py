"""Upstream transport for the passthrough relay path.

Maps endpoint kinds to upstream paths and sends the caller's body to the
selected channel's endpoint through the same ``HTTPUpstreamAdapter`` used
by the chat path, so channel-credential injection applies unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.relay import (
    JsonValue,
    RelayChannel,
    RelayGatewayError,
    RelayGatewayRequest,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.core.result import Result
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["ENDPOINT_PATHS", "call_upstream", "endpoint_url"]

ENDPOINT_PATHS: dict[str, str] = {
    "embeddings": "/v1/embeddings",
}
"""Endpoint kinds to upstream path segments served by this relay.

Every registered kind uses the OpenAI-shaped ``/v1/<kind>`` path; future
kinds with provider-specific shapes (multipart audio, binary images)
extend this table in their own plans.
"""


def endpoint_url(kind: str, channel: RelayChannel) -> str:
    """Build the endpoint URL for *kind* on *channel*.

    Args:
        kind: The endpoint kind being served.
        channel: The selected channel.

    Returns:
        ``<channel base>/v1/<kind>`` for a registered kind; the
        kind was validated against ``ENDPOINT_PATHS`` before the
        channel call, so this never misses.
    """
    base = channel.upstream_base_url.rstrip("/")
    return f"{base}{ENDPOINT_PATHS[kind]}"


async def call_upstream(
    upstream: HTTPUpstreamAdapter,
    kind: str,
    channel: RelayChannel,
    payload: Mapping[str, JsonValue] | bytes,
    content_type: str,
    request: RelayGatewayRequest,
) -> Result[UpstreamResponse, RelayGatewayError]:
    """Send the passthrough body to the selected channel's endpoint.

    JSON bodies go out as their decoded dict; raw bodies (multipart)
    travel through the adapter's payload slot as opaque bytes with their
    content type header intact, so the binary parts reach the provider
    untouched.

    Args:
        upstream: The HTTP transport adapter to send through.
        kind: The endpoint kind being served, selecting the wire path.
        channel: The selected channel.
        payload: The caller's body with the model substituted; a
            decoded JSON object or raw body bytes.
        content_type: The outbound content type header value.
        request: The original gateway request.

    Returns:
        ``Ok(UpstreamResponse)`` or ``Err`` as returned by the
        adapter; the adapter already normalizes transport failures.
    """
    url = endpoint_url(kind, channel)
    logger.info(
        "relay_passthrough_upstream_started",
        request_id=request.request_id,
        channel=channel.name,
        method="POST",
        url=url,
    )
    response = await upstream.request(
        UpstreamRequest(
            request_id=request.request_id,
            method="POST",
            url=url,
            headers={"content-type": content_type},
            payload=cast("Mapping[str, JsonValue]", payload),
            timeout_seconds=channel.timeout_seconds,
            channel_name=channel.name,
        )
    )
    if response.is_err():
        err = response.unwrap_err()
        logger.warning(
            "relay_passthrough_upstream_failed",
            request_id=request.request_id,
            channel=channel.name,
            code=err.code,
            status_code=err.status_code,
            error=str(err),
        )
    return response
