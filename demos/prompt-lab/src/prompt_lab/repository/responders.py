"""Variant-keyed canned completion styles (Registry dispatch, no LLM)."""

from __future__ import annotations

from collections.abc import Callable

from lexigram.primitives import Registry


def _v1_style(question: str) -> str:
    """Terse canned reply."""
    return f"Order issue noted. Ticket filed for: {question}"


def _v2_style(question: str) -> str:
    """Warm canned reply."""
    return (
        "I'm so sorry about the trouble — I'm happy to help with: "
        f"{question} Let's sort it together."
    )


def _build_responders() -> Registry[str, Callable[[str], str]]:
    """Framework Registry keyed by variant id."""
    registry: Registry[str, Callable[[str], str]] = Registry()
    registry.register("v1", _v1_style)
    registry.register("v2", _v2_style)
    return registry


RESPONDERS: Registry[str, Callable[[str], str]] = _build_responders()
