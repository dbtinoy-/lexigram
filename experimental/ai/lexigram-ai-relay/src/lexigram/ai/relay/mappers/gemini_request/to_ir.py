"""Gemini wire request → canonical relay IR conversion."""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate, unsupported_format
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.ai.relay.mappers.gemini_request._shared import (
    _MIME_KEY,
    _TARGET,
    _tool_call_from_part,
)
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, ToolCall
from lexigram.contracts.ai.multimodal import (
    ContentPart,
    ImageBase64Part,
    TextPart,
)
from lexigram.contracts.ai.relay.dto import GeminiContent, GeminiRequest
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.ai.thinking import ThinkingConfig
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import dumps_str


def request_to_ir(
    payload: Any, *, context: ConversionContext
) -> Result[RelayRequest, RelayError]:
    """Convert a ``GeminiRequest`` into canonical ``RelayRequest``.

    Args:
        payload: A wire request DTO.
        context: Per-conversion context with loss sink.

    Returns:
        Ok(request) on success, Err(relay_error) on malformed payload.
    """
    if not isinstance(payload, GeminiRequest):
        return Err(
            unsupported_format(f"expected GeminiRequest, got {type(payload).__name__}")
        )
    try:
        messages = [
            chat_message
            for index, content in enumerate(payload.contents)
            for chat_message in _content_to_ir(content, context, index)
        ]
        metadata: dict[str, Any] = {}
        if payload.safety_settings is not None:
            metadata["safety_settings"] = [
                dict(item) for item in payload.safety_settings
            ]
        if payload.tool_config is not None:
            metadata["tool_config"] = dict(payload.tool_config)
        generation_config = dict(payload.generation_config)
        if generation_config:
            metadata["generation_config"] = generation_config
        return Ok(
            RelayRequest(
                model=str(payload.passthrough.get("model", "")).strip(),
                messages=messages,
                system=_system_to_ir(payload.system_instruction),
                tools=_tools_to_ir(payload.tools),
                temperature=_config_number(generation_config, "temperature"),
                top_p=_config_number(generation_config, "topP"),
                top_k=_config_int(generation_config, "topK"),
                max_tokens=_config_int(generation_config, "maxOutputTokens"),
                stop_sequences=[
                    str(item)
                    for item in generation_config.get("stopSequences", [])
                    if isinstance(item, str)
                ],
                response_format=_response_format_to_ir(generation_config),
                thinking=_thinking_to_ir(generation_config),
                metadata=metadata,
                passthrough=dict(payload.passthrough),
            )
        )
    except (RelayError, ValueError, TypeError, KeyError) as exc:
        return Err(translate(exc, detail="request_to_ir"))


def _system_to_ir(
    system_instruction: dict[str, Any] | None,
) -> str | None:
    """Extract system text from a Gemini ``systemInstruction`` dict."""
    if not isinstance(system_instruction, dict):
        return None
    parts = system_instruction.get("parts")
    if not isinstance(parts, list):
        return None
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("text") is not None:
            texts.append(str(part["text"]))
    return "\n".join(texts)


def _tools_to_ir(tools: list[dict[str, Any]] | None) -> list[ToolDefinition]:
    """Convert Gemini wire tools into canonical ``ToolDefinition`` objects."""
    definitions: list[ToolDefinition] = []
    for tool in tools or []:
        if not isinstance(tool, dict):
            continue
        declarations = tool.get("functionDeclarations")
        if not isinstance(declarations, list):
            continue
        for declaration in declarations:
            if not isinstance(declaration, dict):
                continue
            parameters = declaration.get("parameters")
            definitions.append(
                ToolDefinition(
                    name=str(declaration.get("name", "")),
                    description=str(declaration.get("description", "")),
                    parameters=parameters if isinstance(parameters, dict) else {},
                )
            )
    return definitions


def _content_to_ir(
    content: GeminiContent, context: ConversionContext, index: int
) -> list[ChatMessage]:
    """Convert one Gemini content turn into canonical messages."""
    if content.role == "model":
        return [_assistant_to_ir(content, context)]
    if content.role == "user":
        return _user_to_ir(content, context, index)
    if content.role == "function":
        return _function_to_ir(content, context, index)
    record_loss(
        context,
        field=f"contents[{index}].role",
        target=_TARGET,
        reason="unknown_role_dropped",
    )
    return []


