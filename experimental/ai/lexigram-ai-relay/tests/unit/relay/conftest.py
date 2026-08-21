"""Shared fixtures for the OpenAI Responses mapper test suite.

The workspace shares a repo-root ``tests`` namespace (via the root
``pythonpath = ["."]``), so the ``tests`` module name can be bound to a
different package depending on collection order in workspace-wide runs.
The Gemini mapper suite therefore imports its helper module directly
(``gemini_mapper_test_helpers``) instead of through the ``tests.unit``
namespace: this conftest puts this directory at the front of
``sys.path`` so that direct import resolves deterministically in both
per-package runs and aggregate runs.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.relay.dto import (
    ResponsesItem,
    ResponsesRequest,
    ResponsesResponse,
    ResponsesUsage,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


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
