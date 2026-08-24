"""OpenAI Responses stream event DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.contracts.ai.relay.dto.openai_responses.items import (
    ResponsesItem,
    ResponsesResponse,
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
]
