"""Shared fixtures for the OpenAI Responses mapper test suite."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.relay.dto import (
    ResponsesItem,
    ResponsesRequest,
    ResponsesResponse,
    ResponsesUsage,
)


@pytest.fixture
def mapper() -> Any:
    """A fresh Responses mapper per test."""
    from lexigram.ai.relay.mappers.openai_responses import OpenAIResponsesMapper

    return OpenAIResponsesMapper()


@pytest.fixture
def ctx() -> ConversionContext:
    """A fresh conversion context per test."""
    return ConversionContext()


@pytest.fixture
def resp_req() -> Any:
    """Build a Responses request with sensible defaults."""

    def build(**kwargs: Any) -> ResponsesRequest:
        defaults: dict[str, Any] = {"model": "gpt-5.2", "input": []}
        defaults.update(kwargs)
        return ResponsesRequest(**defaults)

    return build


@pytest.fixture
def item() -> Any:
    """Build a Responses input item with sensible defaults."""

    def build(**kwargs: Any) -> ResponsesItem:
        defaults: dict[str, Any] = {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hi"}],
        }
        defaults.update(kwargs)
        return ResponsesItem(**defaults)

    return build


@pytest.fixture
def resp() -> Any:
    """Build a Responses response with sensible defaults."""

    def build(**kwargs: Any) -> ResponsesResponse:
        defaults: dict[str, Any] = {"id": "resp_1", "model": "gpt-5.2", "output": []}
        defaults.update(kwargs)
        return ResponsesResponse(**defaults)

    return build


@pytest.fixture
def usage() -> Any:
    """Build Responses usage with sensible defaults."""

    def build(**kwargs: Any) -> ResponsesUsage:
        defaults: dict[str, Any] = {"input_tokens": 10, "output_tokens": 5}
        defaults.update(kwargs)
        return ResponsesUsage(**defaults)

    return build
