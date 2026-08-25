"""Shared builders for the relay registry/engine test suite."""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay import RelayConverterRegistry
from lexigram.contracts.ai.relay.dto import (
    OpenAIChatChoice,
    OpenAIChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
    ResponsesRequest,
)
from lexigram.contracts.ai.relay.types import RelayFormat

registry = RelayConverterRegistry.with_defaults()

ALL_PAIRS: list[tuple[RelayFormat, RelayFormat]] = [
    (source, target)
    for source in RelayFormat
    for target in RelayFormat
    if source is not target
]


def chat_request(**kwargs: Any) -> OpenAIChatRequest:
    """Build a Chat request with sensible defaults."""
    defaults: dict[str, Any] = {
        "model": "gpt-4o",
        "messages": [
            OpenAIChatMessage(role="user", content="Hello"),
        ],
    }
    defaults.update(kwargs)
    return OpenAIChatRequest(**defaults)


def chat_response(**kwargs: Any) -> OpenAIChatResponse:
    """Build a Chat response with sensible defaults."""
    defaults: dict[str, Any] = {
        "id": "chat_1",
        "model": "gpt-4o",
        "object": "chat.completion",
        "created": 1700000000,
        "choices": [
            OpenAIChatChoice(
                index=0,
                message=OpenAIChatMessage(role="assistant", content="Hello"),
                finish_reason="stop",
            )
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    defaults.update(kwargs)
    return OpenAIChatResponse(**defaults)


def responses_request(**kwargs: Any) -> ResponsesRequest:
    """Build a Responses request with sensible defaults."""
    defaults: dict[str, Any] = {"model": "gpt-4o", "input": []}
    defaults.update(kwargs)
    return ResponsesRequest(**defaults)
