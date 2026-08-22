"""Scripted two-session conversation replayed by the demo act."""

from __future__ import annotations

DEMO_REPLAY: list[tuple[str, str]] = [
    ("alice", "I'm vegetarian"),
    ("alice", "I'm allergic to peanuts"),
    ("alice", "Suggest a dinner menu"),
    ("bob", "What do you remember about me?"),
    ("bob", "Suggest a dinner menu"),
]
