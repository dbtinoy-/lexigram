"""Relay protocol conversion shared types.

This package holds the canonical intermediate representation (IR), wire
DTOs, conversion context, and service protocols shared by the converter
engine implemented in the ``lexigram-ai-relay`` extension package.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay.auth import (
    RelayAuthError,
    RelayAuthIdentity,
    RelayAuthVerifierProtocol,
)
from lexigram.contracts.ai.relay.context import (
    ClaudeOptions,
    GeminiOptions,
    MediaResolverProtocol,
    RelayConversionContext,
    RelayOptions,
)
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeMessage,
    ClaudeRequest,
    ClaudeResponse,
    GeminiContent,
    GeminiPart,
    GeminiRequest,
    OpenAIChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
    ResponsesItem,
    ResponsesRequest,
    ResponsesResponse,
)
from lexigram.contracts.ai.relay.gateway import (
    RelayChannel,
    RelayGatewayError,
    RelayGatewayMetadata,
    RelayGatewayProtocol,
    RelayGatewayRequest,
    RelayGatewayResult,
)
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    StreamDelta,
    StreamState,
)
from lexigram.contracts.ai.relay.logs import (
    RelayRequestLogEntry,
    RelayRequestLogStoreProtocol,
)
from lexigram.contracts.ai.relay.operations import (
    RelayActiveStream,
    RelayChannelHealth,
    RelayOperationsControlProtocol,
    RelayOperationsProtocol,
    RelayPolicyChange,
    RelayPolicySnapshot,
    RelayPolicyStoreProtocol,
    RelayRegistryDiagnostics,
    RelayRouteMetrics,
    TimeWindow,
)
from lexigram.contracts.ai.relay.protocols import (
    RelayConverterProtocol,
    RelayMapperProtocol,
    RelayRegistryProtocol,
    RelayStreamOptions,
    RelayStreamSessionProtocol,
)
from lexigram.contracts.ai.relay.ratelimit import (
    RelayRateLimitCounterProtocol,
    RelayRateLimitDecision,
)
from lexigram.contracts.ai.relay.store import (
    RelayChannelSnapshot,
    RelayChannelStoreProtocol,
)
from lexigram.contracts.ai.relay.transport import (
    RelayUpstreamProtocol,
    RelayWireEvent,
    UpstreamChunk,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.ai.relay.types import (
    ConversionQuality,
    JsonObject,
    JsonValue,
    RelayConvertResult,
    RelayFormat,
    RelayLoss,
    RelayRequestPayload,
    RelayResponsePayload,
    RelayUsage,
)
from lexigram.contracts.ai.relay.usage import (
    RelayDailyUsage,
    RelayModelRank,
    RelayUsageServiceProtocol,
)

__all__ = [
    "ClaudeContent",
    "ClaudeMessage",
    "ClaudeOptions",
    "ClaudeRequest",
    "ClaudeResponse",
    "ConversionQuality",
    "GeminiContent",
    "GeminiOptions",
    "GeminiPart",
    "GeminiRequest",
    "JsonObject",
    "JsonValue",
    "MediaResolverProtocol",
    "OpenAIChatMessage",
    "OpenAIChatRequest",
    "OpenAIChatResponse",
    "RelayActiveStream",
    "RelayAuthError",
    "RelayAuthIdentity",
    "RelayAuthVerifierProtocol",
    "RelayChannel",
    "RelayChannelHealth",
    "RelayChannelSnapshot",
    "RelayChannelStoreProtocol",
    "RelayConversionContext",
    "RelayConvertResult",
    "RelayConverterProtocol",
    "RelayDailyUsage",
    "RelayFormat",
    "RelayGatewayError",
    "RelayGatewayMetadata",
    "RelayGatewayProtocol",
    "RelayGatewayRequest",
    "RelayGatewayResult",
    "RelayLoss",
    "RelayMapperProtocol",
    "RelayModelRank",
    "RelayOperationsControlProtocol",
    "RelayOperationsProtocol",
    "RelayOptions",
    "RelayPolicyChange",
    "RelayPolicySnapshot",
    "RelayPolicyStoreProtocol",
    "RelayRateLimitCounterProtocol",
    "RelayRateLimitDecision",
    "RelayRegistryDiagnostics",
    "RelayRegistryProtocol",
    "RelayRequest",
    "RelayRequestLogEntry",
    "RelayRequestLogStoreProtocol",
    "RelayRequestPayload",
    "RelayResponse",
    "RelayResponsePayload",
    "RelayRouteMetrics",
    "RelayStreamOptions",
    "RelayStreamSessionProtocol",
    "RelayUpstreamProtocol",
    "RelayUsage",
    "RelayUsageServiceProtocol",
    "RelayWireEvent",
    "ResponsesItem",
    "ResponsesRequest",
    "ResponsesResponse",
    "StreamDelta",
    "StreamState",
    "TimeWindow",
    "UpstreamChunk",
    "UpstreamRequest",
    "UpstreamResponse",
]
