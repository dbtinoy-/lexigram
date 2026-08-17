"""Unified finish-reason and Responses-status mapping tables.

Every canonical ``finish_reason`` -> wire translation for the OpenAI chat,
OpenAI Responses, Claude, and Gemini wire formats lives here so mappers and
emitters never duplicate or drift.  Unknown canonical values fall back to a
safe terminal value rather than raising ``KeyError``; callers that can record
diagnostics attach a ``finish_reason_adapted`` loss around the fallback.
"""

from __future__ import annotations

from collections.abc import Mapping

from lexigram.contracts.ai.relay.ir import normalize_finish_reason
from lexigram.contracts.ai.relay.types import RelayFormat

__all__ = [
    "FINISH_REASON_TO_WIRE",
    "RESPONSES_STATUS_FROM_FINISH",
    "finish_reason_to_wire",
    "normalize_finish_reason",
    "responses_incomplete_from_finish",
    "responses_status_from_finish",
]

#: Canonical finish reason -> wire value per target format.
FINISH_REASON_TO_WIRE: Mapping[str, Mapping[RelayFormat, str]] = {
    "stop": {
        RelayFormat.OPENAI_CHAT: "stop",
        RelayFormat.CLAUDE: "end_turn",
        RelayFormat.GEMINI: "STOP",
    },
    "length": {
        RelayFormat.OPENAI_CHAT: "length",
        RelayFormat.CLAUDE: "max_tokens",
        RelayFormat.GEMINI: "MAX_TOKENS",
    },
    "tool_calls": {
        RelayFormat.OPENAI_CHAT: "tool_calls",
        RelayFormat.CLAUDE: "tool_use",
        RelayFormat.GEMINI: "STOP",
    },
    "function_call": {
        RelayFormat.OPENAI_CHAT: "function_call",
        RelayFormat.CLAUDE: "tool_use",
        RelayFormat.GEMINI: "STOP",
    },
    "content_filter": {
        RelayFormat.OPENAI_CHAT: "content_filter",
        RelayFormat.CLAUDE: "end_turn",
        RelayFormat.GEMINI: "SAFETY",
    },
    "other": {
        RelayFormat.OPENAI_CHAT: "other",
        RelayFormat.CLAUDE: "end_turn",
        RelayFormat.GEMINI: "OTHER",
    },
}

#: Safe terminal value per format for canonical values absent from the table.
_WIRE_FALLBACK: Mapping[RelayFormat, str] = {
    RelayFormat.OPENAI_CHAT: "stop",
    RelayFormat.CLAUDE: "end_turn",
    RelayFormat.GEMINI: "OTHER",
}

#: Canonical finish reason -> (Responses status, incomplete-detail reason).
RESPONSES_STATUS_FROM_FINISH: Mapping[str, tuple[str, str | None]] = {
    "stop": ("completed", None),
    "tool_calls": ("completed", None),
    "function_call": ("completed", None),
    "length": ("incomplete", "max_output_tokens"),
    "content_filter": ("incomplete", "content_filter"),
    "other": ("incomplete", "other"),
}


def finish_reason_to_wire(finish_reason: str | None, target: RelayFormat) -> str:
    """Map a canonical finish reason onto ``target``'s wire value.

    Unknown or missing values fall back to the target's terminal value
    rather than raising ``KeyError``.
    """
    if finish_reason is None:
        return _WIRE_FALLBACK[target]
    row = FINISH_REASON_TO_WIRE.get(finish_reason)
    if row is None:
        return _WIRE_FALLBACK[target]
    return row.get(target, _WIRE_FALLBACK[target])


def responses_status_from_finish(
    finish_reason: str | None,
) -> tuple[str, str | None]:
    """Derive a Responses status and incomplete-detail reason."""
    if finish_reason is None:
        return "completed", None
    return RESPONSES_STATUS_FROM_FINISH.get(finish_reason, ("completed", None))


def responses_incomplete_from_finish(finish_reason: str | None) -> str | None:
    """Return the Responses incomplete-detail reason, or ``None``."""
    if finish_reason is None:
        return None
    _status, detail = RESPONSES_STATUS_FROM_FINISH.get(
        finish_reason, ("completed", None)
    )
    return detail
