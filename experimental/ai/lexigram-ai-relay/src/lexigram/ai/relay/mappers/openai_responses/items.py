"""IR-to-wire item building for the OpenAI Responses mapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.ai.relay.mappers.openai_responses.utils import (
    _TARGET,
    _arguments_to_wire,
)
from lexigram.contracts.ai.llm import ChatMessage
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import ResponsesItem
from lexigram.contracts.ai.relay.ir import RelayRequest

if TYPE_CHECKING:
    from lexigram.ai.relay.mappers.openai_responses import OpenAIResponsesMapper


class ItemsMixin:
    """Serializes canonical messages into wire response items."""

    def _message_to_item(
        self: OpenAIResponsesMapper,
        message: ChatMessage,
        context: ConversionContext,
    ) -> ResponsesItem:
        """Convert a canonical message into a wire message item."""
        data: dict[str, Any] = {"role": message.role}
        if message.metadata and message.metadata.get("item_id"):
            data["id"] = message.metadata["item_id"]
        files = (message.metadata or {}).get("input_files")
        has_files = isinstance(files, list) and any(
            isinstance(item, dict) for item in files
        )
        if isinstance(message.content, str):
            if message.content and not has_files:
                data["content"] = message.content
            elif message.content or has_files:
                parts = self._message_content_parts(message, context)
                if parts:
                    data["content"] = parts
        else:
            parts = self._message_content_parts(message, context)
            if parts:
                data["content"] = parts
        return ResponsesItem(**data)

    @staticmethod
    def _message_content_parts(
        message: ChatMessage, context: ConversionContext
    ) -> list[dict[str, Any]]:
        """Serialize canonical content into wire message parts."""
        parts: list[dict[str, Any]] = []
        content = message.content
        if isinstance(content, str):
            if content:
                parts.append({"type": "input_text", "text": content})
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, TextPart):
                    parts.append({"type": "input_text", "text": part.text})
                elif isinstance(part, ImageUrlPart):
                    parts.append(
                        {
                            "type": "input_image",
                            "image_url": part.url,
                        }
                    )
                elif isinstance(part, ImageBase64Part):
                    parts.append(
                        {
                            "type": "input_image",
                            "image_url": f"data:{part.media_type};base64,{part.data}",
                        }
                    )
                else:
                    record_loss(
                        context,
                        field="message.content",
                        target=_TARGET,
                        reason="unknown_content_part",
                    )
        files = (message.metadata or {}).get("input_files")
        if isinstance(files, list):
            for file_part in files:
                if isinstance(file_part, dict):
                    parts.append(file_part)
        return parts

    def _tool_calls_to_items(
        self: OpenAIResponsesMapper,
        message: ChatMessage,
        context: ConversionContext,
    ) -> list[ResponsesItem]:
        """Convert a tool-calling assistant turn into wire items."""
        items: list[ResponsesItem] = []
        if self._message_content_parts(message, context):
            items.append(self._message_to_item(message, context))
        else:
            items.append(ResponsesItem(role="assistant", content=""))
        item_ids = (message.metadata or {}).get("function_call_item_ids")
        for index, tool in enumerate(message.tool_calls or []):
            data: dict[str, Any] = {
                "type": "function_call",
                "call_id": tool.id or f"call_{index + 1}",
                "name": tool.function.name if tool.function else "",
                "arguments": _arguments_to_wire(
                    tool.function.arguments if tool.function else {}
                ),
            }
            if isinstance(item_ids, list) and index < len(item_ids) and item_ids[index]:
                data["id"] = item_ids[index]
            items.append(ResponsesItem(**data))
        return items

    def _thinking_to_items(
        self: OpenAIResponsesMapper, message: ChatMessage
    ) -> list[ResponsesItem]:
        """Convert canonical thinking blocks into a reasoning item."""
        summary = list(message.thinking_blocks or [])
        if not summary:
            return []
        data: dict[str, Any] = {"type": "reasoning", "summary": summary}
        if message.metadata and message.metadata.get("item_id"):
            data["id"] = message.metadata["item_id"]
        return [ResponsesItem(**data)]

    @staticmethod
    def _tool_result_to_item(message: ChatMessage) -> ResponsesItem:
        """Convert a canonical tool message into a wire output item."""
        content = message.content
        if isinstance(content, list):
            output = "".join(
                part.text for part in content if isinstance(part, TextPart)
            )
        else:
            output = content or ""
        data: dict[str, Any] = {
            "type": "function_call_output",
            "output": str(output),
            "call_id": message.tool_call_id or "call_0",
        }
        if message.metadata and message.metadata.get("item_id"):
            data["id"] = message.metadata["item_id"]
        return ResponsesItem(**data)

    @staticmethod
    def _system_text(message: ChatMessage) -> str:
        """Extract text from a system-role canonical message."""
        content = message.content
        if isinstance(content, str):
            return content
        return "".join(part.text for part in content if isinstance(part, TextPart))

    @staticmethod
    def _web_search_items(request: RelayRequest) -> list[ResponsesItem]:
        """Restore preserved web_search_call input items."""
        raw = request.metadata.get("input_web_search_calls")
        items: list[ResponsesItem] = []
        if isinstance(raw, list):
            for entry in raw:
                if not isinstance(entry, dict):
                    continue
                data = dict(entry)
                items.append(
                    ResponsesItem(
                        type=str(data.pop("type", "web_search_call")),
                        id=data.pop("id", None),
                        passthrough=data,
                    )
                )
        return items
