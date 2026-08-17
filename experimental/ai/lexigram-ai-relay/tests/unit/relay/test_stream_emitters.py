"""Tests for the target-specific stream emitters.

Each target emitter maps one canonical :class:`StreamDelta` into its
wire event family.  These tests drive every source/target direction
through the session state machine (12 directions, text/tool/usage/
finish/truncated) and verify the emitted wire shapes per target.
"""

from __future__ import annotations

from typing import Any

import pytest

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


# -- 12-direction table ------------------------------------------------------


@pytest.mark.parametrize("source,target", DIRECTIONS)
def test_direction_text_and_thinking(source: RelayFormat, target: RelayFormat) -> None:
    """Every direction relays text and thinking deltas."""
    session, _ = make_session(source, target)
    output = total(
        session,
        [
            ("role",),
            ("think", "Let me ", None),
            ("think", "think", None),
            ("text", "Hello "),
            ("text", "world"),
            ("finish", "stop"),
        ],
    )
    checker = CHECKERS[target]
    assert checker.text(output) == "Hello world"
    assert checker.thinking(output) == "Let me think"
    assert checker.finished(output) is not None


@pytest.mark.parametrize("source,target", DIRECTIONS)
def test_direction_tool_call(source: RelayFormat, target: RelayFormat) -> None:
    """Every direction preserves tool id, name, and raw argument text."""
    session, _ = make_session(source, target)
    output = total(
        session,
        [
            ("role",),
            ("tool", 0, "call_123", "get_weather", None),
            ("tool", 0, None, None, '{"city'),
            ("tool", 0, None, None, '":"SP"}'),
            ("finish", "stop"),
        ],
    )
    calls = CHECKERS[target].tool_calls(output)
    if target is RelayFormat.GEMINI:
        assert len(calls) == 1
        assert calls[0][1] == "get_weather"
        assert calls[0][2] == {"city": "SP"}
    else:
        assert len(calls) == 1
        assert calls[0][1] == "call_123"
        assert calls[0][2] == "get_weather"
        assert calls[0][3] == '{"city":"SP"}'


@pytest.mark.parametrize("source,target", DIRECTIONS)
def test_direction_usage(source: RelayFormat, target: RelayFormat) -> None:
    """Usage seen before finish surfaces on each target format."""
    session, _ = make_session(source, target)
    output = total(
        session,
        [
            ("role",),
            ("text", "hi"),
            ("usage", USAGE),
            ("finish", "stop"),
        ],
    )
    usage = CHECKERS[target].usage(output)
    if source is RelayFormat.OPENAI_RESPONSES and target is RelayFormat.OPENAI_CHAT:
        assert usage is None
        return
    assert usage is not None
    if target is RelayFormat.GEMINI:
        assert usage.get("promptTokenCount") == (
            0 if source is RelayFormat.OPENAI_RESPONSES else 10
        )
        assert usage.get("candidatesTokenCount") == (
            0 if source is RelayFormat.OPENAI_RESPONSES else 5
        )
    elif target is RelayFormat.CLAUDE:
        assert usage.input_tokens == 10
        assert usage.output_tokens == 5
    elif target is RelayFormat.OPENAI_CHAT:
        assert usage.get("prompt_tokens") == 10
        assert usage.get("completion_tokens") == 5
    else:
        assert usage.get("input_tokens") == 10
        assert usage.get("output_tokens") == 5


@pytest.mark.parametrize("source,target", DIRECTIONS)
def test_direction_truncated_finalization(
    source: RelayFormat, target: RelayFormat
) -> None:
    """A truncated stream finalizes to a safe stop on every target."""
    session, _ = make_session(source, target)
    output = total(session, [("role",), ("text", "partial")])
    checker = CHECKERS[target]
    assert checker.text(output) == "partial"
    assert checker.finished(output) is not None
    if target is RelayFormat.CLAUDE:
        assert checker.has_message_stop(output)
    if target is RelayFormat.GEMINI:
        assert checker.finished(output) == "STOP"


@pytest.mark.parametrize("source,target", DIRECTIONS)
def test_direction_truncated_usage_requested(
    source: RelayFormat, target: RelayFormat
) -> None:
    """Finalize with include_usage surfaces usage on every target."""
    session, _ = make_session(source, target, include_usage=True)
    output = total(session, [("role",), ("text", "hi"), ("usage", USAGE)])
    checker = CHECKERS[target]
    assert checker.text(output) == "hi"
    assert checker.finished(output) is not None
    usage = checker.usage(output)
    if source is RelayFormat.OPENAI_RESPONSES and target is RelayFormat.OPENAI_CHAT:
        assert usage is None
        return
    assert usage is not None
    if target is RelayFormat.GEMINI:
        assert usage.get("promptTokenCount") == (
            0 if source is RelayFormat.OPENAI_RESPONSES else 10
        )
    elif target is RelayFormat.CLAUDE:
        assert usage.input_tokens == 10
    elif target is RelayFormat.OPENAI_CHAT:
        assert usage.get("prompt_tokens") == 10
    else:
        assert usage.get("input_tokens") == 10


