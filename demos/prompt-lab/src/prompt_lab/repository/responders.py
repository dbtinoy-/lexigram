"""Variant-keyed canned completion styles (registry dispatch, no LLM)."""

from __future__ import annotations

from collections.abc import Callable

RESPONDERS: dict[str, Callable[[str], str]] = {
    "v1": lambda question: f"Order issue noted. Ticket filed for: {question}",
    "v2": lambda question: (
        "I'm so sorry about the trouble — I'm happy to help with: "
        f"{question} Let's sort it together."
    ),
}
