"""OpenAI Chat Completions request and response mapper.

Converts the OpenAI Chat Completions wire DTOs
(:class:`OpenAIChatRequest` / :class:`OpenAIChatResponse`) into the
canonical relay IR and back.  Stream conversion is handled by the shared
stream lifecycle task and reports ``unsupported_feature`` until then.

The mapper class composes direction mixins: :class:`WireToIRMixin`
(parsing) and :class:`IRToWireMixin` (building), with shared free
helpers in :mod:`_helpers`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate, unsupported_feature, unsupported_format
from lexigram.ai.relay.mappers.base import new_uuid, record_loss
from lexigram.ai.relay.mappers.openai_chat._helpers import (
    _TARGET,
    _extract_text,
    _tool_call_to_wire,
    _tool_calls_to_ir,
)
from lexigram.ai.relay.mappers.openai_chat.ir_to_wire import IRToWireMixin
from lexigram.ai.relay.mappers.openai_chat.wire_to_ir import WireToIRMixin
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, ToolCall
from lexigram.contracts.ai.relay.dto import (
    OpenAIChatChoice,
    OpenAIChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
)
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    StreamDelta,
    StreamState,
    normalize_finish_reason,
)
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["OpenAIChatMapper"]


class OpenAIChatMapper(WireToIRMixin, IRToWireMixin):
    """Bidirectional OpenAI Chat Completions converter.

    Attributes:
        format: The wire format this mapper handles.
    """

    format = _TARGET

    def request_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayRequest, RelayError]:
        """Convert an ``OpenAIChatRequest`` into canonical ``RelayRequest``.

        Args:
            payload: A wire request DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on malformed payload.
        """
        if not isinstance(payload, OpenAIChatRequest):
            return Err(
                unsupported_format(
                    f"expected OpenAIChatRequest, got {type(payload).__name__}"
                )
            )
        system_parts: list[str] = []
        messages: list[ChatMessage] = []
        for position, message in enumerate(payload.messages):
            if message.role == "system":
                text = _extract_text(
                    message.content,
                    context,
                    field=f"system_message[{position}].content",
                )
                system_parts.append(text)
                if position > 0:
                    record_loss(
                        context,
                        field="system_message",
                        target=_TARGET,
                        reason="system_message_reordered",
                    )
                continue
            content: str | list[Any]
            if isinstance(message.content, list):
                content = self._wire_parts_to_ir(message.content, context)
            elif message.content is None:
                content = ""
            else:
                content = message.content
            tool_calls = _tool_calls_to_ir(message.tool_calls)
            messages.append(
                ChatMessage(
                    role=message.role,
                    content=cast("str | list[Any]", content),
                    name=message.name,
                    tool_call_id=message.tool_call_id,
                    tool_calls=tool_calls,
                    metadata=dict(message.passthrough) or None,
                )
            )
        max_tokens = self._normalize_max_tokens(payload, context)
        stop_sequences = (
            [payload.stop]
            if isinstance(payload.stop, str)
            else (
                [s for s in payload.stop if isinstance(s, str)] if payload.stop else []
            )
        )
        include_usage = False
        if isinstance(payload.stream_options, dict):
            include_usage = bool(payload.stream_options.get("include_usage", False))
        thinking: ThinkingConfig | None = None
        reasoning = payload.reasoning
        if isinstance(reasoning, dict):
            thinking = ThinkingConfig(effort=reasoning.get("effort"))
        metadata: dict[str, Any] = {}
        if reasoning is not None:
            metadata["reasoning"] = reasoning
        if payload.stream_options is not None:
            metadata["stream_options"] = payload.stream_options
        if payload.service_tier is not None:
            metadata["service_tier"] = payload.service_tier
        return Ok(
            RelayRequest(
                model=context.normalize_model(payload.model),
                messages=messages,
                system="\n".join(system_parts) if system_parts else None,
                tools=self._tools_to_ir(payload.tools, context),
                tool_choice=payload.tool_choice,
                temperature=payload.temperature,
                top_p=payload.top_p,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                response_format=payload.response_format,
                stream=payload.stream,
                include_usage=include_usage,
                parallel_tool_calls=payload.parallel_tool_calls,
                thinking=thinking,
                metadata=metadata,
                passthrough=dict(payload.passthrough),
            )
        )

    def ir_to_request(
        self, request: RelayRequest, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayRequest`` into an ``OpenAIChatRequest``.

        Args:
            request: Canonical request IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on failure.
        """
        try:
            messages: list[OpenAIChatMessage] = []
            if request.system:
                messages.append(
                    OpenAIChatMessage(role="system", content=request.system)
                )
            for message in request.messages:
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
                messages.append(self._message_from_ir(prepared, context))
            stream_options = self._stream_options_from_ir(request)
            reasoning = self._reasoning_from_ir(request, context)
            if request.metadata.get("max_tokens_kind") == "max_completion_tokens":
                max_completion_tokens: int | None = request.max_tokens
                max_tokens: int | None = None
            else:
                max_completion_tokens = None
                max_tokens = request.max_tokens
            return Ok(
                OpenAIChatRequest(
                    model=context.resolve_model(request.model),
                    messages=messages,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=max_tokens,
                    max_completion_tokens=max_completion_tokens,
                    stream=request.stream,
                    stream_options=stream_options,
                    tools=(
                        [self._tool_from_ir(tool) for tool in request.tools]
                        if request.tools
                        else None
                    ),
                    tool_choice=request.tool_choice,
                    parallel_tool_calls=request.parallel_tool_calls,
                    stop=self._stop_from_ir(request.stop_sequences),
                    response_format=request.response_format,
                    reasoning=reasoning,
                    service_tier=request.metadata.get("service_tier"),
                    passthrough={
                        **request.passthrough,
                        **{
                            key: value
                            for key, value in request.metadata.items()
                            if key
                            not in {
                                "service_tier",
                                "reasoning",
                                "stream_options",
                                "generation_config",
                                "safety_settings",
                                "tool_config",
                                "max_tokens_kind",
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
        """Convert an ``OpenAIChatResponse`` into canonical ``RelayResponse``.

        Args:
            payload: A wire response DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on malformed payload.
        """
        if not isinstance(payload, OpenAIChatResponse):
            return Err(
                unsupported_format(
                    f"expected OpenAIChatResponse, got {type(payload).__name__}"
                )
            )
        try:
            passthrough = dict(payload.passthrough)
            if payload.system_fingerprint is not None:
                passthrough["system_fingerprint"] = payload.system_fingerprint
            choice = payload.choices[0] if payload.choices else None
            if len(payload.choices) > 1:
                record_loss(
                    context,
                    field="choices",
                    target=_TARGET,
                    reason="multiple_choices_collapsed",
                )
            message = choice.message if choice is not None else None
            content = ""
            tool_calls: list[ToolCall] = []
            thinking: ThinkingResult | None = None
            if message is not None:
                content = self._message_text_to_ir(message, context)
                tool_calls = list(_tool_calls_to_ir(message.tool_calls) or [])
                thinking = self._reasoning_from_message(message, payload.usage)
            return Ok(
                RelayResponse(
                    model=payload.model,
                    id=payload.id,
                    created=payload.created,
                    content=content,
                    thinking=thinking,
                    tool_calls=tool_calls,
                    finish_reason=normalize_finish_reason(
                        choice.finish_reason if choice is not None else None
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
        """Convert canonical ``RelayResponse`` into an ``OpenAIChatResponse``.

        Args:
            response: Canonical response IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on failure.
        """
        try:
            passthrough = dict(response.passthrough)
            system_fingerprint = passthrough.pop("system_fingerprint", None)
            content: str | None = response.content or None
            tool_calls: list[dict[str, Any]] = []
            for tool in response.tool_calls:
                wire = _tool_call_to_wire(tool)
                if not wire["id"]:
                    wire["id"] = f"call_{new_uuid()}"
                tool_calls.append(wire)
            message = OpenAIChatMessage(
                role="assistant",
                content=content,
                tool_calls=tool_calls or None,
            )
            finish_reason = (
                "tool_calls" if response.tool_calls else response.finish_reason
            )
            return Ok(
                OpenAIChatResponse(
                    id=response.id or f"chatcmpl-{new_uuid()}",
                    model=context.resolve_model(response.model),
                    created=response.created or 0,
                    choices=[
                        OpenAIChatChoice(
                            index=0,
                            message=message,
                            finish_reason=finish_reason,
                        )
                    ],
                    usage=self._usage_to_wire(response.usage),
                    system_fingerprint=(system_fingerprint),
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
            unsupported_feature("openai_chat stream conversion is not implemented yet")
        )

    def delta_to_stream(
        self, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature("openai_chat stream conversion is not implemented yet")
        )
