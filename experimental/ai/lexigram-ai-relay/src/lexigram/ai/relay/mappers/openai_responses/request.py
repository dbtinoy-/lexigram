"""Request-direction conversion for the OpenAI Responses mapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate, unsupported_format
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.ai.relay.mappers.openai_responses.utils import (
    _TARGET,
    _parse_arguments,
)
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import ResponsesItem, ResponsesRequest
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.ai.thinking import ThinkingConfig
from lexigram.contracts.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.relay.mappers.openai_responses import OpenAIResponsesMapper


class RequestMixin:
    """Request conversion: wire ``ResponsesRequest`` to IR and back."""

    def request_to_ir(
        self: OpenAIResponsesMapper,
        payload: Any,
        *,
        context: ConversionContext,
    ) -> Result[RelayRequest, RelayError]:
        """Convert a ``ResponsesRequest`` into canonical ``RelayRequest``.

        Args:
            payload: A wire request DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on malformed payload.
        """
        if not isinstance(payload, ResponsesRequest):
            return Err(
                unsupported_format(
                    f"expected ResponsesRequest, got {type(payload).__name__}"
                )
            )
        system_parts: list[str] = []
        if payload.instructions:
            system_parts.append(payload.instructions)
        messages: list[ChatMessage] = []
        pending_tools: list[ToolCall] = []
        pending_ids: list[str | None] = []
        web_search_calls: list[dict[str, Any]] = []

        def flush_tools() -> None:
            """Emit accumulated function calls as one assistant turn."""
            if not pending_tools:
                return
            metadata: dict[str, Any] = {}
            if any(pending_ids):
                metadata["function_call_item_ids"] = list(pending_ids)
            messages.append(
                ChatMessage(
                    role="assistant",
                    content="",
                    tool_calls=list(pending_tools),
                    metadata=metadata or None,
                )
            )
            pending_tools.clear()
            pending_ids.clear()

        if isinstance(payload.input, str):
            messages.append(ChatMessage(role="user", content=payload.input))
        else:
            for index, wire_item in enumerate(payload.input):
                item_type = wire_item.type
                if item_type == "message":
                    flush_tools()
                    if wire_item.role == "system":
                        system_parts.append(self._message_text_to_ir(wire_item))
                        if index > 0:
                            record_loss(
                                context,
                                field="system_message",
                                target=_TARGET,
                                reason="system_message_reordered",
                            )
                        continue
                    messages.append(self._message_from_item(wire_item, context))
                elif item_type == "function_call":
                    pending_tools.append(self._tool_from_item(wire_item))
                    pending_ids.append(wire_item.id or wire_item.call_id)
                elif item_type == "function_call_output":
                    flush_tools()
                    messages.append(self._tool_result_from_item(wire_item))
                elif item_type == "reasoning":
                    flush_tools()
                    messages.append(self._reasoning_from_item(wire_item))
                elif item_type == "web_search_call":
                    web_search_calls.append(wire_item.to_dict())
                    record_loss(
                        context,
                        field=f"input[{index}]",
                        target=_TARGET,
                        reason="unsupported_item_preserved",
                        severity="info",
                    )
                else:
                    record_loss(
                        context,
                        field=f"input[{index}]",
                        target=_TARGET,
                        reason="unknown_item_dropped",
                    )
            flush_tools()
        metadata: dict[str, Any] = {}
        if payload.include is not None:
            metadata["include"] = list(payload.include)
        if payload.max_output_tokens is not None:
            metadata["max_tokens_kind"] = "max_completion_tokens"
        if web_search_calls:
            metadata["input_web_search_calls"] = web_search_calls
        reasoning = payload.reasoning
        if reasoning is not None:
            metadata["reasoning"] = reasoning
        if payload.text is not None:
            metadata["text"] = payload.text
        if payload.service_tier is not None:
            metadata["service_tier"] = payload.service_tier
        thinking: ThinkingConfig | None = None
        if isinstance(reasoning, dict):
            thinking = ThinkingConfig(effort=reasoning.get("effort"))
        return Ok(
            RelayRequest(
                model=context.normalize_model(payload.model),
                messages=messages,
                system="\n".join(system_parts) if system_parts else None,
                tools=self._tools_to_ir(payload.tools, context),
                temperature=payload.temperature,
                max_tokens=payload.max_output_tokens,
                stream=payload.stream,
                include_usage=bool(payload.include and "usage" in payload.include),
                parallel_tool_calls=payload.parallel_tool_calls,
                thinking=thinking,
                response_format=self._text_to_response_format(payload.text),
                metadata=metadata,
                passthrough=dict(payload.passthrough),
            )
        )

    def ir_to_request(
        self: OpenAIResponsesMapper,
        request: RelayRequest,
        *,
        context: ConversionContext,
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayRequest`` into a ``ResponsesRequest``.

        Args:
            request: Canonical request IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on failure.
        """
        try:
            items: list[ResponsesItem] = []
            instructions = request.system
            system_parts = [request.system] if request.system else []
            for message in request.messages:
                if message.role == "system":
                    system_parts.append(self._system_text(message))
                    record_loss(
                        context,
                        field="system_message",
                        target=_TARGET,
                        reason="system_message_reordered",
                    )
                    continue
                if message.role == "tool":
                    items.append(self._tool_result_to_item(message))
                    continue
                if message.tool_calls:
                    items.extend(self._tool_calls_to_items(message, context))
                    continue
                items.append(self._message_to_item(message, context))
            items.extend(self._web_search_items(request))
            if system_parts:
                instructions = "\n".join(system_parts)
            handled_metadata = {
                "include",
                "reasoning",
                "text",
                "service_tier",
                "input_web_search_calls",
                "generation_config",
                "safety_settings",
                "tool_config",
            }
            return Ok(
                ResponsesRequest(
                    model=context.resolve_model(request.model),
                    input=items,
                    instructions=instructions,
                    tools=(
                        [self._tool_from_ir(tool) for tool in request.tools]
                        if request.tools
                        else None
                    ),
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                    stream=request.stream,
                    include=self._include_from_ir(request),
                    parallel_tool_calls=request.parallel_tool_calls,
                    reasoning=self._reasoning_from_ir(request, context),
                    text=self._text_from_ir(request),
                    service_tier=request.metadata.get("service_tier"),
                    tool_choice=request.tool_choice,
                    passthrough={
                        **request.passthrough,
                        **{
                            key: value
                            for key, value in request.metadata.items()
                            if key not in handled_metadata
                        },
                    },
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="ir_to_request"))

    @staticmethod
    def _message_text_to_ir(wire_item: ResponsesItem) -> str:
        """Extract text from a wire message item."""
        return "".join(
            str(part.get("text", ""))
            for part in wire_item.content or []
            if isinstance(part, dict) and part.get("type") == "input_text"
        )

    @staticmethod
    def _input_parts_to_ir(
        content: list[dict[str, Any]] | None, context: ConversionContext
    ) -> tuple[list[Any], list[dict[str, Any]]]:
        """Convert wire content parts into canonical parts and files."""
        converted: list[Any] = []
        files: list[dict[str, Any]] = []
        for part in content or []:
            if not isinstance(part, dict):
                converted.append(TextPart(text=str(part)))
                continue
            part_type = part.get("type")
            if part_type == "input_text":
                converted.append(TextPart(text=str(part.get("text", ""))))
            elif part_type == "input_image":
                image = part.get("image_url")
                if isinstance(image, dict):
                    converted.append(
                        ImageUrlPart(
                            url=str(image.get("url", "")),
                            detail=cast("Any", image.get("detail", "auto") or "auto"),
                        )
                    )
                else:
                    converted.append(
                        ImageUrlPart(
                            url=str(image or ""),
                            detail=cast("Any", part.get("detail", "auto") or "auto"),
                        )
                    )
            elif part_type == "input_file":
                files.append(part)
                record_loss(
                    context,
                    field="content",
                    target=_TARGET,
                    reason="unrepresentable_part_preserved",
                    severity="info",
                )
            else:
                record_loss(
                    context,
                    field=part_type or "part",
                    target=_TARGET,
                    reason="unknown_part_type",
                )
        return converted, files

    def _message_from_item(
        self: OpenAIResponsesMapper,
        wire_item: ResponsesItem,
        context: ConversionContext,
    ) -> ChatMessage:
        """Convert a wire message item into a canonical message."""
        wire_content = wire_item.content
        if isinstance(wire_content, str):
            wire_content = [{"type": "input_text", "text": wire_content}]
        parts, files = self._input_parts_to_ir(wire_content, context)
        metadata: dict[str, Any] = {}
        if wire_item.id:
            metadata["item_id"] = wire_item.id
        if files:
            metadata["input_files"] = files
        content: str | list[Any]
        if len(parts) == 1 and isinstance(parts[0], TextPart):
            content = parts[0].text
        elif parts:
            content = parts
        else:
            content = ""
        return ChatMessage(
            role=wire_item.role or "user",
            content=content,
            metadata=metadata or None,
        )

    @staticmethod
    def _tool_from_item(wire_item: ResponsesItem) -> ToolCall:
        """Convert a wire function_call item into a canonical tool call."""
        return ToolCall(
            id=wire_item.call_id or wire_item.id or "",
            type="function",
            function=FunctionCall(
                name=wire_item.name or "",
                arguments=_parse_arguments(wire_item.arguments or ""),
            ),
        )

    @staticmethod
    def _tool_result_from_item(wire_item: ResponsesItem) -> ChatMessage:
        """Convert a wire function_call_output item into a tool message."""
        metadata: dict[str, Any] = {}
        if wire_item.id:
            metadata["item_id"] = wire_item.id
        return ChatMessage(
            role="tool",
            content=wire_item.output or "",
            tool_call_id=wire_item.call_id,
            metadata=metadata or None,
        )

    @staticmethod
    def _reasoning_from_item(wire_item: ResponsesItem) -> ChatMessage:
        """Convert a wire reasoning item into an assistant message."""
        metadata: dict[str, Any] = {}
        if wire_item.id:
            metadata["item_id"] = wire_item.id
        return ChatMessage(
            role="assistant",
            content="",
            thinking_blocks=list(wire_item.summary or []),
            metadata=metadata or None,
        )

    @staticmethod
    def _tools_to_ir(
        tools: list[dict[str, Any]] | None, context: ConversionContext
    ) -> list[ToolDefinition]:
        """Convert wire tool dicts into canonical tool definitions."""
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
            if isinstance(tool.get("function"), dict):
                function = tool["function"]
            else:
                function = tool
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
    def _tool_from_ir(tool: ToolDefinition) -> dict[str, Any]:
        """Serialize a canonical tool definition as a wire tool dict."""
        return {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }

    @staticmethod
    def _text_to_response_format(
        text: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Derive a canonical response format from the wire text config."""
        if not isinstance(text, dict):
            return None
        fmt = text.get("format")
        if not isinstance(fmt, dict):
            return None
        fmt_type = fmt.get("type")
        if fmt_type == "json_object":
            return {"type": "json_object"}
        if fmt_type == "json_schema":
            result: dict[str, Any] = {"type": "json_schema"}
            for key in ("schema", "name", "strict"):
                if key in fmt:
                    result[key] = fmt[key]
            return result
        return None

    @classmethod
    def _text_from_ir(cls, request: RelayRequest) -> dict[str, Any] | None:
        """Rebuild the wire text config from canonical response format."""
        raw = request.metadata.get("text")
        text: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
        response_format = request.response_format
        if response_format is None:
            return text or None
        fmt_type = response_format.get("type")
        if fmt_type == "json_object":
            text["format"] = {"type": "json_object"}
        elif fmt_type == "json_schema":
            fmt: dict[str, Any] = {"type": "json_schema"}
            for key in ("schema", "name", "strict"):
                if key in response_format:
                    fmt[key] = response_format[key]
            text["format"] = fmt
        else:
            text["format"] = {"type": "text"}
        return text or None

    @staticmethod
    def _include_from_ir(request: RelayRequest) -> list[str] | None:
        """Rebuild the wire include list from canonical stream settings."""
        raw = request.metadata.get("include")
        include = list(raw) if isinstance(raw, list) else []
        if request.include_usage and "usage" not in include:
            include.append("usage")
        return include or None

    def _reasoning_from_ir(
        self: OpenAIResponsesMapper,
        request: RelayRequest,
        context: ConversionContext,
    ) -> dict[str, Any] | None:
        """Rebuild the wire reasoning config from canonical thinking."""
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