def _assistant_to_ir(content: GeminiContent, context: ConversionContext) -> ChatMessage:
    """Convert a model content turn, separating thinking/tool parts."""
    text_parts: list[str] = []
    thinking_blocks: list[dict[str, Any]] = []
    tool_calls: list[ToolCall] = []
    for part in content.parts:
        if part.thought:
            thinking_blocks.append(
                {
                    "thought": True,
                    "text": part.text or "",
                    "thoughtSignature": part.thought_signature or "",
                }
            )
        elif part.text is not None:
            text_parts.append(part.text)
        elif part.function_call is not None:
            tool_calls.append(_tool_call_from_part(part))
        else:
            record_loss(
                context,
                field="content.part",
                target=_TARGET,
                reason="unrepresentable_part_dropped",
            )
    return ChatMessage(
        role="assistant",
        content="".join(text_parts),
        tool_calls=tool_calls or None,
        thinking_blocks=thinking_blocks or None,
    )


def _user_to_ir(
    content: GeminiContent, context: ConversionContext, index: int
) -> list[ChatMessage]:
    """Convert a user content turn into canonical parts and tool results."""
    parts: list[ContentPart] = []
    tool_results: list[ChatMessage] = []
    for part in content.parts:
        if part.text is not None:
            parts.append(TextPart(text=part.text))
        elif part.inline_data is not None:
            inline = part.inline_data
            parts.append(
                ImageBase64Part(
                    data=str(inline.get("data", "")),
                    media_type=str(inline.get(_MIME_KEY, "")),
                    detail="auto",
                )
            )
        elif part.function_response is not None:
            tool_results.append(_function_response_to_ir(part.function_response))
        else:
            record_loss(
                context,
                field=f"contents[{index}].part",
                target=_TARGET,
                reason="unrepresentable_part_dropped",
            )
    turns: list[ChatMessage] = []
    if parts:
        turns.append(
            ChatMessage(
                role="user",
                content=(
                    parts[0].text
                    if len(parts) == 1 and isinstance(parts[0], TextPart)
                    else list(parts)
                ),
            )
        )
    turns.extend(tool_results)
    if not turns:
        record_loss(
            context,
            field=f"contents[{index}]",
            target=_TARGET,
            reason="empty_message_dropped",
        )
    return turns


def _function_to_ir(
    content: GeminiContent, context: ConversionContext, index: int
) -> list[ChatMessage]:
    """Convert a function content turn into canonical tool messages."""
    messages: list[ChatMessage] = []
    for part in content.parts:
        if part.function_response is not None:
            messages.append(_function_response_to_ir(part.function_response))
        else:
            record_loss(
                context,
                field=f"contents[{index}].part",
                target=_TARGET,
                reason="unrepresentable_part_dropped",
            )
    return messages


def _function_response_to_ir(response: dict[str, Any]) -> ChatMessage:
    """Convert a ``functionResponse`` dict into a canonical tool message."""
    payload = response.get("response")
    if isinstance(payload, str):
        text = payload
    else:
        text = dumps_str(payload) if payload is not None else ""
    return ChatMessage(role="tool", content=text, tool_call_id="")


def _response_format_to_ir(
    generation_config: dict[str, Any],
) -> dict[str, Any] | None:
    """Derive a canonical response format from the generation config."""
    mime = generation_config.get("responseMimeType")
    if not isinstance(mime, str):
        return None
    if mime == "application/json":
        return {"type": "json_object"}
    return None


def _thinking_to_ir(generation_config: dict[str, Any]) -> ThinkingConfig | None:
    """Extract canonical thinking config from ``thinkingConfig``."""
    config = generation_config.get("thinkingConfig")
    if not isinstance(config, dict):
        return None
    level = config.get("thinkingLevel")
    budget = config.get("thinkingBudget")
    if isinstance(level, str) and level:
        return ThinkingConfig(level=level)
    if isinstance(budget, int):
        return ThinkingConfig(budget_tokens=budget)
    return None


def _config_number(generation_config: dict[str, Any], key: str) -> int | float | None:
    """Read a numeric generation config value when well-typed."""
    value = generation_config.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _config_int(generation_config: dict[str, Any], key: str) -> int | None:
    """Read an integer generation config value when well-typed."""
    value = _config_number(generation_config, key)
    if value is None or isinstance(value, float):
        return None
    return value
