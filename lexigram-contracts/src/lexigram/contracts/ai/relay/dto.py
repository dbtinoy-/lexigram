"""Wire-accurate DTOs for the four relay protocols.

Each DTO carries only the fields the conversion engine semantically
understands. Unknown upstream fields land in ``passthrough`` and are
re-emitted verbatim on ``to_dict()`` so a gateway can forward request
bodies without data loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ClaudeContent",
    "ClaudeMessage",
    "ClaudeRequest",
    "GeminiContent",
    "GeminiPart",
    "GeminiRequest",
    "OpenAIChatMessage",
    "OpenAIChatRequest",
    "ResponsesItem",
    "ResponsesRequest",
    "ResponsesResponse",
]


@dataclass(frozen=True)
class OpenAIChatMessage:
    """A message in OpenAI Chat Completions format.

    Attributes:
        role: ``system``, ``user``, ``assistant``, ``tool``, ``function``.
        content: String content, or ``None`` for tool-call turns.
        name: Optional author name.
        tool_call_id: Id of the tool call this message answers.
        tool_calls: Tool calls on an assistant message, or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict, omitting ``None`` optional fields."""
        data: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            data["content"] = self.content
        if self.name is not None:
            data["name"] = self.name
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            data["tool_calls"] = self.tool_calls
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenAIChatMessage:
        """Build a message from a wire dict, capturing unknown keys."""
        known = {"role", "content", "name", "tool_call_id", "tool_calls"}
        return cls(
            role=data.get("role", "user"),
            content=data.get("content"),
            name=data.get("name"),
            tool_call_id=data.get("tool_call_id"),
            tool_calls=data.get("tool_calls"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class OpenAIChatRequest:
    """OpenAI Chat Completions request body.

    Attributes:
        model: Model name.
        messages: Message list.
        temperature: Sampling temperature (``None`` = omitted upstream).
        max_tokens: Max output tokens (``None`` = omitted upstream).
        stream: Whether the caller wants a stream.
        stream_options: ``{"include_usage": bool}`` or ``None``.
        tools: Raw tool definitions, or ``None``.
        tool_choice: Tool choice directive, or ``None``.
        stop: Stop string or list of strings, or ``None``.
        response_format: JSON-mode config, or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    model: str
    messages: list[OpenAIChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    stream_options: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None
    stop: str | list[str] | None = None
    response_format: dict[str, Any] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict, omitting ``None`` optional fields."""
        data: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
        }
        if self.temperature is not None:
            data["temperature"] = self.temperature
        if self.max_tokens is not None:
            data["max_tokens"] = self.max_tokens
        if self.stream:
            data["stream"] = True
        if self.stream_options is not None:
            data["stream_options"] = self.stream_options
        if self.tools is not None:
            data["tools"] = self.tools
        if self.tool_choice is not None:
            data["tool_choice"] = self.tool_choice
        if self.stop is not None:
            data["stop"] = self.stop
        if self.response_format is not None:
            data["response_format"] = self.response_format
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenAIChatRequest:
        """Build a request from a wire dict, capturing unknown keys."""
        known = {
            "model", "messages", "temperature", "max_tokens", "stream",
            "stream_options", "tools", "tool_choice", "stop", "response_format",
        }
        return cls(
            model=data["model"],
            messages=[OpenAIChatMessage.from_dict(m) for m in data.get("messages", [])],
            temperature=data.get("temperature"),
            max_tokens=data.get("max_tokens"),
            stream=bool(data.get("stream", False)),
            stream_options=data.get("stream_options"),
            tools=data.get("tools"),
            tool_choice=data.get("tool_choice"),
            stop=data.get("stop"),
            response_format=data.get("response_format"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ClaudeContent:
    """A content block in a Claude message.

    Attributes:
        type: ``text``, ``image``, ``tool_use``, ``tool_result``, ``thinking``.
        text: Text for ``text`` blocks.
        thinking: Thinking text for ``thinking`` blocks.
        signature: Thinking signature for ``thinking`` blocks.
        tool_use_id: Tool-use id.
        name: Tool name.
        input: Tool call arguments.
        image_source: ``{"type": "base64", "media_type": ..., "data": ...}`` or ``None``.
        tool_result_content: Content of a tool result block.
        passthrough: Unknown fields preserved verbatim.
    """

    type: str = "text"
    text: str | None = None
    thinking: str | None = None
    signature: str | None = None
    tool_use_id: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None
    image_source: dict[str, Any] | None = None
    tool_result_content: list[ClaudeContent] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict."""
        data: dict[str, Any] = {"type": self.type}
        if self.text is not None:
            data["text"] = self.text
        if self.thinking is not None:
            data["thinking"] = self.thinking
        if self.signature is not None:
            data["signature"] = self.signature
        if self.tool_use_id is not None:
            data["tool_use_id"] = self.tool_use_id
        if self.name is not None:
            data["name"] = self.name
        if self.input is not None:
            data["input"] = self.input
        if self.image_source is not None:
            data["source"] = self.image_source
        if self.tool_result_content is not None:
            data["content"] = [c.to_dict() for c in self.tool_result_content]
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClaudeContent:
        """Build a content block from a wire dict, capturing unknown keys."""
        known = {
            "type", "text", "thinking", "signature", "tool_use_id",
            "name", "input", "source", "content",
        }
        return cls(
            type=data.get("type", "text"),
            text=data.get("text"),
            thinking=data.get("thinking"),
            signature=data.get("signature"),
            tool_use_id=data.get("tool_use_id"),
            name=data.get("name"),
            input=data.get("input"),
            image_source=data.get("source"),
            tool_result_content=(
                [ClaudeContent.from_dict(c) for c in data["content"]]
                if isinstance(data.get("content"), list)
                else None
            ),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ClaudeMessage:
    """A message in Claude Messages format.

    Attributes:
        role: ``user`` or ``assistant``.
        content: List of content blocks.
    """

    role: str
    content: list[ClaudeContent]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict."""
        return {"role": self.role, "content": [c.to_dict() for c in self.content]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClaudeMessage:
        """Build a message from a wire dict."""
        content = data.get("content", [])
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        return cls(
            role=data["role"],
            content=[ClaudeContent.from_dict(c) for c in content],
        )


@dataclass(frozen=True)
class ClaudeRequest:
    """Claude Messages request body.

    Attributes:
        model: Model name.
        max_tokens: Max output tokens (required by the protocol).
        messages: Message list.
        system: System text, or ``None``.
        temperature: Sampling temperature, or ``None``.
        stream: Whether the caller wants a stream.
        tools: Raw tool definitions, or ``None``.
        stop_sequences: Stop strings, or ``None``.
        thinking: Thinking config dict, or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    model: str
    max_tokens: int
    messages: list[ClaudeMessage]
    system: str | None = None
    temperature: float | None = None
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    stop_sequences: list[str] | None = None
    thinking: dict[str, Any] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict, omitting ``None`` optional fields."""
        data: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [m.to_dict() for m in self.messages],
        }
        if self.system is not None:
            data["system"] = self.system
        if self.temperature is not None:
            data["temperature"] = self.temperature
        if self.stream:
            data["stream"] = True
        if self.tools is not None:
            data["tools"] = self.tools
        if self.stop_sequences is not None:
            data["stop_sequences"] = self.stop_sequences
        if self.thinking is not None:
            data["thinking"] = self.thinking
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClaudeRequest:
        """Build a request from a wire dict, capturing unknown keys."""
        known = {
            "model", "max_tokens", "messages", "system", "temperature",
            "stream", "tools", "stop_sequences", "thinking",
        }
        return cls(
            model=data["model"],
            max_tokens=data.get("max_tokens", 4096),
            messages=[ClaudeMessage.from_dict(m) for m in data.get("messages", [])],
            system=data.get("system"),
            temperature=data.get("temperature"),
            stream=bool(data.get("stream", False)),
            tools=data.get("tools"),
            stop_sequences=data.get("stop_sequences"),
            thinking=data.get("thinking"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class GeminiPart:
    """A part inside a Gemini content.

    Attributes:
        text: Text payload, or ``None``.
        inline_data: ``{"mime_type": ..., "data": base64}`` or ``None``.
        function_call: ``{"name": ..., "args": {...}}`` or ``None``.
        function_response: ``{"name": ..., "response": {...}}`` or ``None``.
        thought: Whether this is a thinking part.
        passthrough: Unknown fields preserved verbatim.
    """

    text: str | None = None
    inline_data: dict[str, Any] | None = None
    function_call: dict[str, Any] | None = None
    function_response: dict[str, Any] | None = None
    thought: bool = False
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict."""
        data: dict[str, Any] = {}
        if self.text is not None:
            data["text"] = self.text
        if self.inline_data is not None:
            data["inlineData"] = self.inline_data
        if self.function_call is not None:
            data["functionCall"] = self.function_call
        if self.function_response is not None:
            data["functionResponse"] = self.function_response
        if self.thought:
            data["thought"] = True
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeminiPart:
        """Build a part from a wire dict, capturing unknown keys."""
        known = {"text", "inlineData", "functionCall", "functionResponse", "thought"}
        return cls(
            text=data.get("text"),
            inline_data=data.get("inlineData"),
            function_call=data.get("functionCall"),
            function_response=data.get("functionResponse"),
            thought=bool(data.get("thought", False)),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class GeminiContent:
    """One content turn in Gemini format.

    Attributes:
        role: ``user``, ``model``, ``function``.
        parts: Content parts.
    """

    role: str
    parts: list[GeminiPart]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict."""
        return {"role": self.role, "parts": [p.to_dict() for p in self.parts]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeminiContent:
        """Build a content from a wire dict."""
        return cls(
            role=data.get("role", "user"),
            parts=[GeminiPart.from_dict(p) for p in data.get("parts", [])],
        )


@dataclass(frozen=True)
class GeminiRequest:
    """Gemini ``generateContent`` request body.

    Attributes:
        contents: Conversation turns.
        system_instruction: ``{"parts": [{"text": ...}]}`` or ``None``.
        generation_config: Generation config dict (empty when unset).
        tools: Tool definitions list, or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    contents: list[GeminiContent]
    system_instruction: dict[str, Any] | None = None
    generation_config: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict, omitting empty optionals."""
        data: dict[str, Any] = {"contents": [c.to_dict() for c in self.contents]}
        if self.system_instruction is not None:
            data["system_instruction"] = self.system_instruction
        if self.generation_config:
            data["generationConfig"] = self.generation_config
        if self.tools is not None:
            data["tools"] = self.tools
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeminiRequest:
        """Build a request from a wire dict, capturing unknown keys."""
        known = {"contents", "system_instruction", "generationConfig", "tools"}
        return cls(
            contents=[GeminiContent.from_dict(c) for c in data.get("contents", [])],
            system_instruction=data.get("system_instruction"),
            generation_config=data.get("generationConfig", {}),
            tools=data.get("tools"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ResponsesItem:
    """An item in a Responses request ``input`` or response ``output``.

    Attributes:
        type: ``message``, ``function_call``, ``function_call_output``,
            ``reasoning``, ``web_search_call``.
        role: ``user`` / ``assistant`` for message items.
        content: Message content list, or ``None``.
        id: Item id, or ``None``.
        call_id: Function call id, or ``None``.
        name: Function name, or ``None``.
        arguments: Function call arguments string, or ``None``.
        output: Function call output string, or ``None``.
        summary: Reasoning summary for ``reasoning`` items, or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    type: str
    role: str | None = None
    content: list[dict[str, Any]] | None = None
    id: str | None = None
    call_id: str | None = None
    name: str | None = None
    arguments: str | None = None
    output: str | None = None
    summary: list[dict[str, Any]] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict."""
        data: dict[str, Any] = {"type": self.type}
        if self.role is not None:
            data["role"] = self.role
        if self.content is not None:
            data["content"] = self.content
        if self.id is not None:
            data["id"] = self.id
        if self.call_id is not None:
            data["call_id"] = self.call_id
        if self.name is not None:
            data["name"] = self.name
        if self.arguments is not None:
            data["arguments"] = self.arguments
        if self.output is not None:
            data["output"] = self.output
        if self.summary is not None:
            data["summary"] = self.summary
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesItem:
        """Build an item from a wire dict, capturing unknown keys."""
        known = {
            "type", "role", "content", "id", "call_id",
            "name", "arguments", "output", "summary",
        }
        return cls(
            type=data.get("type", "message"),
            role=data.get("role"),
            content=data.get("content"),
            id=data.get("id"),
            call_id=data.get("call_id"),
            name=data.get("name"),
            arguments=data.get("arguments"),
            output=data.get("output"),
            summary=data.get("summary"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ResponsesRequest:
    """OpenAI Responses request body.

    Attributes:
        model: Model name.
        input: List of items, or a plain string.
        instructions: System instructions, or ``None``.
        tools: Tool definitions, or ``None``.
        temperature: Sampling temperature, or ``None``.
        max_output_tokens: Max output tokens, or ``None``.
        stream: Whether the caller wants a stream.
        include: Extra top-level fields to include, or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    model: str
    input: list[ResponsesItem] | str
    instructions: str | None = None
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    stream: bool = False
    include: list[str] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict, omitting ``None`` optional fields."""
        data: dict[str, Any] = {"model": self.model}
        if isinstance(self.input, str):
            data["input"] = self.input
        else:
            data["input"] = [i.to_dict() for i in self.input]
        if self.instructions is not None:
            data["instructions"] = self.instructions
        if self.tools is not None:
            data["tools"] = self.tools
        if self.temperature is not None:
            data["temperature"] = self.temperature
        if self.max_output_tokens is not None:
            data["max_output_tokens"] = self.max_output_tokens
        if self.stream:
            data["stream"] = True
        if self.include is not None:
            data["include"] = self.include
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesRequest:
        """Build a request from a wire dict, capturing unknown keys."""
        known = {
            "model", "input", "instructions", "tools", "temperature",
            "max_output_tokens", "stream", "include",
        }
        raw_input = data.get("input", [])
        return cls(
            model=data["model"],
            input=(
                raw_input
                if isinstance(raw_input, str)
                else [ResponsesItem.from_dict(i) for i in raw_input]
            ),
            instructions=data.get("instructions"),
            tools=data.get("tools"),
            temperature=data.get("temperature"),
            max_output_tokens=data.get("max_output_tokens"),
            stream=bool(data.get("stream", False)),
            include=data.get("include"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ResponsesResponse:
    """OpenAI Responses non-streamed response body.

    Attributes:
        id: Response id.
        model: Model name.
        output: Output items (messages, function calls, reasoning).
        status: ``completed`` etc.
        usage: Usage dict (raw), or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    id: str
    model: str
    output: list[ResponsesItem]
    status: str | None = None
    usage: dict[str, Any] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict."""
        data: dict[str, Any] = {
            "id": self.id,
            "model": self.model,
            "output": [i.to_dict() for i in self.output],
        }
        if self.status is not None:
            data["status"] = self.status
        if self.usage is not None:
            data["usage"] = self.usage
        data.update(self.passthrough)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesResponse:
        """Build a response from a wire dict, capturing unknown keys."""
        known = {"id", "model", "output", "status", "usage"}
        return cls(
            id=data["id"],
            model=data["model"],
            output=[ResponsesItem.from_dict(i) for i in data.get("output", [])],
            status=data.get("status"),
            usage=data.get("usage"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )
