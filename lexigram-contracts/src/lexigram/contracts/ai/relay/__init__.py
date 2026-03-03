"""Relay protocol conversion shared types.

This package holds the canonical intermediate representation (IR), wire
DTOs, conversion context, and service protocols shared by the converter
engine implemented in the ``lexigram-ai-relay`` extension package.
"""

from __future__ import annotations

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
    GeminiContent,
    GeminiPart,
    GeminiRequest,
    OpenAIChatMessage,
    OpenAIChatRequest,
    ResponsesItem,
    ResponsesRequest,
    ResponsesResponse,
)
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    StreamDelta,
    StreamState,
)
from lexigram.contracts.ai.relay.protocols import (
    RelayConverterProtocol,
    RelayMapperProtocol,
    RelayRegistryProtocol,
    RelayStreamOptions,
    RelayStreamSessionProtocol,
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

__all__ = [
    "ClaudeContent",
    "ClaudeMessage",
    "ClaudeOptions",
    "ClaudeRequest",
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
    "RelayConversionContext",
    "RelayConvertResult",
    "RelayConverterProtocol",
    "RelayFormat",
    "RelayLoss",
    "RelayMapperProtocol",
    "RelayOptions",
    "RelayRegistryProtocol",
    "RelayRequest",
    "RelayRequestPayload",
    "RelayResponse",
    "RelayResponsePayload",
    "RelayStreamOptions",
    "RelayStreamSessionProtocol",
    "RelayUsage",
    "ResponsesItem",
    "ResponsesRequest",
    "ResponsesResponse",
    "StreamDelta",
    "StreamState",
]
