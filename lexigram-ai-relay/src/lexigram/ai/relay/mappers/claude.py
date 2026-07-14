"""Anthropic Claude Messages request and response mapper.

Converts the Claude Messages wire DTOs
(:class:`ClaudeRequest` / :class:`ClaudeResponse`) into the canonical
relay IR and back.  Stream conversion is handled by the shared stream
lifecycle task and reports ``unsupported_feature`` until then.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import (
    missing_required_option,
    translate,
    unsupported_feature,
    unsupported_format,
)
from lexigram.ai.relay.finish_reasons import (
    FINISH_REASON_TO_WIRE,
    finish_reason_to_wire,
)
from lexigram.ai.relay.mappers.base import new_uuid, record_loss
from lexigram.ai.relay.media import resolve_media
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import (
    ContentPart,
    ImageBase64Part,
    ImageUrlPart,
    TextPart,
)
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeMessage,
    ClaudeRequest,
    ClaudeResponse,
    ClaudeUsage,
)
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    StreamDelta,
    StreamState,
    normalize_finish_reason,
)
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import loads_str

__all__ = ["ClaudeMapper"]

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


class ClaudeMapper:
    """Bidirectional Anthropic Claude Messages converter.

    Attributes:
        format: The wire format this mapper handles.
    """

    format = _TARGET

    def request_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayRequest, RelayError]:
        """Convert a ``ClaudeRequest`` into canonical ``RelayRequest``.

        Args:
            payload: A wire request DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on malformed payload.
        """
        if not isinstance(payload, ClaudeRequest):
            return Err(
                unsupported_format(
                    f"expected ClaudeRequest, got {type(payload).__name__}"
                )
            )
        try:
            tool_names: dict[str, str] = {}
            messages: list[ChatMessage] = []
            for index, message in enumerate(payload.messages):
                messages.extend(
                    self._message_to_ir(message, context, index, tool_names)
                )
            thinking: ThinkingConfig | None = None
            if isinstance(payload.thinking, dict):
                if payload.thinking.get("type") == "enabled":
                    thinking = ThinkingConfig(
                        budget_tokens=int(payload.thinking.get("budget_tokens", 0) or 0)
                    )
            metadata: dict[str, Any] = {}
            if payload.metadata is not None:
                metadata["metadata"] = payload.metadata
            return Ok(
                RelayRequest(
                    model=context.normalize_model(payload.model),
                    messages=messages,
                    system=self._system_to_ir(payload.system, context),
                    tools=self._tools_to_ir(payload.tools, context),
                    tool_choice=payload.tool_choice,
                    temperature=payload.temperature,
                    top_p=payload.top_p,
                    max_tokens=payload.max_tokens,
                    stop_sequences=list(payload.stop_sequences or []),
                    stream=payload.stream,
                    thinking=thinking,
                    metadata=metadata,
                    passthrough=dict(payload.passthrough),
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="request_to_ir"))

    def ir_to_request(
        self, request: RelayRequest, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayRequest`` into a ``ClaudeRequest``.

        Args:
            request: Canonical request IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on failure.
        """
        max_tokens = request.max_tokens
        if max_tokens is None:
            max_tokens = context.max_tokens_for(request.model)
        if max_tokens is None:
            return Err(missing_required_option("claude requires max_tokens"))
        model = request.model
        temperature = request.temperature
        top_p = request.top_p
        thinking = self._thinking_from_ir(request, context)
        claude_options = context.options.claude
        if claude_options.thinking_adapter_enabled and model.endswith("-thinking"):
            if (
                claude_options.minimum_max_tokens > 0
                and max_tokens < claude_options.minimum_max_tokens
            ):
                max_tokens = claude_options.minimum_max_tokens
                record_loss(
                    context,
                    field="max_tokens",
                    target=_TARGET,
                    reason="max_tokens_floored",
                )
            if thinking is None and claude_options.thinking_budget_percentage > 0:
                thinking = {
                    "type": "enabled",
                    "budget_tokens": int(
                        max_tokens * claude_options.thinking_budget_percentage / 100
                    ),
                }
            temperature = 1.0
            top_p = None
            if (
                not context.preserve_thinking_suffix(model)
                and not context.options.model_suffix_preserved
            ):
                model = model[: -len("-thinking")]
        try:
            messages: list[ClaudeMessage] = []
            system_parts: list[str] = []
            if request.system:
                system_parts.append(request.system)
            for message in request.messages:
                if message.role == "system":
                    system_parts.append(self._text_from_content(message.content))
                    continue
                prepared = message
                if message.role == "assistant" and message.tool_calls:
                    if any(not tool_call.id for tool_call in message.tool_calls):
                        prepared = replace(
                            message,
                            tool_calls=[
                                tool_call
                                if tool_call.id
                                else replace(tool_call, id=f"call_{index + 1}")
                                for index, tool_call in enumerate(message.tool_calls)
                            ],
                        )
                elif message.role == "tool" and not message.tool_call_id:
                    prepared = replace(message, tool_call_id="call_0")
                claude_message = self._message_from_ir(prepared, context)
                if claude_message.is_err():
                    return claude_message
                messages.append(claude_message.unwrap())
            tool_choice = request.tool_choice
            if isinstance(tool_choice, str):
                tool_choice = {"type": tool_choice}
            return Ok(
                ClaudeRequest(
                    model=context.resolve_model(model),
                    max_tokens=max_tokens,
                    messages=messages,
                    system=(
                        [{"type": "text", "text": "\n".join(system_parts)}]
                        if system_parts
                        else None
                    ),
                    temperature=temperature,
                    top_p=top_p,
                    stream=request.stream,
                    tools=(
                        [self._tool_from_ir(tool) for tool in request.tools]
                        if request.tools
                        else None
                    ),
                    tool_choice=tool_choice,
                    stop_sequences=list(request.stop_sequences) or None,
                    thinking=thinking,
                    metadata=(
                        request.metadata.get("metadata")
                        if isinstance(request.metadata.get("metadata"), dict)
                        else None
                    ),
                    passthrough={
                        **request.passthrough,
                        **{
                            key: value
                            for key, value in request.metadata.items()
                            if key
                            not in {
                                "metadata",
                                "max_tokens_kind",
                                "generation_config",
                                "safety_settings",
                                "tool_config",
                                "reasoning",
                                "stream_options",
                                "service_tier",
                            }
                        },
                    },
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="ir_to_request"))

    def response_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayResponse, RelayError]:
        """Convert a ``ClaudeResponse`` into canonical ``RelayResponse``.

        Args:
            payload: A wire response DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on malformed payload.
        """
        if not isinstance(payload, ClaudeResponse):
            return Err(
                unsupported_format(
                    f"expected ClaudeResponse, got {type(payload).__name__}"
                )
            )
        try:
            text_parts: list[str] = []
            thinking: ThinkingResult | None = None
            tool_calls: list[ToolCall] = []
            tool_results: list[ChatMessage] = []
            for block in payload.content:
                if block.type == "text":
                    if block.text is not None:
                        text_parts.append(block.text)
                elif block.type == "thinking":
                    if thinking is None and block.thinking is not None:
                        thinking = ThinkingResult(
                            content=block.thinking, signature=block.signature
                        )
                elif block.type == "tool_use":
                    tool_calls.append(_tool_call_from_block(block))
                elif block.type == "tool_result":
                    result_text = "".join(
                        part.text or ""
                        for part in (block.tool_result_content or [])
                        if part.type == "text"
                    )
                    tool_results.append(
                        ChatMessage(
                            role="tool",
                            content=result_text,
                            tool_call_id=block.tool_use_id,
                        )
                    )
                else:
                    record_loss(
                        context,
                        field=f"content.{block.type}",
                        target=_TARGET,
                        reason="unknown_block_dropped",
                    )
            passthrough = dict(payload.passthrough)
            if payload.stop_sequence is not None:
                passthrough["stop_sequence"] = payload.stop_sequence
            return Ok(
                RelayResponse(
                    model=payload.model,
                    id=payload.id,
                    content="".join(text_parts),
                    thinking=thinking,
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    finish_reason=normalize_finish_reason(payload.stop_reason),
                    usage=self._usage_from_wire(payload.usage),
                    passthrough=passthrough,
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="response_to_ir"))

    def ir_to_response(
        self, response: RelayResponse, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayResponse`` into a ``ClaudeResponse``.

        Args:
            response: Canonical response IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on failure.
        """
        try:
            passthrough = dict(response.passthrough)
            stop_sequence = passthrough.pop("stop_sequence", None)
            blocks: list[ClaudeContent] = []
            if response.content:
                blocks.append(ClaudeContent(type="text", text=response.content))
            for tool_call in response.tool_calls:
                blocks.append(_tool_call_to_block(tool_call))
            stop_reason: str | None = None
            if response.tool_calls:
                stop_reason = "tool_use"
            elif stop_sequence is not None:
                stop_reason = "stop_sequence"
            elif response.finish_reason is not None:
                stop_reason = self._stop_reason_from_ir(response.finish_reason, context)
            return Ok(
                ClaudeResponse(
                    id=response.id or f"chatcmpl-{new_uuid()}",
                    model=context.resolve_model(response.model),
                    content=blocks,
                    stop_reason=stop_reason,
                    stop_sequence=stop_sequence
                    if stop_reason == "stop_sequence"
                    else None,
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
            unsupported_feature("claude stream conversion is not implemented yet")
        )

    def delta_to_stream(
        self, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature("claude stream conversion is not implemented yet")
        )

    # -- helpers -------------------------------------------------------------

    def _message_to_ir(
        self,
        message: ClaudeMessage,
        context: ConversionContext,
        index: int,
        tool_names: dict[str, str],
    ) -> list[ChatMessage]:
        """Convert one Claude message into one or more canonical messages."""
        if message.role == "assistant":
            assistant_message = self._assistant_to_ir(message)
            for tool_call in assistant_message.tool_calls or []:
                if tool_call.id and tool_call.function and tool_call.function.name:
                    tool_names[tool_call.id] = tool_call.function.name
            return [assistant_message]
        if message.role == "user":
            return self._user_to_ir(message, context, index, tool_names)
        record_loss(
            context,
            field=f"messages[{index}].role",
            target=_TARGET,
            reason="unknown_role_dropped",
        )
        return []

    def _assistant_to_ir(self, message: ClaudeMessage) -> ChatMessage:
        """Convert an assistant message, separating thinking/tool blocks."""
        content = message.content
        if isinstance(content, str):
            content = [ClaudeContent(type="text", text=content)]
        text_parts: list[str] = []
        thinking_blocks: list[dict[str, Any]] = []
        tool_calls: list[ToolCall] = []
        for block in content:
            if block.type == "text":
                if block.text is not None:
                    text_parts.append(block.text)
            elif block.type == "thinking":
                thinking_blocks.append(
                    {
                        "type": "thinking",
                        "thinking": block.thinking or "",
                        "signature": block.signature or "",
                    }
                )
            elif block.type == "tool_use":
                tool_calls.append(_tool_call_from_block(block))
        return ChatMessage(
            role="assistant",
            content="".join(text_parts),
            tool_calls=tool_calls or None,
            thinking_blocks=thinking_blocks or None,
        )

    def _user_to_ir(
        self,
        message: ClaudeMessage,
        context: ConversionContext,
        index: int,
        tool_names: dict[str, str],
    ) -> list[ChatMessage]:
        """Convert a user message, unwrapping tool_result blocks."""
        content = message.content
        if isinstance(content, str):
            content = [ClaudeContent(type="text", text=content)]
        parts: list[ContentPart] = []
        tool_results: list[ChatMessage] = []
        has_tool_results = False
        has_other = False
        for block in content:
            if block.type == "tool_result":
                has_tool_results = True
                result_text = "".join(
                    part.text or ""
                    for part in (block.tool_result_content or [])
                    if part.type == "text"
                )
                metadata: dict[str, Any] | None = dict(block.passthrough) or None
                tool_results.append(
                    ChatMessage(
                        role="tool",
                        content=result_text,
                        tool_call_id=block.tool_use_id,
                        name=tool_names.get(block.tool_use_id or ""),
                        metadata=metadata,
                    )
                )
            elif block.type == "text":
                has_other = True
                if block.text is not None:
                    parts.append(TextPart(text=block.text))
            elif block.type == "image":
                has_other = True
                image = self._image_to_part(block, context, index)
                if image is not None:
                    parts.append(image)
            else:
                record_loss(
                    context,
                    field=f"messages[{index}].content.{block.type}",
                    target=_TARGET,
                    reason="unknown_block_dropped",
                )
        if has_tool_results and has_other:
            record_loss(
                context,
                field=f"messages[{index}]",
                target=_TARGET,
                reason="mixed_user_content_reordered",
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
                field=f"messages[{index}]",
                target=_TARGET,
                reason="empty_message_dropped",
            )
        return turns

    @staticmethod
    def _image_to_part(
        block: ClaudeContent, context: ConversionContext, index: int
    ) -> ContentPart | None:
        """Convert a Claude image block into a canonical image part."""
        source = block.image_source
        if not isinstance(source, dict):
            record_loss(
                context,
                field=f"messages[{index}].image",
                target=_TARGET,
                reason="missing_source",
            )
            return None
        source_type = source.get("type")
        if source_type == "base64":
            return ImageBase64Part(
                data=str(source.get("data", "")),
                media_type=str(source.get("media_type", "")),
            )
        if source_type == "url":
            return ImageUrlPart(url=str(source.get("url", "")))
        record_loss(
            context,
            field=f"messages[{index}].image",
            target=_TARGET,
            reason="unknown_source_type",
        )
        return None

    @staticmethod
    def _system_to_ir(
        system: str | list[dict[str, Any]] | None, context: ConversionContext
    ) -> str | None:
        """Normalize the Claude ``system`` field into canonical system text."""
        if system is None:
            return None
        if isinstance(system, str):
            return system
        texts: list[str] = []
        for block in system:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
            else:
                record_loss(
                    context,
                    field="system",
                    target=_TARGET,
                    reason="non_text_system_block_dropped",
                )
        return "\n".join(texts)

    @staticmethod
    def _tools_to_ir(
        tools: list[dict[str, Any]] | None, context: ConversionContext
    ) -> list[ToolDefinition]:
        """Convert Claude wire tools into canonical ``ToolDefinition`` objects."""
        definitions: list[ToolDefinition] = []
        for index, tool in enumerate(tools or []):
            if not isinstance(tool, dict):
                record_loss(
                    context,
                    field=f"tools[{index}]",
                    target=_TARGET,
                    reason="non_dict_tool_dropped",
                )
                continue
            schema = tool.get("input_schema", {})
            definitions.append(
                ToolDefinition(
                    name=str(tool.get("name", "")),
                    description=str(tool.get("description", "")),
                    parameters=schema if isinstance(schema, dict) else {},
                )
            )
        return definitions

    def _message_from_ir(
        self, message: ChatMessage, context: ConversionContext
    ) -> Result[ClaudeMessage, RelayError]:
        """Convert one canonical message into a Claude message."""
        if message.role == "tool":
            return Ok(
                ClaudeMessage(
                    role="user",
                    content=[
                        ClaudeContent(
                            type="tool_result",
                            tool_use_id=message.tool_call_id,
                            tool_result_content=[
                                ClaudeContent(
                                    type="text",
                                    text=self._text_from_content(message.content),
                                )
                            ],
                            passthrough=dict(message.metadata or {}),
                        )
                    ],
                )
            )
        if message.role == "assistant":
            blocks: list[ClaudeContent] = []
            for block in message.thinking_blocks or []:
                if isinstance(block, dict) and block.get("type") == "thinking":
                    blocks.append(
                        ClaudeContent(
                            type="thinking",
                            thinking=str(block.get("thinking", "")),
                            signature=(
                                str(block["signature"])
                                if block.get("signature")
                                else None
                            ),
                        )
                    )
            content_blocks = self._content_to_blocks(message.content, context)
            if content_blocks.is_err():
                return Err(content_blocks.unwrap_err())
            wire_blocks = content_blocks.unwrap()
            has_text = any(block.type == "text" and block.text for block in wire_blocks)
            if not has_text:
                pure_tool_turn = bool(
                    (message.metadata or {}).get("function_call_item_ids")
                )
                if (
                    message.tool_calls and not pure_tool_turn
                ) or not message.tool_calls:
                    wire_blocks = [ClaudeContent(type="text", text="...")]
                else:
                    wire_blocks = []
            blocks.extend(wire_blocks)
            for tool_call in message.tool_calls or []:
                blocks.append(_tool_call_to_block(tool_call))
            return Ok(
                ClaudeMessage(role="assistant", content=self._collapse_content(blocks))
            )
        if message.role == "user":
            if isinstance(message.content, list) and any(
                isinstance(part, ImageBase64Part) for part in message.content
            ):
                return Ok(ClaudeMessage(role="user", content=[]))
            user_blocks = self._content_to_blocks(message.content, context)
            if user_blocks.is_err():
                return Err(user_blocks.unwrap_err())
            return Ok(
                ClaudeMessage(
                    role="user", content=self._collapse_content(user_blocks.unwrap())
                )
            )
        record_loss(
            context,
            field="messages",
            target=_TARGET,
            reason=f"unknown_role_{message.role}_dropped",
        )
        return Ok(
            ClaudeMessage(role="user", content=[ClaudeContent(type="text", text="")])
        )

    def _content_to_blocks(
        self, content: str | list[ContentPart], context: ConversionContext
    ) -> Result[list[ClaudeContent], RelayError]:
        """Convert canonical content into a Claude block list."""
        if isinstance(content, str):
            return Ok([ClaudeContent(type="text", text=content)])
        blocks: list[ClaudeContent] = []
        for part in content:
            if isinstance(part, TextPart):
                blocks.append(ClaudeContent(type="text", text=part.text))
            elif isinstance(part, ImageBase64Part):
                blocks.append(
                    ClaudeContent(
                        type="image",
                        image_source={
                            "type": "base64",
                            "media_type": part.media_type,
                            "data": part.data,
                        },
                    )
                )
            elif isinstance(part, ImageUrlPart):
                resolved = self._resolve_image(part, context)
                if resolved.is_err():
                    return Err(resolved.unwrap_err())
                blocks.append(
                    ClaudeContent(
                        type="image",
                        image_source={
                            "type": "base64",
                            "media_type": resolved.unwrap()[0],
                            "data": resolved.unwrap()[1],
                        },
                    )
                )
            else:
                record_loss(
                    context,
                    field="message.content",
                    target=_TARGET,
                    reason="unknown_content_part",
                )
        if not blocks:
            blocks.append(ClaudeContent(type="text", text=""))
        return Ok(blocks)

    @staticmethod
    def _collapse_content(
        blocks: list[ClaudeContent],
    ) -> str | list[ClaudeContent]:
        """Collapse a single text block into plain string content.

        The Claude wire protocol accepts either a plain string or a block
        list for message content; relaykit emits plain strings for
        single-text messages.
        """
        if len(blocks) == 1 and blocks[0].type == "text" and blocks[0].text is not None:
            return blocks[0].text
        return blocks

    @staticmethod
    def _resolve_image(
        part: ImageUrlPart, context: ConversionContext
    ) -> Result[tuple[str, str], RelayError]:
        """Resolve a URL or data-URI image for Claude.

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

    @staticmethod
    def _text_from_content(content: str | list[ContentPart]) -> str:
        """Extract plain text from canonical content."""
        if isinstance(content, str):
            return content
        return "".join(part.text for part in content if isinstance(part, TextPart))

    @staticmethod
    def _tool_from_ir(tool: ToolDefinition) -> dict[str, Any]:
        """Serialize a canonical ``ToolDefinition`` as a Claude wire tool."""
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }

    def _thinking_from_ir(
        self, request: RelayRequest, context: ConversionContext
    ) -> dict[str, Any] | None:
        """Rebuild the Claude ``thinking`` dict from canonical thinking."""
        thinking = request.thinking
        if thinking is None:
            return None
        if thinking.effort is not None:
            record_loss(
                context,
                field="thinking",
                target=_TARGET,
                reason="effort_not_supported",
            )
            return None
        if thinking.suppress:
            return {"type": "disabled"}
        return {"type": "enabled", "budget_tokens": thinking.budget_tokens}

    @staticmethod
    def _usage_from_wire(usage: ClaudeUsage | None) -> RelayUsage | None:
        """Map a wire ``ClaudeUsage`` into canonical ``RelayUsage``.

        Mirrors relaykit's ``buildOpenAIStyleUsageFromClaudeUsage``: the
        prompt count includes cache reads and cache creations, and the
        chat ``input_tokens`` is stamped with that total.
        """
        if usage is None:
            return None
        prompt = (
            usage.input_tokens
            + usage.cache_read_input_tokens
            + usage.cache_creation_input_tokens
        )
        return RelayUsage(
            prompt_tokens=prompt,
            completion_tokens=usage.output_tokens,
            cache_read_tokens=usage.cache_read_input_tokens,
            cache_creation_tokens=usage.cache_creation_input_tokens,
            input_tokens=prompt,
        )

    @staticmethod
    def _usage_to_wire(usage: RelayUsage | None) -> ClaudeUsage | None:
        """Serialize canonical ``RelayUsage`` into a ``ClaudeUsage``."""
        if usage is None:
            return None
        return ClaudeUsage(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            cache_read_input_tokens=usage.cache_read_tokens,
            cache_creation_input_tokens=usage.cache_creation_tokens,
        )

    @staticmethod
    def _stop_reason_from_ir(
        finish_reason: str | None, context: ConversionContext
    ) -> str | None:
        """Map a canonical finish reason back to a Claude stop reason."""
        if finish_reason is None:
            return None
        if finish_reason in {"function_call", "content_filter"}:
            record_loss(
                context,
                field="finish_reason",
                target=_TARGET,
                reason=f"{finish_reason}_adapted",
            )
        elif finish_reason not in FINISH_REASON_TO_WIRE:
            record_loss(
                context,
                field="finish_reason",
                target=_TARGET,
                reason="finish_reason_adapted",
            )
        return finish_reason_to_wire(finish_reason, _TARGET)
