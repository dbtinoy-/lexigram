"""Tests for SkillRegistry."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.registry import SkillRegistry
from lexigram.ai.skills.exceptions import (
    SkillAlreadyRegisteredError,
    SkillNotFoundError,
)
from unittest.mock import MagicMock


class TestSkillRegistry:
    """Test SkillRegistry registration and lookup."""

    def test_empty_registry(self) -> None:
        """New registry should be empty."""
        registry = SkillRegistry()

        assert registry.get("any_skill") is None
        assert registry.list_skills() == []

    def test_register_skill(self) -> None:
        """Registry should register and retrieve skills."""
        registry = SkillRegistry()
        skill = MagicMock()
        skill.definition.name = "test_skill"
        skill.definition.category = "testing"
        skill.definition.permissions = []

        registry.register(skill)

        assert registry.get("test_skill") == skill

    def test_register_duplicate_raises_error(self) -> None:
        """Registering a skill with duplicate name should raise error."""
        registry = SkillRegistry()
        skill1 = MagicMock()
        skill1.definition.name = "test_skill"
        skill1.definition.category = "testing"
        skill1.definition.permissions = []

        skill2 = MagicMock()
        skill2.definition.name = "test_skill"
        skill2.definition.category = "testing"
        skill2.definition.permissions = []

        registry.register(skill1)

        with pytest.raises(SkillAlreadyRegisteredError):
            registry.register(skill2)

    def test_list_all_skills(self) -> None:
        """list_skills() should return all registered skills."""
        registry = SkillRegistry()

        # Register 3 skills
        for i in range(3):
            skill = MagicMock()
            skill.definition.name = f"skill_{i}"
            skill.definition.category = "testing"
            skill.definition.permissions = []
            registry.register(skill)

        definitions = registry.list_skills()

        assert len(definitions) == 3
        assert all(d.name.startswith("skill_") for d in definitions)

    def test_list_skills_by_category(self) -> None:
        """list_skills() should filter by category."""
        registry = SkillRegistry()

        # Register skills in different categories
        skill1 = MagicMock()
        skill1.definition.name = "math_skill"
        skill1.definition.category = "math"
        skill1.definition.permissions = []

        skill2 = MagicMock()
        skill2.definition.name = "string_skill"
        skill2.definition.category = "string"
        skill2.definition.permissions = []

        registry.register(skill1)
        registry.register(skill2)

        math_skills = registry.list_skills(category="math")

        assert len(math_skills) == 1
        assert math_skills[0].name == "math_skill"

    def test_list_skills_by_permissions(self) -> None:
        """list_skills() should filter by required permissions."""
        registry = SkillRegistry()

        # Register skill with permissions
        skill_admin = MagicMock()
        skill_admin.definition.name = "admin_skill"
        skill_admin.definition.category = "admin"
        skill_admin.definition.permissions = ["admin", "write"]

        skill_public = MagicMock()
        skill_public.definition.name = "public_skill"
        skill_public.definition.category = "public"
        skill_public.definition.permissions = []

        registry.register(skill_admin)
        registry.register(skill_public)

        # User with no permissions can only see public skill
        user_skills = registry.list_skills(permissions=[])
        assert len(user_skills) == 1
        assert user_skills[0].name == "public_skill"

        # User with admin permission can see both
        admin_skills = registry.list_skills(permissions=["admin", "write"])
        assert len(admin_skills) == 2

    def test_get_nonexistent_skill_returns_none(self) -> None:
        """get() should return None for non-existent skills."""
        registry = SkillRegistry()

        assert registry.get("nonexistent") is None

    def test_categories_tracking(self) -> None:
        """Registry should track skills by category."""
        registry = SkillRegistry()

        skill1 = MagicMock()
        skill1.definition.name = "skill1"
        skill1.definition.category = "cat_a"
        skill1.definition.permissions = []

        skill2 = MagicMock()
        skill2.definition.name = "skill2"
        skill2.definition.category = "cat_a"
        skill2.definition.permissions = []

        skill3 = MagicMock()
        skill3.definition.name = "skill3"
        skill3.definition.category = "cat_b"
        skill3.definition.permissions = []

        registry.register(skill1)
        registry.register(skill2)
        registry.register(skill3)

        cat_a_skills = registry.list_skills(category="cat_a")
        cat_b_skills = registry.list_skills(category="cat_b")

        assert len(cat_a_skills) == 2
        assert len(cat_b_skills) == 1

    def test_multiple_filters(self) -> None:
        """list_skills() should apply category and permission filters together."""
        registry = SkillRegistry()

        skill1 = MagicMock()
        skill1.definition.name = "skill1"
        skill1.definition.category = "admin"
        skill1.definition.permissions = ["admin"]

        skill2 = MagicMock()
        skill2.definition.name = "skill2"
        skill2.definition.category = "admin"
        skill2.definition.permissions = ["superadmin"]

        registry.register(skill1)
        registry.register(skill2)

        # Filter by category and permissions
        results = registry.list_skills(category="admin", permissions=["admin"])
        assert len(results) == 1
        assert results[0].name == "skill1"


class TestSkillRegistryExceptions:
    """Test SkillRegistry exception handling."""

    def test_duplicate_registration_exception_message(self) -> None:
        """SkillAlreadyRegisteredError should have meaningful message."""
        registry = SkillRegistry()

        skill = MagicMock()
        skill.definition.name = "test_skill"
        skill.definition.category = "testing"
        skill.definition.permissions = []

        registry.register(skill)

        with pytest.raises(SkillAlreadyRegisteredError) as exc_info:
            registry.register(skill)

        assert "test_skill" in str(exc_info.value)
