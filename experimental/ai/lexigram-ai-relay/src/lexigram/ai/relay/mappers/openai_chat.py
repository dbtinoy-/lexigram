"""OpenAI Chat Completions request and response mapper.

Converts the OpenAI Chat Completions wire DTOs
(:class:`OpenAIChatRequest` / :class:`OpenAIChatResponse`) into the
canonical relay IR and back.  Stream conversion is handled by the shared
stream lifecycle task and reports ``unsupported_feature`` until then.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate, unsupported_feature, unsupported_format
from lexigram.ai.relay.mappers.base import new_uuid, record_loss
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
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
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import dumps_str

__all__ = ["OpenAIChatMapper"]

_TARGET = RelayFormat.OPENAI_CHAT
_MESSAGE_METADATA_INTERNAL = {"function_call_item_ids"}


def _tool_calls_to_ir(
    wire: list[dict[str, Any]] | None,
) -> list[ToolCall] | None:
    """Convert wire tool-call dicts into canonical ``ToolCall`` objects."""
    if not wire:
        return None
    tool_calls: list[ToolCall] = []
    for item in wire:
        function = item.get("function")
        name = function.get("name", "") if isinstance(function, dict) else ""
        arguments = function.get("arguments", {}) if isinstance(function, dict) else {}
        tool_calls.append(
            ToolCall(
                id=str(item.get("id", "")),
                type=str(item.get("type", "function")),
                function=FunctionCall(name=str(name), arguments=arguments),
            )
        )
    return tool_calls


def _tool_call_to_wire(tool_call: ToolCall) -> dict[str, Any]:
    """Serialize one canonical ``ToolCall`` as a wire dict."""
    arguments: Any = tool_call.function.arguments if tool_call.function else {}
    if isinstance(arguments, dict):
        arguments = dumps_str(arguments)
    elif not isinstance(arguments, str):
        arguments = ""
    return {
        "id": tool_call.id,
        "type": "function",
        "function": {
            "name": tool_call.function.name if tool_call.function else "",
            "arguments": arguments,
        },
    }


def _extract_text(
    content: str | list[dict[str, Any]] | None,
    context: ConversionContext,
    *,
    field: str,
) -> str:
    """Extract the text portion of wire content for flattened fields."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    texts: list[str] = []
    lost = False
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            texts.append(str(part.get("text", "")))
        else:
            lost = True
    if lost:
        record_loss(
            context, field=field, target=_TARGET, reason="non_text_parts_dropped"
        )
    return "".join(texts)


class OpenAIChatMapper:
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

    # -- helpers -------------------------------------------------------------

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
