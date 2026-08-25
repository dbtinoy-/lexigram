"""12-direction stream relay tests.

Drives every source/target direction (4x4 minus diagonal) through the
session state machine and verifies text/thinking, tool-call, usage,
and truncated-finalization behavior per target format.
"""

from __future__ import annotations

import pytest

from lexigram.contracts.ai.relay.types import RelayFormat

from ._stream_emitters_support import (
    CHECKERS,
    DIRECTIONS,
    USAGE,
    make_session,
    total,
)


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
