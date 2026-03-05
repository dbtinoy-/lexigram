"""Protocol-facing relay gateway: channel selection, orchestration, upstream I/O, and SSE handling.

The gateway composes the :class:`RelayGatewayService` from a channel
registry, payload codec, upstream HTTP adapter, and the conversion engine,
and exposes it behind :class:`~lexigram.contracts.ai.relay.RelayGatewayProtocol`
through :class:`RelayGatewayModule` / :class:`RelayGatewayProvider`.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.credentials import (
    CredentialInjectingHTTPClient,
    NullChannelCredentialProvider,
    RelayChannelCredentialProvider,
)
from lexigram.ai.relay.gateway.di.provider import RelayGatewayProvider
from lexigram.ai.relay.gateway.module import RelayGatewayModule
from lexigram.ai.relay.gateway.operations import (
    InMemoryRelayPolicyStore,
    RelayChannelAutoTester,
    RelayChannelCheckerProtocol,
    RelayChannelProbeResult,
    RelayControlsService,
    RelayHealthService,
    RelayMetricsService,
    RelayRouteEvent,
    RelayRouteEventSourceProtocol,
    RelayStreamRegistry,
)
from lexigram.ai.relay.gateway.passthrough import PassthroughService
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.ai.relay.gateway.stream import UpstreamEventParser, relay_stream
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter

__all__ = [
    "CredentialInjectingHTTPClient",
    "HTTPUpstreamAdapter",
    "InMemoryRelayPolicyStore",
    "NullChannelCredentialProvider",
    "PassthroughService",
    "RelayChannelAutoTester",
    "RelayChannelCheckerProtocol",
    "RelayChannelCredentialProvider",
    "RelayChannelProbeResult",
    "RelayChannelRegistry",
    "RelayControlsService",
    "RelayGatewayConfig",
    "RelayGatewayModule",
    "RelayGatewayProvider",
    "RelayGatewayService",
    "RelayHealthService",
    "RelayMetricsService",
    "RelayPayloadCodec",
    "RelayRouteEvent",
    "RelayRouteEventSourceProtocol",
    "RelayStreamRegistry",
    "UpstreamEventParser",
    "relay_stream",
]
