"""OpenAI Responses request and response mapper.

Converts the OpenAI Responses wire DTOs
(:class:`ResponsesRequest` / :class:`ResponsesResponse`) into the
canonical relay IR and back.  Stream conversion is handled by the shared
stream lifecycle task and reports ``unsupported_feature`` until then.
"""

from __future__ import annotations

from typing import Any, cast

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate, unsupported_feature, unsupported_format
from lexigram.ai.relay.finish_reasons import (
    responses_incomplete_from_finish,
    responses_status_from_finish,
)
from lexigram.ai.relay.mappers.base import new_uuid, record_loss
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import (
    ResponsesIncompleteDetails,
    ResponsesItem,
    ResponsesRequest,
    ResponsesResponse,
    ResponsesUsage,
)
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    StreamDelta,
    StreamState,
)
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import dumps_str, loads_str

__all__ = ["OpenAIResponsesMapper"]

_TARGET = RelayFormat.OPENAI_RESPONSES


def _parse_arguments(arguments: str) -> dict[str, Any] | str:
    """Parse a wire arguments string into dict form when possible.

    Args:
        arguments: Raw JSON argument string from the wild.

    Returns:
        The parsed dict, or the original string when it is empty or not
        valid JSON.
    """
    if not isinstance(arguments, str) or not arguments.strip():
        return arguments
    try:
        value = loads_str(arguments)
    except (ValueError, TypeError):
        return arguments
    if isinstance(value, dict):
        return value
    return arguments


def _arguments_to_wire(arguments: Any) -> str:
    """Serialize canonical arguments into a JSON string.

    Args:
        arguments: Canonical arguments (dict, string, or anything else).

    Returns:
        A JSON string for the wire, or an empty string when unsupported.
    """
    if isinstance(arguments, dict):
        return dumps_str(arguments)
    if isinstance(arguments, str):
        return arguments
    return ""


