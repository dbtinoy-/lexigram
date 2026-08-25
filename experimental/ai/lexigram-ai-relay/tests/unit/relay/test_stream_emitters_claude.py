"""Tests for the Claude stream emitter.

Verifies content-block lifecycle, tool_use stop reasons, and usage
placement on message_delta events.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay.types import RelayFormat

from ._stream_emitters_support import (
    USAGE,
    ClaudeChecker,
    make_session,
    total,
)


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
