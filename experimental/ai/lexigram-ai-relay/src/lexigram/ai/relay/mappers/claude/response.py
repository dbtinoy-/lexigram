"""Response-direction conversion for the Claude mapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate, unsupported_format
from lexigram.ai.relay.finish_reasons import (
    FINISH_REASON_TO_WIRE,
    finish_reason_to_wire,
)
from lexigram.ai.relay.mappers.base import new_uuid, record_loss
from lexigram.ai.relay.mappers.claude.utils import (
    _TARGET,
    _tool_call_from_block,
    _tool_call_to_block,
)
from lexigram.ai.relay.media import resolve_media
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, ToolCall
from lexigram.contracts.ai.multimodal import (
    ContentPart,
    ImageBase64Part,
    ImageUrlPart,
    TextPart,
)
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeMessage,
    ClaudeResponse,
    ClaudeUsage,
)
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    normalize_finish_reason,
)
from lexigram.contracts.ai.relay.types import RelayUsage
from lexigram.contracts.ai.thinking import ThinkingResult
from lexigram.contracts.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.relay.mappers.claude import ClaudeMapper


class ResponseMixin:
    """Response conversion: wire ``ClaudeResponse`` to IR and back."""

    def response_to_ir(
        self: ClaudeMapper, payload: Any, *, context: ConversionContext
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
        self: ClaudeMapper, response: RelayResponse, *, context: ConversionContext
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

    def _message_from_ir(
        self: ClaudeMapper, message: ChatMessage, context: ConversionContext
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
        self: ClaudeMapper, content: str | list[ContentPart], context: ConversionContext
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
        self: ClaudeMapper, request: RelayRequest, context: ConversionContext
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
