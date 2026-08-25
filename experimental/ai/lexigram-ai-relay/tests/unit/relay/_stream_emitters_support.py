"""Shared fixtures/checkers for stream-emitter tests."""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.errors import unsupported_format
from lexigram.ai.relay.stream import (
    StreamSession,
    claude_emitter,
    gemini_emitter,
    openai_chat_emitter,
    openai_responses_emitter,
)
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.dto import (
    ClaudeStreamEvent,
    GeminiResponse,
    OpenAIChatStreamChunk,
    ResponsesEvent,
)
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

EMITTERS: dict[RelayFormat, Any] = {
    RelayFormat.OPENAI_CHAT: openai_chat_emitter,
    RelayFormat.OPENAI_RESPONSES: openai_responses_emitter,
    RelayFormat.CLAUDE: claude_emitter,
    RelayFormat.GEMINI: gemini_emitter,
}

FORMATS: list[RelayFormat] = list(EMITTERS)

DIRECTIONS: list[tuple[RelayFormat, RelayFormat]] = [
    (source, target) for source in FORMATS for target in FORMATS if source is not target
]

USAGE = RelayUsage(prompt_tokens=10, completion_tokens=5)


class HarnessNormalizer:
    """Maps synthetic source wire events to canonical deltas.

    Events are tuples: ``("role",)``, ``("text", str)``,
    ``("think", str, signature|None)``, ``("tool", index, id, name,
    args)`` (fragments split across events), ``("usage", RelayUsage)``,
    ``("finish", reason)``.
    """

    def __init__(self, source: RelayFormat) -> None:
        self.source = source
        self.calls: list[Any] = []

    def __call__(
        self, event: Any, *, state: Any
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        self.calls.append(event)
        if state.source is not self.source:
            return Err(unsupported_format(f"expected {self.source.value} event"))
        kind = event[0]
        if kind == "role":
            return Ok((StreamDelta(kind="role", role="assistant"),))
        if kind == "text":
            return Ok((StreamDelta(kind="content", content=event[1]),))
        if kind == "think":
            signature = event[2] if len(event) > 2 else None
            passthrough = {"signature": signature} if signature else {}
            return Ok(
                (
                    StreamDelta(
                        kind="thinking",
                        thinking_delta=event[1],
                        passthrough=passthrough,
                    ),
                )
            )
        if kind == "tool":
            return Ok(
                (
                    StreamDelta(
                        kind="tool_call",
                        tool_call_index=event[1],
                        tool_call_id=event[2],
                        tool_call_name=event[3],
                        tool_call_arguments=event[4],
                    ),
                )
            )
        if kind == "usage":
            return Ok((StreamDelta(kind="usage", usage=event[1]),))
        if kind == "finish":
            return Ok((StreamDelta(kind="finish", finish_reason=event[1]),))
        raise AssertionError(f"unexpected event {event!r}")


def make_session(
    source: RelayFormat, target: RelayFormat, *, include_usage: bool = False
) -> tuple[StreamSession, HarnessNormalizer]:
    """Build a session wired to a harness normalizer and the target emitter."""
    normalizer = HarnessNormalizer(source)
    session = StreamSession(
        source=source,
        target=target,
        model="gpt-4o",
        stream_id="s1",
        created=123,
        include_usage=include_usage,
        normalizer=normalizer,
        emitter=EMITTERS[target],
    )
    return session, normalizer


def run(session: StreamSession, events: list[Any]) -> list[Any]:
    """Accept events and collect emitted target wire objects."""
    output: list[Any] = []
    for event in events:
        output.extend(session.accept(event))
    return output


def total(session: StreamSession, events: list[Any]) -> list[Any]:
    """Run events and append finalize's terminal events."""
    output = run(session, events)
    output.extend(session.finalize())
    return output


# -- per-target checkers -----------------------------------------------------


class ChatChecker:
    """Reads text/thinking/tools/usage/terminal state out of Chat chunks."""

    def chunks(self, events: list[Any]) -> list[OpenAIChatStreamChunk]:
        assert all(isinstance(e, OpenAIChatStreamChunk) for e in events)
        return [e for e in events if isinstance(e, OpenAIChatStreamChunk)]

    def text(self, events: list[Any]) -> str:
        return "".join(
            c.choices[0].delta.content or ""
            for c in self.chunks(events)
            if c.choices and c.choices[0].delta
        )

    def thinking(self, events: list[Any]) -> str:
        return "".join(
            c.choices[0].delta.reasoning_content or ""
            for c in self.chunks(events)
            if c.choices and c.choices[0].delta
        )

    def tool_calls(self, events: list[Any]) -> list[tuple[int, str, str, str]]:
        calls: dict[int, list[str]] = {}
        for chunk in self.chunks(events):
            if not chunk.choices or not chunk.choices[0].delta:
                continue
            for fragment in chunk.choices[0].delta.tool_calls or []:
                index = int(fragment.get("index", 0))
                entry = calls.setdefault(index, ["", "", ""])
                if fragment.get("id"):
                    entry[0] += str(fragment["id"])
                function = fragment.get("function") or {}
                if function.get("name"):
                    entry[1] += str(function["name"])
                if function.get("arguments"):
                    entry[2] += str(function["arguments"])
        return [
            (index, entry[0], entry[1], entry[2])
            for index, entry in sorted(calls.items())
        ]

    def usage(self, events: list[Any]) -> dict[str, Any] | None:
        for chunk in reversed(self.chunks(events)):
            if chunk.usage is not None:
                return chunk.usage
        return None

    def finished(self, events: list[Any]) -> str | None:
        for chunk in self.chunks(events):
            if chunk.choices and chunk.choices[0].finish_reason:
                return chunk.choices[0].finish_reason
        return None


class ClaudeChecker:
    """Reads text/thinking/tools/usage/terminal state out of Claude events."""

    def events(self, events: list[Any]) -> list[ClaudeStreamEvent]:
        assert all(isinstance(e, ClaudeStreamEvent) for e in events)
        return [e for e in events if isinstance(e, ClaudeStreamEvent)]

    def text(self, events: list[Any]) -> str:
        return "".join(
            e.delta.get("text", "") or ""
            for e in self.events(events)
            if e.type == "content_block_delta"
            and isinstance(e.delta, dict)
            and e.delta.get("type") == "text_delta"
        )

    def thinking(self, events: list[Any]) -> str:
        return "".join(
            e.delta.get("thinking", "") or ""
            for e in self.events(events)
            if e.type == "content_block_delta"
            and isinstance(e.delta, dict)
            and e.delta.get("type") == "thinking_delta"
        )

    def tool_calls(self, events: list[Any]) -> list[tuple[int, str, str, str]]:
        blocks: dict[int, list[str]] = {}
        for e in self.events(events):
            if e.type == "content_block_start" and e.content_block is not None:
                block = e.content_block
                if block.type == "tool_use":
                    blocks[e.index or 0] = [
                        block.tool_use_id or "",
                        block.name or "",
                        "",
                    ]
            elif (
                e.type == "content_block_delta"
                and isinstance(e.delta, dict)
                and e.delta.get("type") == "input_json_delta"
            ):
                entry = blocks.get(e.index)
                if entry is not None:
                    entry[2] += str(e.delta.get("partial_json", ""))
        return [
            (index, entry[0], entry[1], entry[2])
            for index, entry in sorted(blocks.items())
        ]

    def usage(self, events: list[Any]) -> dict[str, Any] | None:
        usage = None
        for e in self.events(events):
            if e.usage is not None:
                usage = e.usage
        return usage

    def finished(self, events: list[Any]) -> str | None:
        stop_reason = None
        for e in self.events(events):
            if e.type == "message_delta" and e.delta:
                stop_reason = e.delta.get("stop_reason")
        return stop_reason

    def has_message_stop(self, events: list[Any]) -> bool:
        return any(e.type == "message_stop" for e in self.events(events))

    def blocks_closed(self, events: list[Any]) -> bool:
        """Every opened content block is closed exactly once."""
        opened: set[int] = set()
        for e in self.events(events):
            if e.type == "content_block_start":
                assert e.index not in opened
                opened.add(e.index or 0)
            elif e.type == "content_block_stop":
                assert e.index in opened
                opened.discard(e.index or 0)
        return not opened


class GeminiChecker:
    """Reads text/thinking/tools/usage/terminal state out of Gemini chunks."""

    def chunks(self, events: list[Any]) -> list[GeminiResponse]:
        assert all(isinstance(e, GeminiResponse) for e in events)
        return [e for e in events if isinstance(e, GeminiResponse)]

    def text(self, events: list[Any]) -> str:
        text = ""
        for chunk in self.chunks(events):
            for candidate in chunk.candidates:
                if candidate.content is None:
                    continue
                for part in candidate.content.parts:
                    if part.text is not None and not part.thought:
                        text += part.text
        return text

    def thinking(self, events: list[Any]) -> str:
        text = ""
        for chunk in self.chunks(events):
            for candidate in chunk.candidates:
                if candidate.content is None:
                    continue
                for part in candidate.content.parts:
                    if part.text is not None and part.thought:
                        text += part.text
        return text

    def tool_calls(self, events: list[Any]) -> list[tuple[int, str, Any]]:
        calls: list[tuple[int, str, Any]] = []
        for chunk in self.chunks(events):
            for candidate in chunk.candidates:
                if candidate.content is None:
                    continue
                for part in candidate.content.parts:
                    if part.function_call is not None:
                        calls.append(
                            (
                                candidate.index or 0,
                                str(part.function_call.get("name", "")),
                                part.function_call.get("args", {}),
                            )
                        )
        return calls

    def usage(self, events: list[Any]) -> dict[str, Any] | None:
        for chunk in reversed(self.chunks(events)):
            if chunk.usage_metadata is not None:
                return chunk.usage_metadata.to_dict()
        return None

    def finished(self, events: list[Any]) -> str | None:
        for chunk in reversed(self.chunks(events)):
            for candidate in chunk.candidates:
                if candidate.finish_reason:
                    return candidate.finish_reason
        return None


class ResponsesChecker:
    """Reads text/thinking/tools/usage/terminal state out of Responses events."""

    def events(self, events: list[Any]) -> list[ResponsesEvent]:
        assert all(isinstance(e, ResponsesEvent) for e in events)
        return [e for e in events if isinstance(e, ResponsesEvent)]

    def text(self, events: list[Any]) -> str:
        return "".join(
            e.delta or ""
            for e in self.events(events)
            if e.type == "response.output_text.delta"
        )

    def thinking(self, events: list[Any]) -> str:
        return "".join(
            e.delta or ""
            for e in self.events(events)
            if e.type == "response.reasoning_summary_text.delta"
        )

    def tool_calls(self, events: list[Any]) -> list[tuple[int, str, str, str]]:
        items = self._final_items(events)
        return [
            (0, item.call_id or "", item.name or "", item.arguments or "")
            for item in items
            if item.type == "function_call"
        ]

    def _final_items(self, events: list[Any]) -> list[Any]:
        completed = [e for e in self.events(events) if e.type == "response.completed"]
        if not completed:
            return []
        response = completed[-1].response
        return list(response.output) if response is not None else []

    def usage(self, events: list[Any]) -> dict[str, Any] | None:
        completed = [e for e in self.events(events) if e.type == "response.completed"]
        if not completed:
            return None
        response = completed[-1].response
        if response is None or response.usage is None:
            return None
        return response.usage.to_dict()

    def finished(self, events: list[Any]) -> str | None:
        completed = [e for e in self.events(events) if e.type == "response.completed"]
        if not completed:
            return None
        response = completed[-1].response
        return response.status if response is not None else None

    def types(self, events: list[Any]) -> list[str]:
        return [e.type for e in self.events(events)]


CHECKERS: dict[RelayFormat, Any] = {
    RelayFormat.OPENAI_CHAT: ChatChecker(),
    RelayFormat.OPENAI_RESPONSES: ResponsesChecker(),
    RelayFormat.CLAUDE: ClaudeChecker(),
    RelayFormat.GEMINI: GeminiChecker(),
}
