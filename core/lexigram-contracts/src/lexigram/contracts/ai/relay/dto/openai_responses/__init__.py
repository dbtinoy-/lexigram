"""OpenAI Responses wire DTO family."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.contracts.ai.relay.dto.common import require_field


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
        status: Output item status (``completed`` / ``incomplete``).
        quality: Output item quality (relaykit always serializes ``""``).
        size: Output item size (relaykit always serializes ``""``).
        passthrough: Unknown fields preserved verbatim.
    """

    type: str | None = None
    role: str | None = None
    content: str | list[dict[str, Any]] | None = None
    id: str | None = None
    call_id: str | None = None
    name: str | None = None
    arguments: str | None = None
    output: str | None = None
    summary: list[dict[str, Any]] | None = None
    status: str | None = None
    quality: str | None = None
    size: str | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict.

        Output items (those carrying a ``status``) always serialize
        ``content`` (relaykit uses no ``omitempty`` on it, so function
        calls carry an explicit ``null``) plus the ``status``,
        ``quality``, and ``size`` fields relaykit Go structs always
        render. Input request items never render a ``content`` key for
        function calls.
        """
        data: dict[str, Any] = {**self.passthrough}
        if self.type is not None:
            data["type"] = self.type
        if self.role is not None:
            data["role"] = self.role
        if (
            self.type == "function_call" and self.status is not None
        ) or self.content is not None:
            data["content"] = self.content
        if self.status is not None:
            data["status"] = self.status
        if self.quality is not None:
            data["quality"] = self.quality
        if self.size is not None:
            data["size"] = self.size
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
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesItem:
        """Build an item from a wire dict, capturing unknown keys."""
        known = {
            "type",
            "role",
            "content",
            "id",
            "call_id",
            "name",
            "arguments",
            "output",
            "summary",
            "status",
            "quality",
            "size",
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
            status=data.get("status"),
            quality=data.get("quality"),
            size=data.get("size"),
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
        parallel_tool_calls: Parallel tool-call flag, or ``None``.
        reasoning: Reasoning config (e.g. ``{"effort": ...}``), or ``None``.
        text: Response-format config, or ``None``.
        service_tier: Service tier, or ``None``.
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
    parallel_tool_calls: bool | None = None
    reasoning: dict[str, Any] | None = None
    text: dict[str, Any] | None = None
    service_tier: str | None = None
    tool_choice: Any | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict, omitting ``None`` optional fields."""
        data: dict[str, Any] = {**self.passthrough, "model": self.model}
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
        data["stream"] = self.stream
        if self.include is not None:
            data["include"] = self.include
        if self.parallel_tool_calls is not None:
            data["parallel_tool_calls"] = self.parallel_tool_calls
        if self.reasoning is not None:
            data["reasoning"] = self.reasoning
        if self.text is not None:
            data["text"] = self.text
        if self.service_tier is not None:
            data["service_tier"] = self.service_tier
        if self.tool_choice is not None:
            data["tool_choice"] = self.tool_choice
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesRequest:
        """Build a request from a wire dict, capturing unknown keys.

        Raises:
            RelayError: With code ``malformed_payload`` when ``model``
                is absent.
        """
        known = {
            "model",
            "input",
            "instructions",
            "tools",
            "temperature",
            "max_output_tokens",
            "stream",
            "include",
            "parallel_tool_calls",
            "reasoning",
            "text",
            "service_tier",
            "tool_choice",
        }
        raw_input = data.get("input", [])
        return cls(
            model=require_field(data, "model"),
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
            parallel_tool_calls=data.get("parallel_tool_calls"),
            reasoning=data.get("reasoning"),
            text=data.get("text"),
            service_tier=data.get("service_tier"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ResponsesUsage:
    """OpenAI Responses usage accounting.

    Attributes:
        prompt_tokens: Chat-style prompt token count.
        completion_tokens: Chat-style completion token count.
        total_tokens: Explicit totals (can differ from prompt + completion).
        prompt_tokens_details: Cache details (relaykit serializes a
            zero-value prompt_tokens_details dict even when empty).
        completion_tokens_details: Reasoning/details count (relaykit
            serializes it even when empty).
        input_tokens: Source input count carried into chat emission.
        input_tokens_details: Raw input token details per ``input_tokens``.
        output_tokens: Source output count carried into chat emails.
        output_tokens_details: Legacy capture of the raw output details
            (never serialized; relaykit emits ``completion_tokens_details``).
        passthrough: Unknown fields preserved verbatim.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    prompt_tokens_details: dict[str, Any] | None = None
    completion_tokens_details: dict[str, Any] | None = None
    input_tokens: int = 0
    input_tokens_details: dict[str, Any] | None = None
    output_tokens: int = 0
    output_tokens_details: dict[str, Any] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict, mirroring relaykit's always-on usage."""
        data: dict[str, Any] = {
            **self.passthrough,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
            or (self.input_tokens + self.output_tokens),
            "prompt_tokens_details": self.prompt_tokens_details or {"cached_tokens": 0},
            "completion_tokens_details": self.completion_tokens_details
            or {"reasoning_tokens": 0},
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }
        if self.input_tokens_details is not None:
            data["input_tokens_details"] = self.input_tokens_details
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesUsage:
        """Build usage from a wire dict, capturing unknown keys."""
        known = {
            "input_tokens",
            "input_tokens_details",
            "output_tokens",
            "output_tokens_details",
            "total_tokens",
            "prompt_tokens_details",
            "completion_tokens_details",
            "prompt_tokens",
            "completion_tokens",
        }
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            prompt_tokens_details=data.get("prompt_tokens_details"),
            completion_tokens_details=data.get("completion_tokens_details"),
            input_tokens=data.get("input_tokens", 0),
            input_tokens_details=data.get("input_tokens_details"),
            output_tokens=data.get("output_tokens", 0),
            output_tokens_details=data.get("output_tokens_details"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ResponsesIncompleteDetails:
    """Why a Responses response is incomplete.

    Attributes:
        reason: ``max_output_tokens``, ``content_filter``, etc.
        passthrough: Unknown fields preserved verbatim.
    """

    reason: str | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict, omitting ``None`` optional fields."""
        data: dict[str, Any] = {**self.passthrough}
        if self.reason is not None:
            data["reason"] = self.reason
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesIncompleteDetails:
        """Build details from a wire dict, capturing unknown keys."""
        known = {"reason"}
        return cls(
            reason=data.get("reason"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ResponsesResponse:
    """OpenAI Responses non-streamed response body.

    Attributes:
        id: Response id.
        model: Model name.
        output: Output items (messages, function calls, reasoning).
        object: Object type (``response``).
        created_at: Unix timestamp.
        status: ``completed``, ``in_progress``, ``incomplete``, ``failed``.
        incomplete_details: Why the response is incomplete, or ``None``.
        error: Error object for failed responses, or ``None``.
        usage: Typed usage, or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    id: str
    model: str
    output: list[ResponsesItem]
    object: str = "response"
    created_at: int = 0
    status: str | None = None
    incomplete_details: ResponsesIncompleteDetails | None = None
    error: dict[str, Any] | None = None
    usage: ResponsesUsage | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict.

        Relaykit's Go response structs always serialize the optional
        request-style fields (``instructions``, ``temperature``, ...) as
        explicit nulls/zeros, so this mirrors that shape.
        """
        data: dict[str, Any] = {
            **self.passthrough,
            "id": self.id,
            "object": self.object,
            "created_at": self.created_at,
            "status": self.status or "completed",
            "instructions": None,
            "max_output_tokens": 0,
            "model": self.model,
            "output": [i.to_dict() for i in self.output],
            "parallel_tool_calls": False,
            "previous_response_id": None,
            "reasoning": None,
            "store": False,
            "temperature": 0,
            "tool_choice": None,
            "tools": None,
            "top_p": 0,
            "truncation": None,
        }
        if self.incomplete_details is not None:
            data["incomplete_details"] = self.incomplete_details.to_dict()
        if self.error is not None:
            data["error"] = self.error
        if self.usage is not None:
            data["usage"] = self.usage.to_dict()
        data["user"] = None
        data["metadata"] = None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesResponse:
        """Build a response from a wire dict, capturing unknown keys.

        Raises:
            RelayError: With code ``malformed_payload`` when ``id`` or
                ``model`` is absent.
        """
        known = {
            "id",
            "object",
            "created_at",
            "model",
            "output",
            "status",
            "incomplete_details",
            "error",
            "usage",
        }
        incomplete = data.get("incomplete_details")
        usage = data.get("usage")
        return cls(
            id=require_field(data, "id"),
            object=data.get("object", "response"),
            created_at=data.get("created_at", 0),
            model=require_field(data, "model"),
            output=[ResponsesItem.from_dict(i) for i in data.get("output", [])],
            status=data.get("status"),
            incomplete_details=(
                ResponsesIncompleteDetails.from_dict(incomplete)
                if isinstance(incomplete, dict)
                else None
            ),
            error=data.get("error"),
            usage=ResponsesUsage.from_dict(usage) if isinstance(usage, dict) else None,
            passthrough={k: v for k, v in data.items() if k not in known},
        )


@dataclass(frozen=True)
class ResponsesEvent:
    """One SSE event in the Responses stream lifecycle.

    The ``type`` field is the discriminator (``response.created``,
    ``response.output_item.added``, ``response.content_part.added``,
    ``response.output_text.delta``, ``response.output_text.done``,
    ``response.content_part.done``, ``response.output_item.done``,
    ``response.function_call_arguments.delta``,
    ``response.function_call_arguments.done``,
    ``response.reasoning_summary_text.delta``,
    ``response.reasoning_summary_text.done``, ``response.completed``,
    ``response.incomplete``, ``response.failed``, ``response.error``).

    Attributes:
        type: Event type discriminator.
        sequence_number: Monotonic event sequence number.
        response: Snapshot on ``response.*`` lifecycle events, or ``None``.
        item: Item on ``output_item.*`` events, or ``None``.
        item_id: Id of the item an event describes, or ``None``.
        output_index: Output item index, or ``None``.
        content_index: Content part index, or ``None``.
        part: Raw content part on ``content_part.*`` events, or ``None``.
        delta: Text/arguments delta, or ``None``.
        error: Raw error payload, or ``None``.
        passthrough: Unknown fields preserved verbatim.
    """

    type: str
    sequence_number: int = 0
    response: ResponsesResponse | None = None
    item: ResponsesItem | None = None
    item_id: str | None = None
    output_index: int | None = None
    content_index: int | None = None
    part: dict[str, Any] | None = None
    delta: str | None = None
    error: dict[str, Any] | None = None
    passthrough: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to wire dict as the Responses SSE envelope.

        Relaykit frames each stream event as ``{"Type": <type>, "Payload":
        <fields>}`` — the ``Type`` is the SSE ``event`` name and ``Payload``
        is the JSON body (which repeats the ``type`` discriminator).
        """
        payload: dict[str, Any] = {**self.passthrough, "type": self.type}
        if self.sequence_number:
            payload["sequence_number"] = self.sequence_number
        if self.response is not None:
            payload["response"] = self.response.to_dict()
        if self.item is not None:
            payload["item"] = self.item.to_dict()
        if self.item_id is not None:
            payload["item_id"] = self.item_id
        if self.output_index is not None:
            payload["output_index"] = self.output_index
        if self.content_index is not None:
            payload["content_index"] = self.content_index
        if self.part is not None:
            payload["part"] = self.part
        if self.delta is not None:
            payload["delta"] = self.delta
        if self.error is not None:
            payload["error"] = self.error
        return {"Type": self.type, "Payload": payload}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResponsesEvent:
        """Build an event from a wire dict, capturing unknown keys.

        Accepts both the SSE envelope (``Payload``) and the bare payload.
        """
        source = data.get("Payload")
        if isinstance(source, dict):
            data = source
        known = {
            "type",
            "sequence_number",
            "response",
            "item",
            "item_id",
            "output_index",
            "content_index",
            "part",
            "delta",
            "error",
        }
        response = data.get("response")
        item = data.get("item")
        return cls(
            type=data.get("type", "response.in_progress"),
            sequence_number=data.get("sequence_number", 0),
            response=(
                ResponsesResponse.from_dict(response)
                if isinstance(response, dict)
                else None
            ),
            item=ResponsesItem.from_dict(item) if isinstance(item, dict) else None,
            item_id=data.get("item_id"),
            output_index=data.get("output_index"),
            content_index=data.get("content_index"),
            part=data.get("part"),
            delta=data.get("delta"),
            error=data.get("error"),
            passthrough={k: v for k, v in data.items() if k not in known},
        )


__all__ = [
    "ResponsesEvent",
    "ResponsesIncompleteDetails",
    "ResponsesItem",
    "ResponsesRequest",
    "ResponsesResponse",
    "ResponsesUsage",
]
