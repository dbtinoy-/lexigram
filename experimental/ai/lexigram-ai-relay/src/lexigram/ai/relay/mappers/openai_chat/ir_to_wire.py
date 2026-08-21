"""IR → wire building helpers for the OpenAI Chat mapper."""

from __future__ import annotations

from typing import Any, cast

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.ai.relay.mappers.openai_chat._helpers import (
    _MESSAGE_METADATA_INTERNAL,
    _TARGET,
    _tool_call_to_wire,
)
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.llm import ChatMessage
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import OpenAIChatMessage
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.ai.relay.types import RelayUsage


class IRToWireMixin:
    """Builders turning canonical IR into OpenAI Chat wire shapes."""

    def _message_from_ir(
        self, message: ChatMessage, context: ConversionContext
    ) -> OpenAIChatMessage:
        """Convert a canonical message into an ``OpenAIChatMessage``."""
        content: Any
        if isinstance(message.content, list):
            parts: list[Any] = []
            for part in message.content:
                if isinstance(part, TextPart):
                    parts.append({"type": "text", "text": part.text})
                elif isinstance(part, ImageUrlPart):
                    parts.append(
                        {
                            "type": "image_url",
                            "image_url": part.url,
                        }
                    )
                elif isinstance(part, ImageBase64Part):
                    image_url: dict[str, Any] = {
                        "url": f"data:{part.media_type};base64,{part.data}",
                    }
                    if part.detail:
                        image_url["detail"] = part.detail
                    parts.append(
                        {
                            "type": "image_url",
                            "image_url": image_url,
                        }
                    )
                else:
                    record_loss(
                        context,
                        field="message.content",
                        target=_TARGET,
                        reason="unknown_content_part",
                    )
            content = parts
        elif message.content == "":
            content = None
        else:
            content = message.content
        return OpenAIChatMessage(
            role=message.role,
            content=cast("str | None", content),
            name=message.name,
            tool_call_id=message.tool_call_id,
            tool_calls=(
                [_tool_call_to_wire(tool) for tool in message.tool_calls]
                if message.tool_calls
                else None
            ),
            passthrough={
                key: value
                for key, value in (message.metadata or {}).items()
                if key not in _MESSAGE_METADATA_INTERNAL
            },
        )

    @staticmethod
    def _tool_from_ir(tool: ToolDefinition) -> dict[str, Any]:
        """Serialize a canonical ``ToolDefinition`` as a wire tool dict."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    @staticmethod
    def _stream_options_from_ir(request: RelayRequest) -> dict[str, Any] | None:
        """Rebuild ``stream_options`` from canonical stream settings."""
        raw = request.metadata.get("stream_options")
        options: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
        if request.include_usage:
            options["include_usage"] = True
        elif "include_usage" in options:
            options.pop("include_usage")
        if not options:
            return None
        return options

    def _reasoning_from_ir(
        self, request: RelayRequest, context: ConversionContext
    ) -> dict[str, Any] | None:
        """Rebuild the OpenAI ``reasoning`` config from canonical thinking."""
        thinking = request.thinking
        if thinking is not None:
            if thinking.effort is not None:
                return {"effort": thinking.effort}
            record_loss(
                context,
                field="thinking",
                target=_TARGET,
                reason="effort_only_supported",
            )
        raw = request.metadata.get("reasoning")
        if isinstance(raw, dict):
            return dict(raw)
        return None

    @staticmethod
    def _stop_from_ir(stop_sequences: list[str]) -> str | list[str] | None:
        """Rebuild a wire ``stop`` value from canonical stop sequences."""
        if not stop_sequences:
            return None
        if len(stop_sequences) == 1:
            return stop_sequences[0]
        return list(stop_sequences)

    @staticmethod
    def _usage_to_wire(usage: RelayUsage | None) -> dict[str, Any] | None:
        """Serialize canonical ``RelayUsage`` into a wire usage dict.

        Mirrors relaykit's ``dto.Usage`` serialization: the detail
        containers and responses-style ``input_tokens``/``output_tokens``
        are always present (zeros included), and cache-write counters are
        added only when non-zero.
        """
        if usage is None:
            return None
        data: dict[str, Any] = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "prompt_tokens_details": {"cached_tokens": usage.cache_read_tokens},
            "completion_tokens_details": {"reasoning_tokens": usage.reasoning_tokens},
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        }
        if usage.cache_creation_tokens:
            data["prompt_tokens_details"]["cached_creation_tokens"] = (
                usage.cache_creation_tokens
            )
            data["prompt_tokens_details"]["cache_write_tokens"] = (
                usage.cache_creation_tokens
            )
        if usage.audio_input_tokens or usage.audio_output_tokens:
            data["audio_tokens"] = {
                "input_tokens": usage.audio_input_tokens,
                "output_tokens": usage.audio_output_tokens,
            }
        return data
