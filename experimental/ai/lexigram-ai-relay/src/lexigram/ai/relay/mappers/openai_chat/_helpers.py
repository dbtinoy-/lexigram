"""Constants and free helpers shared across OpenAI Chat conversion."""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.contracts.ai.llm import FunctionCall, ToolCall
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.serialization import dumps_str

_TARGET = RelayFormat.OPENAI_CHAT
_MESSAGE_METADATA_INTERNAL = {"function_call_item_ids"}


def _tool_calls_to_ir(
    wire: list[dict[str, Any]] | None,
) -> list[ToolCall] | None:
    """Convert wire tool-call dicts into canonical ``ToolCall`` objects."""
    if not wire:
        return None
    tool_calls: list[ToolCall] = []
    for item in wire:
        function = item.get("function")
        name = function.get("name", "") if isinstance(function, dict) else ""
        arguments = function.get("arguments", {}) if isinstance(function, dict) else {}
        tool_calls.append(
            ToolCall(
                id=str(item.get("id", "")),
                type=str(item.get("type", "function")),
                function=FunctionCall(name=str(name), arguments=arguments),
            )
        )
    return tool_calls


def _tool_call_to_wire(tool_call: ToolCall) -> dict[str, Any]:
    """Serialize one canonical ``ToolCall`` as a wire dict."""
    arguments: Any = tool_call.function.arguments if tool_call.function else {}
    if isinstance(arguments, dict):
        arguments = dumps_str(arguments)
    elif not isinstance(arguments, str):
        arguments = ""
    return {
        "id": tool_call.id,
        "type": "function",
        "function": {
            "name": tool_call.function.name if tool_call.function else "",
            "arguments": arguments,
        },
    }


def _extract_text(
    content: str | list[dict[str, Any]] | None,
    context: ConversionContext,
    *,
    field: str,
) -> str:
    """Extract the text portion of wire content for flattened fields."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    texts: list[str] = []
    lost = False
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            texts.append(str(part.get("text", "")))
        else:
            lost = True
    if lost:
        record_loss(
            context, field=field, target=_TARGET, reason="non_text_parts_dropped"
        )
    return "".join(texts)
