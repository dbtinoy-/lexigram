"""Skill base classes — public API re-exports."""

from __future__ import annotations

from lexigram.ai.skills.base.core import (
    AbstractSkill,
    FunctionSkill,
    SkillToolAdapter,
    ToolSkillAdapter,
)

BaseSkill = AbstractSkill

__all__ = [
    "AbstractSkill",
    "BaseSkill",
    "FunctionSkill",
    "SkillToolAdapter",
    "ToolSkillAdapter",
]
