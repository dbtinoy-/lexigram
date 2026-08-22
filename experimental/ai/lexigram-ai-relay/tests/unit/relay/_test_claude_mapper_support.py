"""Shared builders/stubs for test_claude_mapper tests."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeMessage,
    ClaudeRequest,
)
from lexigram.contracts.core.result import Ok

mapper = ClaudeMapper()


def claude_req(**kwargs: Any) -> ClaudeRequest:
    """Build a Claude request with sensible defaults."""
    defaults: dict[str, Any] = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 1024,
        "messages": [],
    }
    defaults.update(kwargs)
    return ClaudeRequest(**defaults)


def claude_msg(role: str, blocks: list[ClaudeContent]) -> ClaudeMessage:
    """Build a Claude message."""
    return ClaudeMessage(role=role, content=blocks)


@pytest.fixture
def ctx() -> ConversionContext:
    """A fresh conversion context per test."""
    return ConversionContext()


class FakeResolver:
    """Structural media resolver returning a fixed base64 payload."""

    def resolve(self, url: str) -> object:
        return Ok(("image/png", "AAAB"))
