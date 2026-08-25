"""Tests for the OpenAI Chat stream emitter.

Verifies chunk ordering, raw tool-fragment preservation, and the
finish/usage terminal chunk shape.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay.types import RelayFormat

from ._stream_emitters_support import (
    USAGE,
    ChatChecker,
    make_session,
    run,
)


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
