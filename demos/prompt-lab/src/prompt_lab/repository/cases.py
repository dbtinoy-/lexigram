"""Seeded evaluation cases — references favour v2 deterministically.

Each ``Case`` pairs a customer question with a reference phrase that
the evaluation harness checks for.  All four cases reference
``"happy to help"`` — v2's empathetic few-shot template always includes
it, while v1's terse instruction never does, so v2 scores 1.0 and
v1 scores 0.0 on every run.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CASES", "CRITERIA", "Case"]


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
