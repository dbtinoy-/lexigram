"""Request-direction conversion for the Claude mapper."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import (
    missing_required_option,
    translate,
    unsupported_format,
)
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.ai.relay.mappers.claude.utils import (
    _TARGET,
    _tool_call_from_block,
)
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, ToolCall
from lexigram.contracts.ai.multimodal import (
    ContentPart,
    ImageBase64Part,
    ImageUrlPart,
    TextPart,
)
from lexigram.contracts.ai.relay.dto import ClaudeContent, ClaudeMessage, ClaudeRequest
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.ai.thinking import ThinkingConfig
from lexigram.contracts.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.relay.mappers.claude import ClaudeMapper


class RequestMixin:
    """Request conversion: wire ``ClaudeRequest`` to IR and back."""

    def request_to_ir(
        self: ClaudeMapper, payload: Any, *, context: ConversionContext
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
        self: ClaudeMapper, request: RelayRequest, *, context: ConversionContext
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

    def _message_to_ir(
        self: ClaudeMapper,
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

    def _assistant_to_ir(self: ClaudeMapper, message: ClaudeMessage) -> ChatMessage:
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
        self: ClaudeMapper,
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
