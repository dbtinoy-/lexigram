"""Google Gemini ``generateContent`` request and response mapper.

Converts the Gemini wire DTOs (:class:`GeminiRequest` /
:class:`GeminiResponse`) into the canonical relay IR and back.  Stream
conversion is handled by the shared stream lifecycle task and reports
``unsupported_feature`` until then.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import (
    media_resolution_required,
    translate,
    unsupported_feature,
    unsupported_format,
)
from lexigram.ai.relay.mappers.base import record_loss
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
    GeminiCandidate,
    GeminiContent,
    GeminiGroundingMetadata,
    GeminiPart,
    GeminiPromptFeedback,
    GeminiRequest,
    GeminiResponse,
    GeminiSafetyRating,
    GeminiUsageMetadata,
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
from lexigram.serialization import dumps_str, loads_str

__all__ = ["GeminiMapper"]

_TARGET = RelayFormat.GEMINI

_SAFETY_CATEGORIES = (
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
    "HARM_CATEGORY_CIVIC_INTEGRITY",
)

_MIME_KEY = "mimeType"


def _tool_call_from_part(part: GeminiPart) -> ToolCall:
    """Convert a Gemini ``functionCall`` part into a canonical ``ToolCall``."""
    call = part.function_call or {}
    name = str(call.get("name", ""))
    args = call.get("args")
    return ToolCall(
        id=name,
        type="custom",
        function=FunctionCall(
            name=name,
            arguments=args if isinstance(args, dict) else {},
        ),
    )


def _tool_call_to_part(tool_call: ToolCall) -> GeminiPart:
    """Serialize a canonical ``ToolCall`` as a Gemini ``functionCall`` part."""
    arguments: Any = tool_call.function.arguments if tool_call.function else {}
    if isinstance(arguments, str):
        try:
            arguments = loads_str(arguments)
        except ValueError:
            arguments = {}
    elif not isinstance(arguments, dict):
        arguments = {}
    return GeminiPart(
        function_call={
            "name": tool_call.function.name if tool_call.function else "",
            "args": arguments,
        }
    )


class GeminiMapper:
    """Bidirectional Google Gemini ``generateContent`` converter.

    Attributes:
        format: The wire format this mapper handles.
    """

    format = _TARGET

    def request_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayRequest, RelayError]:
        """Convert a ``GeminiRequest`` into canonical ``RelayRequest``.

        Args:
            payload: A wire request DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on malformed payload.
        """
        if not isinstance(payload, GeminiRequest):
            return Err(
                unsupported_format(
                    f"expected GeminiRequest, got {type(payload).__name__}"
                )
            )
        try:
            messages = [
                chat_message
                for index, content in enumerate(payload.contents)
                for chat_message in self._content_to_ir(content, context, index)
            ]
            metadata: dict[str, Any] = {}
            if payload.safety_settings is not None:
                metadata["safety_settings"] = [
                    dict(item) for item in payload.safety_settings
                ]
            if payload.tool_config is not None:
                metadata["tool_config"] = dict(payload.tool_config)
            generation_config = dict(payload.generation_config)
            if generation_config:
                metadata["generation_config"] = generation_config
            return Ok(
                RelayRequest(
                    model=str(payload.passthrough.get("model", "")).strip(),
                    messages=messages,
                    system=self._system_to_ir(payload.system_instruction),
                    tools=self._tools_to_ir(payload.tools),
                    temperature=_config_number(generation_config, "temperature"),
                    top_p=_config_number(generation_config, "topP"),
                    top_k=_config_int(generation_config, "topK"),
                    max_tokens=_config_int(generation_config, "maxOutputTokens"),
                    stop_sequences=[
                        str(item)
                        for item in generation_config.get("stopSequences", [])
                        if isinstance(item, str)
                    ],
                    response_format=self._response_format_to_ir(generation_config),
                    thinking=self._thinking_to_ir(generation_config),
                    metadata=metadata,
                    passthrough=dict(payload.passthrough),
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="request_to_ir"))

    def ir_to_request(
        self, request: RelayRequest, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayRequest`` into a ``GeminiRequest``.

        Args:
            request: Canonical request IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(request) on success, Err(relay_error) on failure.
        """
        try:
            system_parts: list[str] = []
            contents: list[GeminiContent] = []
            for message in request.messages:
                if message.role == "system":
                    system_parts.append(self._text_from_content(message.content))
                    continue
                content = self._content_from_ir(message, request.model, context)
                if content.is_err():
                    return content
                contents.append(content.unwrap())
            if request.system:
                system_parts.append(request.system)
            return Ok(
                GeminiRequest(
                    contents=contents,
                    system_instruction=(
                        {"parts": [{"text": text} for text in system_parts]}
                        if system_parts
                        else None
                    ),
                    generation_config=self._generation_config_from_ir(request, context),
                    safety_settings=self._safety_settings_from_ir(request, context),
                    tools=self._tools_from_ir(request.tools),
                    tool_config=self._tool_config_from_ir(request),
                    passthrough=self._request_passthrough(request),
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="ir_to_request"))

    def response_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayResponse, RelayError]:
        """Convert a ``GeminiResponse`` into canonical ``RelayResponse``.

        Args:
            payload: A wire response DTO.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on malformed payload.
        """
        if not isinstance(payload, GeminiResponse):
            return Err(
                unsupported_format(
                    f"expected GeminiResponse, got {type(payload).__name__}"
                )
            )
        try:
            candidates = payload.candidates or []
            if len(candidates) > 1:
                record_loss(
                    context,
                    field="candidates",
                    target=_TARGET,
                    reason="multiple_candidates_collapsed",
                )
            candidate = candidates[0] if candidates else None
            passthrough: dict[str, Any] = dict(payload.passthrough)
            if payload.model_version is not None:
                passthrough["model_version"] = payload.model_version
            if payload.create_time is not None:
                passthrough["create_time"] = payload.create_time
            if payload.prompt_feedback is not None:
                passthrough["prompt_feedback"] = payload.prompt_feedback.to_dict()
            content = ""
            thinking: ThinkingResult | None = None
            tool_calls: list[ToolCall] = []
            if candidate is not None and candidate.content is not None:
                text_parts: list[str] = []
                think_parts: list[str] = []
                think_signature: str | None = None
                for part in candidate.content.parts:
                    if part.thought:
                        think_parts.append(part.text or "")
                        think_signature = part.thought_signature
                    elif part.text is not None:
                        text_parts.append(part.text)
                    elif part.function_call is not None:
                        tool_calls.append(_tool_call_from_part(part))
                    elif (
                        part.inline_data is not None
                        or part.function_response is not None
                    ):
                        record_loss(
                            context,
                            field="content.part",
                            target=_TARGET,
                            reason="unrepresentable_part_dropped",
                        )
                content = "".join(text_parts)
                if think_parts:
                    thinking = ThinkingResult(
                        content="".join(think_parts),
                        signature=think_signature,
                        tokens=self._thought_tokens(payload),
                    )
                self._preserve_candidate_metadata(candidate, passthrough)
            return Ok(
                RelayResponse(
                    model=payload.model_version or "",
                    id=payload.response_id,
                    content=content,
                    thinking=thinking,
                    tool_calls=tool_calls,
                    finish_reason=normalize_finish_reason(
                        candidate.finish_reason if candidate else None
                    ),
                    usage=self._usage_from_wire(payload.usage_metadata),
                    passthrough=passthrough,
                )
            )
        except (RelayError, ValueError, TypeError, KeyError) as exc:
            return Err(translate(exc, detail="response_to_ir"))

    def ir_to_response(
        self, response: RelayResponse, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert canonical ``RelayResponse`` into a ``GeminiResponse``.

        Args:
            response: Canonical response IR.
            context: Per-conversion context with loss sink.

        Returns:
            Ok(response) on success, Err(relay_error) on failure.
        """
        try:
            passthrough = dict(response.passthrough)
            model_version = passthrough.pop("model_version", None)
            prompt_feedback = passthrough.pop("prompt_feedback", None)
            create_time = passthrough.pop("create_time", None)
            safety_ratings = passthrough.pop("safety_ratings", None)
            grounding_metadata = passthrough.pop("grounding_metadata", None)
            citation_metadata = passthrough.pop("citation_metadata", None)
            token_count = passthrough.pop("token_count", None)
            avg_logprobs = passthrough.pop("avg_logprobs", None)
            parts: list[GeminiPart] = []
            if response.thinking is not None and response.thinking.content:
                parts.append(
                    GeminiPart(
                        text=response.thinking.content,
                        thought=True,
                        thought_signature=response.thinking.signature,
                    )
                )
            if response.content:
                parts.append(GeminiPart(text=response.content))
            for tool_call in response.tool_calls:
                parts.append(_tool_call_to_part(tool_call))
            candidate = GeminiCandidate(
                content=GeminiContent(role="model", parts=parts),
                finish_reason=self._finish_reason_from_ir(
                    response.finish_reason, context
                ),
                safety_ratings=self._safety_ratings_from_passthrough(safety_ratings),
                grounding_metadata=self._grounding_from_passthrough(grounding_metadata),
                citation_metadata=(
                    citation_metadata if isinstance(citation_metadata, dict) else None
                ),
                token_count=token_count if isinstance(token_count, int) else None,
                avg_logprobs=(
                    avg_logprobs if isinstance(avg_logprobs, (int, float)) else None
                ),
                passthrough=dict(passthrough),
            )
            return Ok(
                GeminiResponse(
                    candidates=[candidate],
                    prompt_feedback=self._prompt_feedback_from_passthrough(
                        prompt_feedback
                    ),
                    usage_metadata=self._usage_to_wire(response.usage),
                    model_version=model_version
                    if isinstance(model_version, str)
                    else None,
                    create_time=create_time if isinstance(create_time, str) else None,
                    response_id=response.id,
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
            unsupported_feature("gemini stream conversion is not implemented yet")
        )

    def delta_to_stream(
        self, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        """Stream conversion is deferred to the shared stream lifecycle task."""
        return Err(
            unsupported_feature("gemini stream conversion is not implemented yet")
        )

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _system_to_ir(
        system_instruction: dict[str, Any] | None,
    ) -> str | None:
        """Extract system text from a Gemini ``systemInstruction`` dict."""
        if not isinstance(system_instruction, dict):
            return None
        parts = system_instruction.get("parts")
        if not isinstance(parts, list):
            return None
        texts: list[str] = []
        for part in parts:
            if isinstance(part, dict) and part.get("text") is not None:
                texts.append(str(part["text"]))
        return "\n".join(texts)

    @staticmethod
    def _tools_to_ir(tools: list[dict[str, Any]] | None) -> list[ToolDefinition]:
        """Convert Gemini wire tools into canonical ``ToolDefinition`` objects."""
        definitions: list[ToolDefinition] = []
        for tool in tools or []:
            if not isinstance(tool, dict):
                continue
            declarations = tool.get("functionDeclarations")
            if not isinstance(declarations, list):
                continue
            for declaration in declarations:
                if not isinstance(declaration, dict):
                    continue
                parameters = declaration.get("parameters")
                definitions.append(
                    ToolDefinition(
                        name=str(declaration.get("name", "")),
                        description=str(declaration.get("description", "")),
                        parameters=parameters if isinstance(parameters, dict) else {},
                    )
                )
        return definitions

    def _content_to_ir(
        self, content: GeminiContent, context: ConversionContext, index: int
    ) -> list[ChatMessage]:
        """Convert one Gemini content turn into canonical messages."""
        if content.role == "model":
            return [self._assistant_to_ir(content, context)]
        if content.role == "user":
            return self._user_to_ir(content, context, index)
        if content.role == "function":
            return self._function_to_ir(content, context, index)
        record_loss(
            context,
            field=f"contents[{index}].role",
            target=_TARGET,
            reason="unknown_role_dropped",
        )
        return []

    def _assistant_to_ir(
        self, content: GeminiContent, context: ConversionContext
    ) -> ChatMessage:
        """Convert a model content turn, separating thinking/tool parts."""
        text_parts: list[str] = []
        thinking_blocks: list[dict[str, Any]] = []
        tool_calls: list[ToolCall] = []
        for part in content.parts:
            if part.thought:
                thinking_blocks.append(
                    {
                        "thought": True,
                        "text": part.text or "",
                        "thoughtSignature": part.thought_signature or "",
                    }
                )
            elif part.text is not None:
                text_parts.append(part.text)
            elif part.function_call is not None:
                tool_calls.append(_tool_call_from_part(part))
            else:
                record_loss(
                    context,
                    field="content.part",
                    target=_TARGET,
                    reason="unrepresentable_part_dropped",
                )
        return ChatMessage(
            role="assistant",
            content="".join(text_parts),
            tool_calls=tool_calls or None,
            thinking_blocks=thinking_blocks or None,
        )

    def _user_to_ir(
        self, content: GeminiContent, context: ConversionContext, index: int
    ) -> list[ChatMessage]:
        """Convert a user content turn into canonical content parts."""
        parts: list[ContentPart] = []
        for part in content.parts:
            if part.text is not None:
                parts.append(TextPart(text=part.text))
            elif part.inline_data is not None:
                inline = part.inline_data
                parts.append(
                    ImageBase64Part(
                        data=str(inline.get("data", "")),
                        media_type=str(inline.get(_MIME_KEY, "")),
                    )
                )
            else:
                record_loss(
                    context,
                    field=f"contents[{index}].part",
                    target=_TARGET,
                    reason="unrepresentable_part_dropped",
                )
        if not parts:
            record_loss(
                context,
                field=f"contents[{index}]",
                target=_TARGET,
                reason="empty_message_dropped",
            )
            return []
        return [
            ChatMessage(
                role="user",
                content=(
                    parts[0].text
                    if len(parts) == 1 and isinstance(parts[0], TextPart)
                    else list(parts)
                ),
            )
        ]

    def _function_to_ir(
        self, content: GeminiContent, context: ConversionContext, index: int
    ) -> list[ChatMessage]:
        """Convert a function content turn into canonical tool messages."""
        messages: list[ChatMessage] = []
        for part in content.parts:
            if part.function_response is not None:
                messages.append(self._function_response_to_ir(part.function_response))
            else:
                record_loss(
                    context,
                    field=f"contents[{index}].part",
                    target=_TARGET,
                    reason="unrepresentable_part_dropped",
                )
        return messages

    @staticmethod
    def _function_response_to_ir(response: dict[str, Any]) -> ChatMessage:
        """Convert a ``functionResponse`` dict into a canonical tool message."""
        name = str(response.get("name", ""))
        payload = response.get("response")
        if isinstance(payload, str):
            text = payload
        else:
            text = dumps_str(payload) if payload is not None else ""
        return ChatMessage(role="tool", content=text, tool_call_id=name)

    @staticmethod
    def _response_format_to_ir(
        generation_config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Derive a canonical response format from the generation config."""
        mime = generation_config.get("responseMimeType")
        if not isinstance(mime, str):
            return None
        if mime == "application/json":
            return {"type": "json_object"}
        return None

    def _thinking_to_ir(
        self, generation_config: dict[str, Any]
    ) -> ThinkingConfig | None:
        """Extract canonical thinking config from ``thinkingConfig``."""
        config = generation_config.get("thinkingConfig")
        if not isinstance(config, dict):
            return None
        level = config.get("thinkingLevel")
        budget = config.get("thinkingBudget")
        if isinstance(level, str) and level:
            return ThinkingConfig(level=level)
        if isinstance(budget, int):
            return ThinkingConfig(budget_tokens=budget)
        return None

    def _content_from_ir(
        self, message: ChatMessage, model: str, context: ConversionContext
    ) -> Result[GeminiContent, RelayError]:
        """Convert one canonical message into a Gemini content turn."""
        if message.role == "tool":
            response: Any = message.content
            if isinstance(response, list):
                response = self._text_from_content(message.content)
            if isinstance(response, str):
                try:
                    response = loads_str(response)
                except ValueError:
                    pass
            return Ok(
                GeminiContent(
                    role="function",
                    parts=[
                        GeminiPart(
                            function_response={
                                "name": message.tool_call_id or "",
                                "response": response,
                            }
                        )
                    ],
                )
            )
        if message.role == "assistant":
            parts = self._assistant_parts_from_ir(message, model, context)
            if parts.is_err():
                return Err(parts.unwrap_err())
            return Ok(GeminiContent(role="model", parts=parts.unwrap()))
        if message.role == "user":
            parts = self._user_parts_from_ir(message.content, context)
            if parts.is_err():
                return Err(parts.unwrap_err())
            return Ok(GeminiContent(role="user", parts=parts.unwrap()))
        record_loss(
            context,
            field="messages",
            target=_TARGET,
            reason=f"unknown_role_{message.role}_dropped",
        )
        return Ok(GeminiContent(role="user", parts=[GeminiPart(text="")]))

    def _assistant_parts_from_ir(
        self, message: ChatMessage, model: str, context: ConversionContext
    ) -> Result[list[GeminiPart], RelayError]:
        """Rebuild Gemini model parts from an assistant message."""
        parts: list[GeminiPart] = []
        bypass = (
            context.options.gemini.thought_signature_bypass
            and context.preserve_thinking_suffix(model)
        )
        for block in message.thinking_blocks or []:
            if not isinstance(block, dict):
                continue
            signature = block.get("thoughtSignature")
            if bypass:
                record_loss(
                    context,
                    field="thinking_signature",
                    target=_TARGET,
                    reason="thought_signature_bypassed",
                )
                signature = None
            parts.append(
                GeminiPart(
                    text=str(block.get("text", "")),
                    thought=True,
                    thought_signature=str(signature) if signature else None,
                )
            )
        content_parts = self._user_parts_from_ir(message.content, context)
        if content_parts.is_err():
            return Err(content_parts.unwrap_err())
        parts.extend(content_parts.unwrap())
        for tool_call in message.tool_calls or []:
            parts.append(_tool_call_to_part(tool_call))
        return Ok(parts)

    def _user_parts_from_ir(
        self, content: str | list[ContentPart], context: ConversionContext
    ) -> Result[list[GeminiPart], RelayError]:
        """Convert canonical content into Gemini parts."""
        if isinstance(content, str):
            return Ok([GeminiPart(text=content)] if content else [])
        parts: list[GeminiPart] = []
        for part in content:
            if isinstance(part, TextPart):
                parts.append(GeminiPart(text=part.text))
            elif isinstance(part, ImageBase64Part):
                parts.append(
                    GeminiPart(
                        inline_data={
                            _MIME_KEY: part.media_type,
                            "data": part.data,
                        }
                    )
                )
            elif isinstance(part, ImageUrlPart):
                resolved = self._resolve_image(part, context)
                if resolved.is_err():
                    return Err(resolved.unwrap_err())
                media_type, data = resolved.unwrap()
                parts.append(
                    GeminiPart(inline_data={_MIME_KEY: media_type, "data": data})
                )
            else:
                record_loss(
                    context,
                    field="message.content",
                    target=_TARGET,
                    reason="unknown_content_part",
                )
        return Ok(parts)

    @staticmethod
    def _resolve_image(
        part: ImageUrlPart, context: ConversionContext
    ) -> Result[tuple[str, str], RelayError]:
        """Resolve a URL image into ``(media_type, base64)`` for Gemini."""
        resolver = context.media_resolver
        if resolver is None:
            return Err(media_resolution_required(part.url))
        return resolver.resolve(part.url)

    @staticmethod
    def _text_from_content(content: str | list[ContentPart]) -> str:
        """Extract plain text from canonical content."""
        if isinstance(content, str):
            return content
        return "".join(part.text for part in content if isinstance(part, TextPart))

    def _generation_config_from_ir(
        self, request: RelayRequest, context: ConversionContext
    ) -> dict[str, Any]:
        """Rebuild ``generationConfig`` from protocol metadata and canonical fields."""
        raw = request.metadata.get("generation_config")
        config: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
        for key in (
            "temperature",
            "topP",
            "topK",
            "maxOutputTokens",
            "stopSequences",
            "responseMimeType",
            "responseSchema",
            "thinkingConfig",
        ):
            config.pop(key, None)
        if request.temperature is not None:
            config["temperature"] = request.temperature
        if request.top_p is not None:
            config["topP"] = request.top_p
        if request.top_k is not None:
            config["topK"] = request.top_k
        if request.max_tokens is not None:
            config["maxOutputTokens"] = request.max_tokens
        if request.stop_sequences:
            config["stopSequences"] = list(request.stop_sequences)
        if request.response_format is not None:
            if request.response_format.get("type") == "json_object":
                config["responseMimeType"] = "application/json"
            if isinstance(request.response_format.get("schema"), dict):
                config["responseSchema"] = request.response_format["schema"]
        thinking_config = self._thinking_config_from_ir(request, context)
        if thinking_config is not None:
            config["thinkingConfig"] = thinking_config
        return config

    def _thinking_config_from_ir(
        self, request: RelayRequest, context: ConversionContext
    ) -> dict[str, Any] | None:
        """Build a Gemini ``thinkingConfig`` from canonical thinking."""
        thinking = request.thinking
        if thinking is not None:
            if thinking.suppress:
                record_loss(
                    context,
                    field="thinking",
                    target=_TARGET,
                    reason="suppress_not_supported",
                )
            if thinking.level is not None:
                return {"thinkingLevel": thinking.level}
            if thinking.budget_tokens:
                return {"thinkingBudget": thinking.budget_tokens}
        if (
            context.options.gemini.thinking_adapter_enabled
            and context.options.gemini.thinking_budget
        ):
            return {"thinkingBudget": context.options.gemini.thinking_budget}
        return None

    @staticmethod
    def _safety_settings_from_ir(
        request: RelayRequest, context: ConversionContext
    ) -> list[dict[str, Any]] | None:
        """Rebuild Gemini safety settings from metadata or the callback."""
        raw = request.metadata.get("safety_settings")
        if isinstance(raw, list):
            preserved = [dict(item) for item in raw if isinstance(item, dict)]
            return preserved or None
        collected: list[dict[str, Any]] = []
        for category in _SAFETY_CATEGORIES:
            threshold = context.safety_setting(category)
            if threshold and isinstance(threshold, str):
                collected.append({"category": category, "threshold": threshold})
        return collected or None

    @staticmethod
    def _tools_from_ir(tools: list[ToolDefinition]) -> list[dict[str, Any]] | None:
        """Serialize canonical tools as Gemini function declarations."""
        if not tools:
            return None
        return [
            {
                "functionDeclarations": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                    for tool in tools
                ]
            }
        ]

    @staticmethod
    def _tool_config_from_ir(request: RelayRequest) -> dict[str, Any] | None:
        """Rebuild a Gemini ``toolConfig`` from protocol metadata."""
        raw = request.metadata.get("tool_config")
        if isinstance(raw, dict):
            return dict(raw)
        return None

    @staticmethod
    def _request_passthrough(request: RelayRequest) -> dict[str, Any]:
        """Merge canonical stream state into request passthrough."""
        passthrough = dict(request.passthrough)
        if request.model:
            passthrough["model"] = request.model
        if request.stream:
            passthrough["stream"] = True
        return passthrough

    def _usage_from_wire(self, usage: GeminiUsageMetadata | None) -> RelayUsage | None:
        """Map a wire ``GeminiUsageMetadata`` into canonical ``RelayUsage``."""
        if usage is None:
            return None
        return RelayUsage(
            prompt_tokens=usage.prompt_token_count,
            completion_tokens=usage.candidates_token_count,
            cache_read_tokens=usage.cached_content_token_count or 0,
            reasoning_tokens=usage.thoughts_token_count or 0,
        )

    @staticmethod
    def _usage_to_wire(usage: RelayUsage | None) -> GeminiUsageMetadata | None:
        """Serialize canonical ``RelayUsage`` into a ``GeminiUsageMetadata``."""
        if usage is None:
            return None
        return GeminiUsageMetadata(
            prompt_token_count=usage.prompt_tokens,
            candidates_token_count=usage.completion_tokens,
            total_token_count=usage.total_tokens,
            cached_content_token_count=usage.cache_read_tokens or None,
            thoughts_token_count=usage.reasoning_tokens or None,
        )

    @staticmethod
    def _thought_tokens(payload: GeminiResponse) -> int | None:
        """Read thinking tokens from the usage metadata."""
        if (
            payload.usage_metadata is None
            or not payload.usage_metadata.thoughts_token_count
        ):
            return None
        return payload.usage_metadata.thoughts_token_count

    @staticmethod
    def _preserve_candidate_metadata(
        candidate: GeminiCandidate, passthrough: dict[str, Any]
    ) -> None:
        """Preserve candidate-level provider metadata as passthrough."""
        if candidate.safety_ratings:
            passthrough["safety_ratings"] = [
                rating.to_dict() for rating in candidate.safety_ratings
            ]
        if candidate.grounding_metadata is not None:
            passthrough["grounding_metadata"] = candidate.grounding_metadata.to_dict()
        if candidate.citation_metadata is not None:
            passthrough["citation_metadata"] = candidate.citation_metadata
        if candidate.token_count is not None:
            passthrough["token_count"] = candidate.token_count
        if candidate.avg_logprobs is not None:
            passthrough["avg_logprobs"] = candidate.avg_logprobs
        passthrough.update(candidate.passthrough)

    def _finish_reason_from_ir(
        self, finish_reason: str | None, context: ConversionContext
    ) -> str | None:
        """Map a canonical finish reason back to a Gemini value."""
        if finish_reason == "stop":
            return "STOP"
        if finish_reason == "length":
            return "MAX_TOKENS"
        if finish_reason in {"tool_calls", "function_call"}:
            if finish_reason == "function_call":
                record_loss(
                    context,
                    field="finish_reason",
                    target=_TARGET,
                    reason="function_call_adapted",
                )
            return "STOP"
        if finish_reason == "content_filter":
            return "SAFETY"
        if finish_reason == "other":
            return "OTHER"
        if finish_reason is not None:
            record_loss(
                context,
                field="finish_reason",
                target=_TARGET,
                reason="finish_reason_adapted",
            )
            return "OTHER"
        return None

    @staticmethod
    def _safety_ratings_from_passthrough(
        raw: Any,
    ) -> list[GeminiSafetyRating] | None:
        """Rebuild safety ratings from passthrough dicts."""
        if not isinstance(raw, list):
            return None
        ratings = [
            GeminiSafetyRating.from_dict(item) for item in raw if isinstance(item, dict)
        ]
        return ratings or None

    @classmethod
    def _grounding_from_passthrough(cls, raw: Any) -> GeminiGroundingMetadata | None:
        """Rebuild grounding metadata from a passthrough dict."""
        if not isinstance(raw, dict):
            return None
        return GeminiGroundingMetadata.from_dict(raw)

    @staticmethod
    def _prompt_feedback_from_passthrough(
        raw: Any,
    ) -> GeminiPromptFeedback | None:
        """Rebuild prompt feedback from a passthrough dict."""
        if not isinstance(raw, dict):
            return None
        return GeminiPromptFeedback.from_dict(raw)


def _config_number(generation_config: dict[str, Any], key: str) -> int | float | None:
    """Read a numeric generation config value when well-typed."""
    value = generation_config.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _config_int(generation_config: dict[str, Any], key: str) -> int | None:
    """Read an integer generation config value when well-typed."""
    value = _config_number(generation_config, key)
    if value is None or isinstance(value, float):
        return None
    return value
