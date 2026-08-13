"""Unified finish-reason mapping table (Task 12 Step 3)."""

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.finish_reasons import (
    FINISH_REASON_TO_WIRE,
    finish_reason_to_wire,
    normalize_finish_reason,
    responses_incomplete_from_finish,
    responses_status_from_finish,
)
from lexigram.contracts.ai.relay.types import RelayFormat


@pytest.fixture
def ctx() -> ConversionContext:
    return ConversionContext()


def test_table_covers_all_canonical_values() -> None:
    """Every canonical finish reason maps to every supported format."""
    canonical = {
        "stop",
        "length",
        "tool_calls",
        "function_call",
        "content_filter",
        "other",
    }
    assert set(FINISH_REASON_TO_WIRE) == canonical
    for finish in canonical:
        row = FINISH_REASON_TO_WIRE[finish]
        assert set(row) == {
            RelayFormat.OPENAI_CHAT,
            RelayFormat.CLAUDE,
            RelayFormat.GEMINI,
        }


@pytest.mark.parametrize(
    ("finish", "expected"),
    [
        ("stop", "stop"),
        ("length", "length"),
        ("tool_calls", "tool_calls"),
        ("function_call", "function_call"),
        ("content_filter", "content_filter"),
        ("other", "other"),
    ],
)
def test_openai_chat_values(finish: str, expected: str) -> None:
    assert finish_reason_to_wire(finish, RelayFormat.OPENAI_CHAT) == expected


@pytest.mark.parametrize(
    ("finish", "expected"),
    [
        ("stop", "end_turn"),
        ("length", "max_tokens"),
        ("tool_calls", "tool_use"),
        ("function_call", "tool_use"),
        ("content_filter", "end_turn"),
        ("other", "end_turn"),
    ],
)
def test_claude_values(finish: str, expected: str) -> None:
    assert finish_reason_to_wire(finish, RelayFormat.CLAUDE) == expected


@pytest.mark.parametrize(
    ("finish", "expected"),
    [
        ("stop", "STOP"),
        ("length", "MAX_TOKENS"),
        ("tool_calls", "STOP"),
        ("function_call", "STOP"),
        ("content_filter", "SAFETY"),
        ("other", "OTHER"),
    ],
)
def test_gemini_values(finish: str, expected: str) -> None:
    assert finish_reason_to_wire(finish, RelayFormat.GEMINI) == expected


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (RelayFormat.OPENAI_CHAT, "stop"),
        (RelayFormat.CLAUDE, "end_turn"),
        (RelayFormat.GEMINI, "OTHER"),
    ],
)
def test_unknown_finish_falls_back(target: RelayFormat, expected: str) -> None:
    """Unknown canonical values fall back instead of raising KeyError."""
    assert finish_reason_to_wire("teleport", target) == expected
    assert finish_reason_to_wire(None, target) == expected


@pytest.mark.parametrize(
    ("finish", "status", "detail"),
    [
        ("stop", "completed", None),
        ("tool_calls", "completed", None),
        ("function_call", "completed", None),
        ("length", "incomplete", "max_output_tokens"),
        ("content_filter", "incomplete", "content_filter"),
        ("other", "incomplete", "other"),
    ],
)
def test_responses_status_mapping(finish: str, status: str, detail: str | None) -> None:
    assert responses_status_from_finish(finish) == (status, detail)


def test_responses_unknown_and_none_default_to_completed() -> None:
    assert responses_status_from_finish("teleport") == ("completed", None)
    assert responses_status_from_finish(None) == ("completed", None)


def test_responses_incomplete_details() -> None:
    assert responses_incomplete_from_finish("length") == "max_output_tokens"
    assert responses_incomplete_from_finish("content_filter") == "content_filter"
    assert responses_incomplete_from_finish("other") == "other"
    assert responses_incomplete_from_finish("stop") is None
    assert responses_incomplete_from_finish(None) is None


def test_normalize_wire_values_to_canonical() -> None:
    assert normalize_finish_reason("end_turn") == "stop"
    assert normalize_finish_reason("max_tokens") == "length"
    assert normalize_finish_reason("tool_use") == "tool_calls"
    assert normalize_finish_reason("STOP") == "stop"
    assert normalize_finish_reason("safety") == "content_filter"
    assert normalize_finish_reason("teleport") == "other"
    assert normalize_finish_reason(None) is None
