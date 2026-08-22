"""Seeded evaluation cases; references favor v2 deterministically."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    """One scored scenario."""

    id: str
    question: str
    reference: str


CASES: list[Case] = [
    Case("billing", "My card was charged twice.", "happy to help"),
    Case("shipping", "Where is my order?", "happy to help"),
    Case("bug", "The app crashes on login.", "happy to help"),
    Case("feature", "Can you add dark mode?", "happy to help"),
]

CRITERIA = [{"type": "contains", "expected": "happy to help"}]
