"""Root hook payload surface for lexigram-ai-skills."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SkillExecutedHook",
    "SkillExecutionFailedHook",
    "SkillRegisteredHook",
]


@dataclass(frozen=True, kw_only=True)
class SkillRegisteredHook:
    """Payload fired when a skill registry adds a skill definition."""

    skill_name: str


@dataclass(frozen=True, kw_only=True)
class SkillExecutedHook:
    """Payload fired when a skill executor completes a skill call."""

    skill_name: str


@dataclass(frozen=True, kw_only=True)
class SkillExecutionFailedHook:
    """Payload fired when a skill executor records a failed skill call."""

    skill_name: str