# -- OpenAI Chat emitter ------------------------------------------------------


def test_chat_role_then_content_chunks() -> None:
    """Role announcement precedes content in separate chunks."""
    session, _ = make_session(RelayFormat.CLAUDE, RelayFormat.OPENAI_CHAT)
    output = run(session, [("role",), ("text", "Hello")])
    chunks = ChatChecker().chunks(output)
    assert chunks[0].choices[0].delta.role == "assistant"
    assert chunks[1].choices[0].delta.content == "Hello"
    assert chunks[0].id == "s1"
    assert chunks[0].model == "gpt-4o"
    assert chunks[0].created == 123


def test_chat_tool_fragments_stay_raw_strings() -> None:
    """Fragments preserve indices and raw argument strings."""
    session, _ = make_session(RelayFormat.GEMINI, RelayFormat.OPENAI_CHAT)
    output = run(
        session,
        [
            ("tool", 0, "call_", None, None),
            ("tool", 0, None, "get_w", None),
            ("tool", 0, None, None, '{"city'),
            ("tool", 0, None, None, '":"SP"}'),
        ],
    )
    chunks = ChatChecker().chunks(output)
    deltas = [c.choices[0].delta for c in chunks if c.choices and c.choices[0].delta]
    fragments = [f for d in deltas for f in (d.tool_calls or [])]
    assert fragments[0] == {"index": 0, "id": "call_", "function": {"name": "get_w"}}
    assert fragments[1] == {"index": 0, "function": {"arguments": '{"city'}}
    assert fragments[2] == {"index": 0, "function": {"arguments": '":"SP"}'}}


def test_chat_finish_and_usage_only_chunk() -> None:
    """Finish emits a terminal chunk; the accumulated usage rides it."""
    session, _ = make_session(RelayFormat.CLAUDE, RelayFormat.OPENAI_CHAT)
    output = run(
        session,
        [("text", "hi"), ("usage", USAGE), ("finish", "length")],
    )
    checker = ChatChecker()
    chunks = checker.chunks(output)
    assert not any(c.usage is not None and not c.choices for c in chunks)
    finish_chunk = [c for c in chunks if c.choices and c.choices[0].finish_reason][0]
    assert finish_chunk.choices[0].finish_reason == "length"
    assert finish_chunk.usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "prompt_tokens_details": {"cached_tokens": 0},
        "completion_tokens_details": {"reasoning_tokens": 0},
        "input_tokens": 10,
        "output_tokens": 0,
    }


# -- Claude emitter -----------------------------------------------------------


def test_claude_block_lifecycle_closes_each_block_once() -> None:
    """Thinking/text/tool blocks start and stop exactly once in order."""
    session, _ = make_session(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE)
    output = total(
        session,
        [
            ("role",),
            ("think", "Let me ", "sig-1"),
            ("think", "think", None),
            ("text", "Hello "),
            ("text", "world"),
            ("tool", 0, "call_123", "get_weather", None),
            ("tool", 0, None, None, '{"city'),
            ("tool", 0, None, None, '":"SP"}'),
            ("finish", "stop"),
        ],
    )
    events = ClaudeChecker().events(output)
    assert events[0].type == "message_start"
    assert events[0].message is not None
    assert events[0].message.id == "s1"
    assert events[0].message.model == "gpt-4o"
    starts = [e for e in events if e.type == "content_block_start"]
    stops = [e for e in events if e.type == "content_block_stop"]
    assert [e.index for e in starts] == [0, 1, 2]
    assert [e.index for e in stops] == [0, 1, 2]
    assert [e.content_block.type for e in starts] == ["thinking", "text", "tool_use"]
    assert starts[2].content_block.tool_use_id == "call_123"
    assert starts[2].content_block.name == "get_weather"
    deltas = [e for e in events if e.type == "content_block_delta"]
    thinking_deltas = [e for e in deltas if e.delta.get("type") == "thinking_delta"]
    assert thinking_deltas[0].delta["signature"] == "sig-1"
    assert ClaudeChecker().blocks_closed(output)
    assert events[-1].type == "message_stop"
    terminal = [e for e in events if e.type == "message_delta"][-1]
    assert terminal.delta == {"stop_reason": "end_turn"}


