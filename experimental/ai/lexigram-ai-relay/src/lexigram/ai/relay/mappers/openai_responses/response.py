"""Response-direction conversion for the OpenAI Responses mapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate, unsupported_format
from lexigram.ai.relay.finish_reasons import (
    responses_status_from_finish,
)
from lexigram.ai.relay.mappers.base import new_uuid, record_loss
from lexigram.ai.relay.mappers.openai_responses.utils import (
    _TARGET,
    _arguments_to_wire,
    _incomplete_for_finish,
    _parse_arguments,
)
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import TextPart
from lexigram.contracts.ai.relay.dto import (
    ResponsesIncompleteDetails,
    ResponsesItem,
    ResponsesResponse,
    ResponsesUsage,
)
from lexigram.contracts.ai.relay.ir import RelayResponse
from lexigram.contracts.ai.relay.types import RelayUsage
from lexigram.contracts.ai.thinking import ThinkingResult
from lexigram.contracts.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.relay.mappers.openai_responses import OpenAIResponsesMapper


class ResponseMixin:
    """Response conversion: wire ``ResponsesResponse`` to IR and back."""

    def response_to_ir(
        self: OpenAIResponsesMapper,
        payload: Any,
        *,
        context: ConversionContext,
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
        self: OpenAIResponsesMapper,
        response: RelayResponse,
        *,
        context: ConversionContext,
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
