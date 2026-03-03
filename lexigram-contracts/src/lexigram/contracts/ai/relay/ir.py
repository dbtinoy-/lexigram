"""Canonical relay request/response representation (IR).

Every converter maps a wire DTO onto :class:`RelayRequest` (inbound)
and from :class:`RelayResponse` (outbound).  The IR reuses the existing
contract chat types (``ChatMessage``, ``ToolCall``, ``ToolDefinition``,
``ThinkingResult``) so downstream consumers — channels, billing, usage
logging — see one stable shape regardless of the upstream provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, ToolCall
from lexigram.contracts.ai.thinking import ThinkingResult

__all__ = [
    "RelayError",
    "RelayRequest",
    "RelayResponse",
    "RelayUsage",
]


@dataclass(frozen=True)
class RelayUsage:
    """Normalised token usage reported by a relayed completion.

    ``total_tokens`` is reported by the upstream provider when available;
    otherwise it is left as ``0`` and computed downstream (e.g. by the
    billing layer) from the two components.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int | None = None
    """Prompt tokens served from the provider cache (prompt cache reads)."""
    reasoning_tokens: int | None = None
    """Tokens consumed by internal reasoning/thinking, when reported."""


@dataclass(frozen=True)
class RelayRequest:
    """Canonical request: what every converter receives and produces.

    Attributes:
        model: The upstream model id (as spoken by the destination
            protocol).
        messages: Conversation messages in canonical ``ChatMessage``
            form.  Content may be a string or a list of multimodal
            parts.
        tools: Tool schemas to offer to the model, ``None`` when the
            request offers no tools.
        parameters: Standard generation knobs (``temperature``,
            ``max_tokens``, ``top_p``, ``stop``, ...) shared across
            protocols.
        stream: Whether the response should be streamed.
        passthrough: Protocol-specific fields without a canonical
            mapping, carried verbatim for round-trips.
        metadata: Gateway bookkeeping (channel id, user id, request id).
    """

    model: str
    messages: list[ChatMessage]
    tools: list[ToolDefinition] | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    stream: bool = False
    passthrough: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelayResponse:
    """Canonical completion response produced by converters.

    Exactly one of ``content`` and ``tool_calls`` is typically populated;
    both may be present when a model emits text alongside tool calls.
    ``thinking`` carries provider reasoning output for providers that
    expose it (Anthropic extended thinking, Gemini thought blocks,
    OpenAI reasoning tokens).
    """

    model: str
    content: str | None = None
    thinking: ThinkingResult | None = None
    tool_calls: list[ToolCall] | None = None
    finish_reason: str | None = None
    usage: RelayUsage | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)
