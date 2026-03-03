"""Relay conversion shared types — canonical IR, wire DTOs, protocol enums.

These types are the contract between the wire DTOs and the converter
engine in ``lexigram-ai-llm``.
"""

from __future__ import annotations

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
    RelayError,
    RelayRequest,
    RelayResponse,
    RelayUsage,
)
from lexigram.contracts.ai.relay.types import (
    PassthroughData,
    RelayConfig,
    RelayProtocol,
    StreamMode,
)

__all__ = [
    "ClaudeContent",
    "ClaudeMessage",
    "ClaudeRequest",
    "GeminiContent",
    "GeminiPart",
    "GeminiRequest",
    "OpenAIChatMessage",
    "OpenAIChatRequest",
    "PassthroughData",
    "RelayConfig",
    "RelayError",
    "RelayProtocol",
    "RelayRequest",
    "RelayResponse",
    "RelayUsage",
    "ResponsesItem",
    "ResponsesRequest",
    "ResponsesResponse",
    "StreamMode",
]
