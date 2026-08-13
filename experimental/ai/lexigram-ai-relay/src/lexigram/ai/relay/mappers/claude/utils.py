"""Shared parsing/serialization helpers for the Claude mapper."""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.mappers.base import new_uuid
from lexigram.contracts.ai.llm import FunctionCall, ToolCall
from lexigram.contracts.ai.relay.dto import ClaudeContent
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.serialization import loads_str

_TARGET = RelayFormat.CLAUDE


def _tool_call_from_block(block: ClaudeContent) -> ToolCall:
    """Convert a Claude ``tool_use`` block into a canonical ``ToolCall``."""
    return ToolCall(
        id=block.tool_use_id or "",
        type="custom",
        function=FunctionCall(name=block.name or "", arguments=block.input or {}),
    )


def _tool_call_to_block(tool_call: ToolCall) -> ClaudeContent:
    """Serialize a canonical ``ToolCall`` as a Claude ``tool_use`` block."""
    arguments: Any = tool_call.function.arguments if tool_call.function else {}
    if isinstance(arguments, str):
        try:
            arguments = loads_str(arguments)
        except ValueError:
            arguments = {}
    elif not isinstance(arguments, dict):
        arguments = {}
    return ClaudeContent(
        type="tool_use",
        tool_use_id=tool_call.id or f"call_{new_uuid()}",
        name=tool_call.function.name if tool_call.function else "",
        input=arguments,
    )
