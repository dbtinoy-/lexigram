"""Constants and wire-part helpers shared by Gemini request conversion.

The canonical ``ToolCall`` to/from Gemini part helpers live here because
both conversion directions and the response module consume the same
wire-part shapes when rebuilding candidate content.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.llm import FunctionCall, ToolCall
from lexigram.contracts.ai.relay.dto import GeminiPart
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.serialization import loads_str

_TARGET = RelayFormat.GEMINI

_SAFETY_CATEGORIES = (
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
)

_MIME_KEY = "mimeType"

_THOUGHT_SIGNATURE_BYPASS = "context_engineering_is_the_way_to_go"

_SCHEMA_TYPE_MAP = {
    "string": "STRING",
    "object": "OBJECT",
    "array": "ARRAY",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
}


def _tool_call_from_part(part: GeminiPart) -> ToolCall:
    """Convert a Gemini ``functionCall`` part into a canonical ``ToolCall``.

    Gemini function calls carry no stable id; the canonical id stays
    empty so target writers can generate a dialect-appropriate one.
    """
    call = part.function_call or {}
    name = str(call.get("name", ""))
    args = call.get("args")
    return ToolCall(
        id="",
        type="custom",
        function=FunctionCall(
            name=name,
            arguments=args if isinstance(args, dict) else {},
        ),
    )


def _tool_call_to_part(tool_call: ToolCall) -> GeminiPart:
    """Serialize a canonical ``ToolCall`` as a Gemini ``functionCall`` part."""
    arguments: Any = tool_call.function.arguments if tool_call.function else {}
    if isinstance(arguments, str):
        try:
            arguments = loads_str(arguments)
        except ValueError:
            arguments = {}
    elif not isinstance(arguments, dict):
        arguments = {}
    return GeminiPart(
        function_call={
            "name": tool_call.function.name if tool_call.function else "",
            "args": arguments,
        }
    )
