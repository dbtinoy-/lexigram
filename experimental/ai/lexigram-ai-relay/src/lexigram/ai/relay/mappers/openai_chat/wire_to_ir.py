"""Wire → IR parsing helpers for the OpenAI Chat mapper."""

from __future__ import annotations

from typing import Any, cast

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.ai.relay.mappers.openai_chat._helpers import (
    _TARGET,
    _extract_text,
)
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.multimodal import ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import OpenAIChatMessage, OpenAIChatRequest
from lexigram.contracts.ai.relay.types import RelayUsage
from lexigram.contracts.ai.thinking import ThinkingResult


class WireToIRMixin:
    """Static parsers turning OpenAI Chat wire shapes into canonical IR."""

    @staticmethod
    def _tools_to_ir(
        tools: list[dict[str, Any]] | None, context: ConversionContext
    ) -> list[ToolDefinition]:
        """Convert wire tool dicts into canonical ``ToolDefinition`` objects."""
        definitions: list[ToolDefinition] = []
        if not tools:
            return definitions
        for index, tool in enumerate(tools):
            if not isinstance(tool, dict):
                record_loss(
                    context,
                    field=f"tools[{index}]",
                    target=_TARGET,
                    reason="non_dict_tool_dropped",
                )
                continue
            if tool.get("type", "function") != "function":
                record_loss(
                    context,
                    field=f"tools[{index}]",
                    target=_TARGET,
                    reason="non_function_tool_dropped",
                )
                continue
            function = tool.get("function")
            if not isinstance(function, dict):
                record_loss(
                    context,
                    field=f"tools[{index}]",
                    target=_TARGET,
                    reason="missing_function",
                )
                continue
            parameters = function.get("parameters", {})
            definitions.append(
                ToolDefinition(
                    name=str(function.get("name", "")),
                    description=str(function.get("description", "")),
                    parameters=parameters if isinstance(parameters, dict) else {},
                )
            )
        return definitions

    @staticmethod
    def _normalize_max_tokens(
        payload: OpenAIChatRequest, context: ConversionContext
    ) -> int | None:
        """Normalize ``max_tokens``/``max_completion_tokens`` into one value."""
        max_tokens = payload.max_tokens
        max_completion_tokens = payload.max_completion_tokens
        if max_tokens is not None and max_completion_tokens is not None:
            if max_tokens != max_completion_tokens:
                record_loss(
                    context,
                    field="max_completion_tokens",
                    target=_TARGET,
                    reason="conflicts_with_max_tokens",
                )
            return max_completion_tokens
        if max_completion_tokens is not None:
            return max_completion_tokens
        return max_tokens

    @staticmethod
    def _wire_parts_to_ir(
        parts: list[dict[str, Any]], context: ConversionContext
    ) -> list[Any]:
        """Convert wire content parts into canonical content parts."""
        converted: list[Any] = []
        for part in parts:
            if not isinstance(part, dict):
                converted.append(TextPart(text=str(part)))
                continue
            part_type = part.get("type")
            if part_type == "text":
                converted.append(TextPart(text=str(part.get("text", ""))))
            elif part_type == "image_url":
                image = part.get("image_url")
                if isinstance(image, dict):
                    converted.append(
                        ImageUrlPart(
                            url=str(image.get("url", "")),
                            detail=cast("Any", image.get("detail", "auto") or "auto"),
                        )
                    )
                else:
                    converted.append(TextPart(text=str(part)))
            else:
                record_loss(
                    context,
                    field=part_type or "part",
                    target=_TARGET,
                    reason="unknown_part_type",
                )
        return converted

    @staticmethod
    def _message_text_to_ir(
        message: OpenAIChatMessage, context: ConversionContext
    ) -> str:
        """Extract text content from a response message."""
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return _extract_text(content, context, field="message.content")
        return ""

    @staticmethod
    def _reasoning_from_message(
        message: OpenAIChatMessage, usage: dict[str, Any] | None
    ) -> ThinkingResult | None:
        """Build a ``ThinkingResult`` from message reasoning passthrough."""
        raw = message.passthrough.get("reasoning") or message.passthrough.get(
            "reasoning_content"
        )
        reasoning_text: str | None = None
        if isinstance(raw, str) and raw:
            reasoning_text = raw
        elif isinstance(raw, dict) and isinstance(raw.get("content"), str):
            reasoning_text = raw["content"]
        if reasoning_text is None:
            return None
        tokens: int | None = None
        if isinstance(usage, dict):
            details = usage.get("completion_tokens_details")
            if isinstance(details, dict) and isinstance(
                details.get("reasoning_tokens"), int
            ):
                tokens = details["reasoning_tokens"]
        return ThinkingResult(content=reasoning_text, tokens=tokens)

    @staticmethod
    def _usage_from_wire(usage: dict[str, Any] | None) -> RelayUsage | None:
        """Map a wire usage dict into canonical ``RelayUsage``."""
        if not isinstance(usage, dict):
            return None
        prompt_details = usage.get("prompt_tokens_details")
        completion_details = usage.get("completion_tokens_details")
        audio_tokens = usage.get("audio_tokens")
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        return RelayUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=(
                int(prompt_details.get("cached_tokens", 0) or 0)
                if isinstance(prompt_details, dict)
                else 0
            ),
            cache_creation_tokens=(
                int(
                    prompt_details.get("cached_creation_tokens", 0)
                    or prompt_details.get("cache_write_tokens", 0)
                    or 0
                )
                if isinstance(prompt_details, dict)
                else 0
            ),
            reasoning_tokens=(
                int(completion_details.get("reasoning_tokens", 0) or 0)
                if isinstance(completion_details, dict)
                else 0
            ),
            audio_input_tokens=(
                int(audio_tokens.get("input_tokens", 0) or 0)
                if isinstance(audio_tokens, dict)
                else 0
            ),
            audio_output_tokens=(
                int(audio_tokens.get("output_tokens", 0) or 0)
                if isinstance(audio_tokens, dict)
                else 0
            ),
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
        )
