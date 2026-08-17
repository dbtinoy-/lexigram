"""P3 hook surface import verification for lexigram-ai-skills."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest


def test_skills_hooks_root_module_exists() -> None:
    import lexigram.ai.skills
    from lexigram.ai.skills.hooks import (
        SkillExecutedHook,
        SkillExecutionFailedHook,
        SkillRegisteredHook,
    )

    assert lexigram.ai.skills.SkillRegisteredHook is SkillRegisteredHook
    assert lexigram.ai.skills.SkillExecutedHook is SkillExecutedHook
    assert (
        lexigram.ai.skills.SkillExecutionFailedHook is SkillExecutionFailedHook
    )


def test_skills_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ai.skills.hooks import (
        SkillExecutedHook,
        SkillExecutionFailedHook,
        SkillRegisteredHook,
    )

    registered = SkillRegisteredHook(skill_name="web_search")
    executed = SkillExecutedHook(skill_name="web_search")
    failed = SkillExecutionFailedHook(skill_name="web_search")

    assert is_dataclass(registered)
    assert is_dataclass(executed)
    assert is_dataclass(failed)
    assert [field.name for field in fields(registered)] == ["skill_name"]
    assert [field.name for field in fields(executed)] == ["skill_name"]
    assert [field.name for field in fields(failed)] == ["skill_name"]

    with pytest.raises(TypeError):
        SkillRegisteredHook("web_search")  # type: ignore[misc]

    with pytest.raises(TypeError):
        SkillExecutedHook("web_search")  # type: ignore[misc]

    with pytest.raises(TypeError):
        SkillExecutionFailedHook("web_search")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        registered.skill_name = "math"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        executed.skill_name = "math"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        failed.skill_name = "math"  # type: ignore[misc]