def test_claude_tool_use_finish_reason() -> None:
    """A tool-call finish maps to Claude's ``tool_use`` stop reason."""
    session, _ = make_session(RelayFormat.GEMINI, RelayFormat.CLAUDE)
    output = total(
        session,
        [
            ("tool", 0, "call_9", "get_temp", None),
            ("tool", 0, None, None, '{"unit":"C"}'),
            ("finish", "tool_calls"),
        ],
    )
    events = ClaudeChecker().events(output)
    terminal = [e for e in events if e.type == "message_delta"][-1]
    assert terminal.delta == {"stop_reason": "tool_use"}
    assert events[-1].type == "message_stop"


def test_claude_usage_rides_message_delta() -> None:
    """Usage mid-stream and at finish appears on message_delta events."""
    session, _ = make_session(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE)
    output = total(
        session,
        [("role",), ("text", "hi"), ("usage", USAGE), ("finish", "stop")],
    )
    usage = ClaudeChecker().usage(output)
    assert usage is not None
    assert usage.output_tokens == 5
    assert usage.input_tokens == 10


def test_claude_usage_after_finish_is_suppressed() -> None:
    """Usage arriving after message_stop emits nothing."""
    session, _ = make_session(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE)
    output = total(
        session,
        [("text", "hi"), ("finish", "stop"), ("usage", USAGE)],
    )
    assert ClaudeChecker().usage(output) is None
    assert ClaudeChecker().events(output)[-1].type == "message_stop"


# -- Gemini emitter -----------------------------------------------------------


def test_gemini_camel_case_wire_fields() -> None:
    """Wire serialization uses camelCase with correct part shapes."""
    session, _ = make_session(RelayFormat.CLAUDE, RelayFormat.GEMINI)
    output = total(
        session,
        [
            ("think", "reasoning ", "sig-x"),
            ("text", "hi"),
            ("tool", 0, "call_123", "get_weather", None),
            ("tool", 0, None, None, '{"city":"SP"}'),
            ("usage", USAGE),
            ("finish", "stop"),
        ],
    )
    chunks = GeminiChecker().chunks(output)
    wire = [c.to_dict() for c in chunks]
    final = wire[-1]
    assert final["candidates"][0]["finishReason"] == "STOP"
    part = final["candidates"][0]["content"]["parts"][0]
    assert part["functionCall"] == {"name": "get_weather", "args": {"city": "SP"}}
    usage = final["usageMetadata"]
    assert usage["promptTokenCount"] == 10
    assert usage["candidatesTokenCount"] == 5
    assert usage["totalTokenCount"] == 15
    thought = [
        c
        for c in wire
        if "candidates" in c
        and c["candidates"][0]["content"]["parts"][0].get("thought")
    ][0]
    thought_part = thought["candidates"][0]["content"]["parts"][0]
    assert thought_part["thoughtSignature"] == "sig-x"


def test_gemini_tool_calls_emitted_on_finish_chunk() -> None:
    """functionCall parts appear on the terminal chunk, in order."""
    session, _ = make_session(RelayFormat.OPENAI_CHAT, RelayFormat.GEMINI)
    session.accept(("role",))
    mid = run(
        session,
        [
            ("tool", 0, "call_a", "get_weather", None),
            ("tool", 0, None, None, '{"city":"SP"}'),
            ("tool", 2, "call_b", "get_temp", None),
            ("tool", 2, None, None, '{"unit":"C"}'),
        ],
    )
    assert GeminiChecker().tool_calls(mid) == []
    output = total(session, [("finish", "stop")])
    calls = GeminiChecker().tool_calls(output)
    assert [call[1] for call in calls] == ["get_weather", "get_temp"]
    assert calls[0][2] == {"city": "SP"}
    assert calls[1][2] == {"unit": "C"}


def test_gemini_finish_reason_mapping() -> None:
    """Canonical reasons map onto Gemini wire values."""
    session, _ = make_session(RelayFormat.CLAUDE, RelayFormat.GEMINI)
    output = total(session, [("text", "hi"), ("finish", "length")])
    assert GeminiChecker().finished(output) == "MAX_TOKENS"
    session, _ = make_session(RelayFormat.CLAUDE, RelayFormat.GEMINI)
    output = total(session, [("text", "hi"), ("finish", "content_filter")])
    assert GeminiChecker().finished(output) == "SAFETY"


# -- Responses emitter --------------------------------------------------------


