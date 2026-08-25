"""Tests for the Gemini stream emitter.

Verifies camelCase wire serialization, tool-call emission on the
finish chunk, and canonical finish-reason mapping.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay.types import RelayFormat

from ._stream_emitters_support import (
    USAGE,
    GeminiChecker,
    make_session,
    run,
    total,
)


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
