"""Root hook payload surface for lexigram-ai-guard."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GuardInputCheckedHook",
    "GuardOutputCheckedHook",
    "GuardPipelineCompletedHook",
]


@dataclass(frozen=True, kw_only=True)
class GuardInputCheckedHook:
    """Payload fired after an input guard evaluates content."""

    guard_name: str
    blocked: bool


@dataclass(frozen=True, kw_only=True)
class GuardOutputCheckedHook:
    """Payload fired after an output guard evaluates content."""

    guard_name: str
    blocked: bool


@dataclass(frozen=True, kw_only=True)
class GuardPipelineCompletedHook:
    """Payload fired after the guard pipeline finishes a full pass."""

    blocked: bool