def test_responses_full_lifecycle_order() -> None:
    """Events follow the Responses stream lifecycle in order."""
    session, _ = make_session(RelayFormat.OPENAI_CHAT, RelayFormat.OPENAI_RESPONSES)
    output = total(
        session,
        [
            ("role",),
            ("think", "let me ", None),
            ("think", "think", None),
            ("text", "Hello "),
            ("text", "world"),
            ("tool", 0, "call_123", "get_weather", None),
            ("tool", 0, None, None, '{"city'),
            ("tool", 0, None, None, '":"SP"}'),
            ("usage", USAGE),
            ("finish", "stop"),
        ],
    )
    types = ResponsesChecker().types(output)
    assert types[0] == "response.created"
    created = [e for e in output if e.type == "response.created"][0]
    assert created.response.id == "stream_fixed"
    assert types.index("response.output_item.added") < types.index(
        "response.reasoning_summary_text.delta"
    )
    assert types.index("response.reasoning_summary_text.delta") < types.index(
        "response.output_text.delta"
    )
    assert types.index("response.output_text.delta") < types.index(
        "response.function_call_arguments.delta"
    )
    assert types.index("response.function_call_arguments.delta") < types.index(
        "response.reasoning_summary_text.done"
    )
    assert types.index("response.reasoning_summary_text.done") < types.index(
        "response.output_text.done"
    )
    assert types.index("response.output_text.done") < types.index(
        "response.function_call_arguments.done"
    )
    assert types.index("response.function_call_arguments.done") < max(
        index for index, t in enumerate(types) if t == "response.output_item.done"
    )
    assert types[-1] == "response.completed"
    assert types.count("response.completed") == 1
    assert "response.in_progress" not in types


def test_responses_indices_and_item_ids() -> None:
    """Output indices are unique and item ids correlate with events."""
    session, _ = make_session(RelayFormat.CLAUDE, RelayFormat.OPENAI_RESPONSES)
    output = total(
        session,
        [
            ("role",),
            ("think", "hmm", None),
            ("text", "hi"),
            ("tool", 0, "call_123", "get_weather", None),
            ("tool", 0, None, None, '{"city":"SP"}'),
            ("finish", "stop"),
        ],
    )
    checker = ResponsesChecker()
    events = checker.events(output)
    added = [e for e in events if e.type == "response.output_item.added"]
    assert [e.output_index for e in added] == [0, 1, 2]
    assert added[0].item.type == "reasoning"
    assert added[1].item.type == "message"
    assert added[2].item.type == "function_call"
    assert added[2].item.call_id == "call_123"
    assert added[2].item.name == "get_weather"
    deltas = [e for e in events if e.type == "response.output_text.delta"]
    assert deltas[0].item_id == added[1].item.id
    assert deltas[0].output_index == 1
    calls = checker.tool_calls(output)
    assert calls == [(0, "call_123", "get_weather", '{"city":"SP"}')]


def test_responses_incomplete_on_length() -> None:
    """A length finish yields response.incomplete with details."""
    session, _ = make_session(RelayFormat.CLAUDE, RelayFormat.OPENAI_RESPONSES)
    output = total(session, [("text", "hi"), ("finish", "length")])
    completed = [e for e in output if e.type == "response.completed"][0]
    assert completed.response.status == "incomplete"
    assert completed.response.incomplete_details.reason == "max_output_tokens"


def test_responses_usage_on_completed() -> None:
    """Usage seen before finish rides the completed event."""
    session, _ = make_session(RelayFormat.CLAUDE, RelayFormat.OPENAI_RESPONSES)
    output = total(
        session,
        [("text", "hi"), ("usage", USAGE), ("finish", "stop")],
    )
    usage = ResponsesChecker().usage(output)
    assert usage is not None
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 5
    assert usage["total_tokens"] == 15


def test_responses_truncated_stream_completes() -> None:
    """A truncated stream ends with response.completed status completed."""
    session, _ = make_session(RelayFormat.GEMINI, RelayFormat.OPENAI_RESPONSES)
    output = total(session, [("text", "partial")])
    types = ResponsesChecker().types(output)
    assert types[0] == "response.created"
    assert types[-1] == "response.completed"
    assert types.count("response.completed") == 1
    completed = [e for e in output if e.type == "response.completed"][0]
    assert completed.response.status == "completed"
    assert completed.response.output[0].content[0]["text"] == "partial"


# -- protocol plumbing --------------------------------------------------------


def test_emitter_receives_accumulated_snapshot() -> None:
    """Emitters see the joined tool-call record, not fragments."""
    session, normalizer = make_session(RelayFormat.OPENAI_CHAT, RelayFormat.OPENAI_CHAT)
    captured: list[Any] = []

    def recorder(
        delta: StreamDelta, *, state: Any
    ) -> Result[tuple[Any, ...], RelayError]:
        captured.append(state)
        return Ok((delta,))

    session.emitter = recorder  # type: ignore[assignment]
    run(
        session,
        [
            ("tool", 0, "call_", None, None),
            ("tool", 0, None, "get_w", None),
            ("tool", 0, None, None, '{"a":1}'),
        ],
    )
    assert normalizer.calls
    assert len(captured) == 3
    last = captured[-1]
    assert last.tool_calls[0].id == "call_"
    assert last.tool_calls[0].name == "get_w"
    assert last.tool_calls[0].arguments == '{"a":1}'
