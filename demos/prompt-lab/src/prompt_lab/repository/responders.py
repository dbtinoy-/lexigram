"""Variant-keyed canned completion styles (registry dispatch, no LLM)."""

from __future__ import annotations

from collections.abc import Callable

from lexigram.primitives import Registry

_V1_STYLE: Callable[[str], str] = lambda question: (
    f"Order issue noted. Ticket filed for: {question}"
)
_V2_STYLE: Callable[[str], str] = lambda question: (
    "I'm so sorry about the trouble — I'm happy to help with: "
    f"{question} Let's sort it together."
)


def _build_responders() -> Registry[str, Callable[[str], str]]:
    """Framework Registry keyed by variant id."""
    registry: Registry[str, Callable[[str], str]] = Registry()
    registry.register("v1", _V1_STYLE)
    registry.register("v2", _V2_STYLE)
    return registry


RESPONDERS: Registry[str, Callable[[str], str]] = _build_responders()
