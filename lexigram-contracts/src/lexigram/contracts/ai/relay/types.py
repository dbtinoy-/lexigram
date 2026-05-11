"""Shared relay types for the protocol conversion engine.

The relay layer normalises the four supported wire protocols (OpenAI
Chat Completions, Claude Messages, Gemini generateContent, OpenAI
Responses) into a single canonical representation.  These types are
protocol-agnostic and are shared by the converters in
``lexigram-ai-llm`` and the gateway layer (channels, billing) added in
later stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeAlias

PassthroughData: TypeAlias = dict[str, Any]
"""Opaque protocol-specific extras carried verbatim through conversion."""


class RelayProtocol(StrEnum):
    """The wire protocols supported by the relay conversion engine."""

    OPENAI_CHAT = "openai_chat"
    CLAUDE = "claude"
    GEMINI = "gemini"
    RESPONSES = "responses"


class StreamMode(StrEnum):
    """Streaming mode of a relayed request."""

    NON_STREAM = "non_stream"
    STREAM_SSE = "stream_sse"


@dataclass(frozen=True)
class RelayConfig:
    """Static, protocol-agnostic relay settings.

    Attributes:
        stream_mode: How the gateway streams responses to clients.
        passthrough: When ``True``, protocol-specific request fields are
            forwarded to the upstream provider even when the engine has
            no explicit mapping for them.
    """

    stream_mode: StreamMode = StreamMode.NON_STREAM
    passthrough: bool = False


__all__ = [
    "PassthroughData",
    "RelayConfig",
    "RelayProtocol",
    "StreamMode",
]
