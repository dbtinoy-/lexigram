"""Tests for the OpenAI Responses stream emitter.

Verifies event lifecycle ordering, output indices/item ids, the
incomplete status on length finishes, usage placement, and truncated
stream completion.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay.types import RelayFormat

from ._stream_emitters_support import (
    USAGE,
    ResponsesChecker,
    make_session,
    total,
)


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