class OpenAIResponsesMapper:
    """Bidirectional OpenAI Responses converter.

    Attributes:
        format: The wire format this mapper handles.
    """

    format = _TARGET

    def request_to_ir(
        self, payload: Any, *, context: ConversionContext
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
        self, request: RelayRequest, *, context: ConversionContext
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

    def response_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayResponse, RelayError]:
        """Convert a ``ResponsesResponse`` into canonical ``RelayResponse``.

        Args:
            payload: A wire response DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on malformed payload.
        """
        if not isinstance(payload, ResponsesResponse):
            return Err(
                unsupported_format(
                    f"expected ResponsesResponse, got {type(payload).__name__}"
                )
            )
        try:
            passthrough = dict(payload.passthrough)
            if payload.error is not None:
                passthrough["error"] = payload.error
            if payload.object != "response":
                passthrough["object"] = payload.object
            content_parts: list[str] = []
            tool_calls: list[ToolCall] = []
            tool_results: list[ChatMessage] = []
            reasoning_text: list[str] = []
            web_search_calls: list[dict[str, Any]] = []
            for index, output_item in enumerate(payload.output):
                item_type = output_item.type
                if item_type == "message":
                    for part in output_item.content or []:
                        if not isinstance(part, dict):
                            content_parts.append(str(part))
                            continue
                        part_type = part.get("type")
                        if part_type == "output_text":
                            content_parts.append(str(part.get("text", "")))
                        else:
                            record_loss(
                                context,
                                field=part_type or "part",
                                target=_TARGET,
                                reason="unknown_part_type",
                            )
                elif item_type == "reasoning":
                    reasoning_text.extend(self._summary_texts(output_item.summary))
                elif item_type == "function_call":
                    tool_calls.append(
                        ToolCall(
                            id=output_item.call_id or output_item.id or "",
                            type="function",
                            function=FunctionCall(
                                name=output_item.name or "",
                                arguments=_parse_arguments(output_item.arguments or ""),
                            ),
                        )
                    )
                elif item_type == "function_call_output":
                    tool_results.append(
                        ChatMessage(
                            role="tool",
                            content=output_item.output or "",
                            tool_call_id=output_item.call_id,
                        )
                    )
                elif item_type == "web_search_call":
                    web_search_calls.append(output_item.to_dict())
                    record_loss(
                        context,
                        field=f"output[{index}]",
                        target=_TARGET,
                        reason="unsupported_item_preserved",
                        severity="info",
                    )
                else:
                    record_loss(
                        context,
                        field=f"output[{index}]",
                        target=_TARGET,
                        reason="unknown_item_dropped",
                    )
            if web_search_calls:
                passthrough["web_search_calls"] = web_search_calls
            thinking: ThinkingResult | None = None
            if reasoning_text:
                tokens: int | None = None
                if payload.usage is not None:
                    details = payload.usage.output_tokens_details
                    if isinstance(details, dict) and isinstance(
                        details.get("reasoning_tokens"), int
                    ):
                        tokens = details["reasoning_tokens"]
                thinking = ThinkingResult(
                    content="".join(reasoning_text), tokens=tokens
                )
            return Ok(
                RelayResponse(
                    model=payload.model,
                    id=payload.id,
                    created=payload.created_at,
                    content="".join(content_parts),
                    thinking=thinking,
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    finish_reason=self._finish_from_status(
                        payload.status,
                        payload.incomplete_details,
                        bool(tool_calls),
                    ),
                    status=payload.status,
                    incomplete_details=(
                        payload.incomplete_details.to_dict()
                        if payload.incomplete_details is not None
                        else None
                    ),
                    usage=self._usage_from_wire(payload.usage),
                    passthrough=passthrough,
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="response_to_ir"))

    def ir_to_response(
        self, response: RelayResponse, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayResponse`` into a ``ResponsesResponse``.

        Args:
            response: Canonical response IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on failure.
        """
        try:
            passthrough = dict(response.passthrough)
            error = passthrough.pop("error", None)
            object_type = passthrough.pop("object", "response")
            status, incomplete = self._status_from_finish(response)
            response_id = response.id or f"chatcmpl-{new_uuid()}"
            item_status = "incomplete" if status == "incomplete" else "completed"
            items: list[ResponsesItem] = []
            content_parts: list[dict[str, Any]] = []
            if response.content:
                content_parts.append(
                    {
                        "type": "output_text",
                        "text": response.content,
                        "annotations": [],
                    }
                )
            if content_parts:
                items.append(
                    ResponsesItem(
                        type="message",
                        role="assistant",
                        id=f"{response_id}_msg_0",
                        status=item_status,
                        content=content_parts,
                        quality="",
                        size="",
                    )
                )
            if response.thinking is not None and response.thinking.content:
                items.append(
                    ResponsesItem(
                        type="reasoning",
                        id=f"{response_id}_reasoning_0",
                        status=item_status,
                        role="",
                        content=[
                            {
                                "type": "summary_text",
                                "text": response.thinking.content,
                                "annotations": None,
                            }
                        ],
                        quality="",
                        size="",
                    )
                )
            for tool in response.tool_calls:
                call_id = tool.id or f"call_{new_uuid()}"
                items.append(
                    ResponsesItem(
                        type="function_call",
                        id=call_id,
                        status=item_status,
                        role="",
                        content=None,
                        quality="",
                        size="",
                        call_id=call_id,
                        name=tool.function.name if tool.function else "",
                        arguments=_arguments_to_wire(
                            tool.function.arguments if tool.function else {}
                        ),
                    )
                )
            for index, result in enumerate(response.tool_results):
                items.append(
                    ResponsesItem(
                        type="function_call_output",
                        id=f"fcoc_{index}",
                        call_id=result.tool_call_id,
                        output=self._result_output(result),
                    )
                )
            return Ok(
                ResponsesResponse(
                    id=response_id,
                    model=context.resolve_model(response.model),
                    output=items,
                    object=object_type,
                    created_at=response.created or 0,
                    status=status,
                    incomplete_details=incomplete,
                    error=error if isinstance(error, dict) else None,
                    usage=self._usage_to_wire(response.usage),
                    passthrough=passthrough,
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="ir_to_response"))

    def stream_to_delta(
        self, event: Any, *, state: StreamState
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature(
                "openai_responses stream conversion is not implemented yet"
            )
        )

    def delta_to_stream(
        self, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        """Stream emission is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature(
                "openai_responses stream conversion is not implemented yet"
            )
        )

    # -- helpers -------------------------------------------------------------

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
        self, wire_item: ResponsesItem, context: ConversionContext
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

    def _message_to_item(
        self, message: ChatMessage, context: ConversionContext
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
        self, message: ChatMessage, context: ConversionContext
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

    def _thinking_to_items(self, message: ChatMessage) -> list[ResponsesItem]:
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
        self, request: RelayRequest, context: ConversionContext
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

    @staticmethod
    def _summary_texts(
        summary: list[dict[str, Any]] | None,
    ) -> list[str]:
        """Extract text from reasoning summary blocks."""
        return [
            str(item.get("text", ""))
            for item in summary or []
            if isinstance(item, dict) and item.get("type") == "summary_text"
        ]

    @staticmethod
    def _finish_from_status(
        status: str | None,
        incomplete_details: ResponsesIncompleteDetails | None,
        has_tool_calls: bool,
    ) -> str | None:
        """Derive a canonical finish reason from a wire status."""
        if status == "completed":
            return "tool_calls" if has_tool_calls else "stop"
        if status == "incomplete":
            reason = (
                incomplete_details.reason if incomplete_details is not None else None
            )
            if reason == "max_output_tokens":
                return "length"
            if reason == "content_filter":
                return "content_filter"
            return "other"
        if status == "failed":
            return "other"
        return None

    @staticmethod
    def _status_from_finish(
        response: RelayResponse,
    ) -> tuple[str | None, ResponsesIncompleteDetails | None]:
        """Derive a wire status from canonical finish behavior."""
        status = response.status
        incomplete: ResponsesIncompleteDetails | None = None
        if response.incomplete_details is not None:
            raw = dict(response.incomplete_details)
            reason = raw.pop("reason", None)
            incomplete = ResponsesIncompleteDetails(reason=reason, passthrough=raw)
        if status is not None:
            if status == "incomplete" and incomplete is None:
                derived = _incomplete_for_finish(response.finish_reason)
                if derived is not None:
                    incomplete = derived
            return status, incomplete
        finish = response.finish_reason
        wire_status, detail = responses_status_from_finish(finish)
        if detail is None:
            return wire_status, None
        return wire_status, ResponsesIncompleteDetails(reason=detail)

    @staticmethod
    def _result_output(message: ChatMessage) -> str:
        """Extract a tool result string from a canonical tool message."""
        content = message.content
        if isinstance(content, list):
            return "".join(part.text for part in content if isinstance(part, TextPart))
        return str(content or "")

    @staticmethod
    def _usage_from_wire(usage: ResponsesUsage | None) -> RelayUsage | None:
        """Map wire usage into canonical ``RelayUsage``."""
        if usage is None:
            return None
        input_details = usage.input_tokens_details
        completion_details = usage.completion_tokens_details
        if not isinstance(completion_details, dict):
            completion_details = usage.output_tokens_details
        return RelayUsage(
            prompt_tokens=usage.prompt_tokens or usage.input_tokens,
            completion_tokens=usage.completion_tokens or usage.output_tokens,
            total_tokens_override=usage.total_tokens or None,
            cache_read_tokens=(
                int(input_details.get("cached_tokens", 0) or 0)
                if isinstance(input_details, dict)
                else 0
            ),
            reasoning_tokens=(
                int(completion_details.get("reasoning_tokens", 0) or 0)
                if isinstance(completion_details, dict)
                else 0
            ),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )

    @staticmethod
    def _usage_to_wire(usage: RelayUsage | None) -> ResponsesUsage | None:
        """Serialize canonical ``RelayUsage`` into wire usage."""
        if usage is None:
            return None
        input_details = (
            {"cached_tokens": usage.cache_read_tokens}
            if usage.cache_read_tokens
            else None
        )
        return ResponsesUsage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            prompt_tokens_details={"cached_tokens": 0},
            completion_tokens_details={"reasoning_tokens": usage.reasoning_tokens},
            input_tokens=usage.prompt_tokens,
            input_tokens_details=input_details,
            output_tokens=usage.completion_tokens,
        )


def _incomplete_for_finish(
    finish_reason: str | None,
) -> ResponsesIncompleteDetails | None:
    """Map a canonical finish reason to an incomplete-details payload."""
    detail = responses_incomplete_from_finish(finish_reason)
    if detail is None:
        return None
    return ResponsesIncompleteDetails(reason=detail)
