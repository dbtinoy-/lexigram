"""Shared parsing/serialization helpers for the OpenAI Responses mapper."""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.finish_reasons import responses_incomplete_from_finish
from lexigram.contracts.ai.relay.dto import ResponsesIncompleteDetails
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.serialization import dumps_str, loads_str

_TARGET = RelayFormat.OPENAI_RESPONSES


def _parse_arguments(arguments: str) -> dict[str, Any] | str:
    """Parse a wire arguments string into dict form when possible.

    Args:
        arguments: Raw JSON argument string from the wild.

    Returns:
        The parsed dict, or the original string when it is empty or not
        valid JSON.
    """
    if not isinstance(arguments, str) or not arguments.strip():
        return arguments
    try:
        value = loads_str(arguments)
    except (ValueError, TypeError):
        return arguments
    if isinstance(value, dict):
        return value
    return arguments


def _arguments_to_wire(arguments: Any) -> str:
    """Serialize canonical arguments into a JSON string.

    Args:
        arguments: Canonical arguments (dict, string, or anything else).

    Returns:
        A JSON string for the wire, or an empty string when unsupported.
    """
    if isinstance(arguments, dict):
        return dumps_str(arguments)
    if isinstance(arguments, str):
        return arguments
    return ""


def _incomplete_for_finish(
    finish_reason: str | None,
) -> ResponsesIncompleteDetails | None:
    """Map a canonical finish reason to an incomplete-details payload."""
    detail = responses_incomplete_from_finish(finish_reason)
    if detail is None:
        return None
    return ResponsesIncompleteDetails(reason=detail)
