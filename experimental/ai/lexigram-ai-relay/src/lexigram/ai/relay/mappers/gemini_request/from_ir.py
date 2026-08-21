"""Canonical relay IR → Gemini wire request conversion."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.ai.relay.mappers.gemini_request._shared import (
    _MIME_KEY,
    _SAFETY_CATEGORIES,
    _SCHEMA_TYPE_MAP,
    _TARGET,
    _THOUGHT_SIGNATURE_BYPASS,
    _tool_call_to_part,
)
from lexigram.ai.relay.media import resolve_media
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage
from lexigram.contracts.ai.multimodal import (
    ContentPart,
    ImageBase64Part,
    ImageUrlPart,
    TextPart,
)
from lexigram.contracts.ai.relay.dto import GeminiContent, GeminiPart, GeminiRequest
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import loads_str


def ir_to_request(
    request: RelayRequest, *, context: ConversionContext
) -> Result[Any, RelayError]:
    """Convert canonical ``RelayRequest`` into a ``GeminiRequest``.

    Args:
        request: Canonical request IR.
        context: Per-conversion context with loss sink.

    Returns:
        Ok(request) on success, Err(relay_error) on failure.
    """
    try:
        system_parts: list[str] = []
        contents: list[GeminiContent] = []
        tool_names, tool_names_by_id = _tool_name_resolver(request)
        for message in request.messages:
            if message.role == "system":
                system_parts.append(_text_from_content(message.content))
                continue
            content = _content_from_ir(
                message, request.model, tool_names, tool_names_by_id, context
            )
            if content.is_err():
                return content
            contents.append(content.unwrap())
        if request.system:
            system_parts.append(request.system)
        return Ok(
            GeminiRequest(
                contents=contents,
                system_instruction=(
                    {"parts": [{"text": text} for text in system_parts]}
                    if system_parts
                    else None
                ),
                generation_config=_generation_config_from_ir(request, context),
                safety_settings=_safety_settings_from_ir(request, context),
                tools=_tools_from_ir(request.tools),
                tool_config=_tool_config_from_ir(request),
                passthrough=_request_passthrough(request),
            )
        )
    except (RelayError, ValueError, TypeError, KeyError) as exc:
        return Err(translate(exc, detail="ir_to_request"))


def _content_from_ir(
    message: ChatMessage,
    model: str,
    tool_names: list[str],
    tool_names_by_id: dict[str, str],
    context: ConversionContext,
) -> Result[GeminiContent, RelayError]:
    """Convert one canonical message into a Gemini content turn.

    Args:
        message: Canonical message to serialize.
        model: The selected model, for capability lookups.
        tool_names: Positional resolver for tool-message function
            names when the canonical ``tool_call_id`` carries no
            stable link.
        tool_names_by_id: Resolver keyed by canonical tool-call id.
        context: Per-conversion context with loss sink.

    Returns:
        Ok(content) on success, Err(relay_error) on failure.
    """
    if message.role == "tool":
        response: Any = message.content
        if isinstance(response, list):
            response = _text_from_content(message.content)
        if isinstance(response, str):
            try:
                response = loads_str(response)
            except ValueError:
                pass
        name = tool_names_by_id.get(message.tool_call_id or "", "")
        if not name and tool_names:
            name = tool_names.pop(0)
        if isinstance(response, str):
            response = {"content": response}
        return Ok(
            GeminiContent(
                role="user",
                parts=[
                    GeminiPart(
                        function_response={
                            "name": name,
                            "response": response,
                        }
                    )
                ],
            )
        )
    if message.role == "assistant":
        parts = _assistant_parts_from_ir(message, model, context)
        if parts.is_err():
            return Err(parts.unwrap_err())
        return Ok(GeminiContent(role="model", parts=parts.unwrap()))
    if message.role == "user":
        parts = _user_parts_from_ir(message.content, context)
        if parts.is_err():
            return Err(parts.unwrap_err())
        return Ok(GeminiContent(role="user", parts=parts.unwrap()))
    record_loss(
        context,
        field="messages",
        target=_TARGET,
        reason=f"unknown_role_{message.role}_dropped",
    )
    return Ok(GeminiContent(role="user", parts=[GeminiPart(text="")]))


def _tool_name_resolver(
    request: RelayRequest,
) -> tuple[list[str], dict[str, str]]:
    """Return tool-message name resolvers for a request.

    Gemini ``functionResponse`` blocks name the function, not the
    call id.  Tool messages resolve their function name by canonical
    ``tool_call_id`` first; unresolved messages fall back to
    positional order against the assistant tool calls that preceded
    them.
    """
    names: list[str] = []
    names_by_id: dict[str, str] = {}
    for message in request.messages:
        if message.role == "assistant":
            for tool_call in message.tool_calls or []:
                if tool_call.function:
                    names.append(tool_call.function.name)
                    if tool_call.id:
                        names_by_id[tool_call.id] = tool_call.function.name
    return names, names_by_id


def _assistant_parts_from_ir(
    message: ChatMessage, model: str, context: ConversionContext
) -> Result[list[GeminiPart], RelayError]:
    """Rebuild Gemini model parts from an assistant message.

    When the thought-signature bypass policy is enabled the thinking
    blocks are folded away and a bypass ``thoughtSignature`` is
    attached to the first function-call part (relaykit's
    ``FunctionCallThoughtSignatureEnabled`` behavior).  Otherwise
    thinking blocks are re-emitted as native Gemini thought parts.
    """
    attach_signature = context.options.gemini.thought_signature_bypass
    parts: list[GeminiPart] = []
    if not attach_signature:
        for block in message.thinking_blocks or []:
            if not isinstance(block, dict):
                continue
            signature = block.get("thoughtSignature")
            parts.append(
                GeminiPart(
                    text=str(block.get("text", "")),
                    thought=True,
                    thought_signature=str(signature) if signature else None,
                )
            )
    content_parts = _user_parts_from_ir(message.content, context)
    if content_parts.is_err():
        return Err(content_parts.unwrap_err())
    parts.extend(content_parts.unwrap())
    for tool_call in message.tool_calls or []:
        parts.append(_tool_call_to_part(tool_call))
    if attach_signature:
        parts = _attach_thought_signature(parts)
    return Ok(parts)


def _attach_thought_signature(parts: list[GeminiPart]) -> list[GeminiPart]:
    """Attach the relaykit thought-signature bypass value to model parts.

    The signature lands on the first function-call part, or on the
    first non-empty text part when the message carries no tool calls.
    """
    rebuilt: list[GeminiPart] = []
    attached = False
    for part in parts:
        current = part
        if not attached and part.function_call is not None:
            current = replace(part, thought_signature=_THOUGHT_SIGNATURE_BYPASS)
            attached = True
        rebuilt.append(current)
    if not attached:
        for index, part in enumerate(rebuilt):
            if part.text:
                rebuilt[index] = replace(
                    part, thought_signature=_THOUGHT_SIGNATURE_BYPASS
                )
                break
    return rebuilt


def _user_parts_from_ir(
    content: str | list[ContentPart], context: ConversionContext
) -> Result[list[GeminiPart], RelayError]:
    """Convert canonical content into Gemini parts."""
    if isinstance(content, str):
        return Ok([GeminiPart(text=content)] if content else [])
    parts: list[GeminiPart] = []
    for part in content:
        if isinstance(part, TextPart):
            parts.append(GeminiPart(text=part.text))
        elif isinstance(part, ImageBase64Part):
            parts.append(
                GeminiPart(
                    inline_data={
                        _MIME_KEY: part.media_type,
                        "data": part.data,
                    }
                )
            )
        elif isinstance(part, ImageUrlPart):
            resolved = _resolve_image(part, context)
            if resolved.is_err():
                return Err(resolved.unwrap_err())
            media_type, data = resolved.unwrap()
            parts.append(GeminiPart(inline_data={_MIME_KEY: media_type, "data": data}))
        else:
            record_loss(
                context,
                field="message.content",
                target=_TARGET,
                reason="unknown_content_part",
            )
    return Ok(parts)


def _resolve_image(
    part: ImageUrlPart, context: ConversionContext
) -> Result[tuple[str, str], RelayError]:
    """Resolve a URL or data-URI image for Gemini.

    Data URIs decode locally; URLs go through the context resolver.
    """
    resolved = resolve_media(
        part.url,
        context,
        field="message.content",
        target=_TARGET,
        lossy=False,
    )
    if resolved.is_err():
        return Err(resolved.unwrap_err())
    image = resolved.unwrap()
    assert image is not None  # lossy=False never drops media  # noqa: S101
    return Ok(image)


def _text_from_content(content: str | list[ContentPart]) -> str:
    """Extract plain text from canonical content."""
    if isinstance(content, str):
        return content
    return "".join(part.text for part in content if isinstance(part, TextPart))


def _generation_config_from_ir(
    request: RelayRequest, context: ConversionContext
) -> dict[str, Any]:
    """Rebuild ``generationConfig`` from protocol metadata and canonical fields."""
    raw = request.metadata.get("generation_config")
    config: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
    for key in (
        "temperature",
        "topP",
        "topK",
        "maxOutputTokens",
        "stopSequences",
        "responseMimeType",
        "responseSchema",
        "thinkingConfig",
    ):
        config.pop(key, None)
    if request.temperature is not None:
        config["temperature"] = request.temperature
    if request.top_p is not None:
        config["topP"] = request.top_p
    if request.top_k is not None:
        config["topK"] = request.top_k
    if request.max_tokens is not None:
        config["maxOutputTokens"] = request.max_tokens
    if request.stop_sequences:
        config["stopSequences"] = list(request.stop_sequences)
    if request.response_format is not None:
        if request.response_format.get("type") == "json_object":
            config["responseMimeType"] = "application/json"
        if isinstance(request.response_format.get("schema"), dict):
            config["responseSchema"] = request.response_format["schema"]
    thinking_config = _thinking_config_from_ir(request, context)
    if thinking_config is not None:
        config["thinkingConfig"] = thinking_config
    if "responseModalities" not in config and context.supports_image_generation(
        request.model
    ):
        config["responseModalities"] = ["TEXT", "IMAGE"]
    return config


def _thinking_config_from_ir(
    request: RelayRequest, context: ConversionContext
) -> dict[str, Any] | None:
    """Build a Gemini ``thinkingConfig`` from canonical thinking."""
    if request.thinking is not None:
        record_loss(
            context,
            field="thinking",
            target=_TARGET,
            reason="thinking_not_supported",
        )
    if (
        context.options.gemini.thinking_adapter_enabled
        and context.options.gemini.thinking_budget
    ):
        return {"thinkingBudget": context.options.gemini.thinking_budget}
    return None


def _safety_settings_from_ir(
    request: RelayRequest, context: ConversionContext
) -> list[dict[str, Any]] | None:
    """Rebuild Gemini safety settings from metadata or the callback."""
    raw = request.metadata.get("safety_settings")
    if isinstance(raw, list):
        preserved = [dict(item) for item in raw if isinstance(item, dict)]
        return preserved or None
    collected: list[dict[str, Any]] = []
    for category in _SAFETY_CATEGORIES:
        threshold = context.safety_setting(category)
        if threshold and isinstance(threshold, str):
            collected.append({"category": category, "threshold": threshold})
    return collected or None


def _tools_from_ir(tools: list[ToolDefinition]) -> list[dict[str, Any]] | None:
    """Serialize canonical tools as Gemini function declarations."""
    if not tools:
        return None
    return [
        {
            "functionDeclarations": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": _upper_schema_types(tool.parameters),
                }
                for tool in tools
            ]
        }
    ]


def _request_passthrough(request: RelayRequest) -> dict[str, Any]:
    """Carry canonical passthrough state into the request wire payload."""
    return dict(request.passthrough)


def _upper_schema_types(parameters: dict[str, Any]) -> dict[str, Any]:
    """Uppercase Gemini schema type markers recursively.

    Gemini function declarations require ``STRING``/``OBJECT`` type
    values; canonical schemas carry the lowercase JSON-Schema form.
    """
    out: dict[str, Any] = {}
    for key, value in parameters.items():
        if key == "type" and isinstance(value, str):
            out[key] = _SCHEMA_TYPE_MAP.get(value, value)
        elif isinstance(value, dict):
            out[key] = _upper_schema_types(value)
        elif isinstance(value, list):
            out[key] = [
                _upper_schema_types(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            out[key] = value
    return out


def _tool_config_from_ir(request: RelayRequest) -> dict[str, Any] | None:
    """Rebuild a Gemini ``toolConfig`` from canonical tool choice."""
    raw = request.metadata.get("tool_config")
    if isinstance(raw, dict):
        return dict(raw)
    choice = request.tool_choice
    if isinstance(choice, dict):
        name = choice.get("function", {})
        if isinstance(name, dict):
            name = name.get("name")
        if isinstance(name, str) and name:
            return {
                "functionCallingConfig": {
                    "mode": "ANY",
                    "allowedFunctionNames": [name],
                }
            }
        return {"functionCallingConfig": {"mode": "ANY"}}
    if isinstance(choice, str):
        mode = {"auto": "AUTO", "none": "NONE", "required": "ANY"}.get(choice, "AUTO")
        return {"functionCallingConfig": {"mode": mode}}
    return None
