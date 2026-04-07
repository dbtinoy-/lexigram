"""SkillRegistry — central catalog for registering and discovering skills."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.skills.exceptions import SkillAlreadyRegisteredError
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.agents import ToolProtocol
    from lexigram.contracts.ai.skills import SkillDefinition, SkillProtocol

logger = get_logger(__name__)


class SkillRegistry:
    """Central registry for all available skills.

    Supports registration, lookup by name, category-based listing,
    permission-filtered listing, and OpenAI function-calling schema export.
    """

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._skills: dict[str, SkillProtocol] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, skill: SkillProtocol) -> None:
        """Register a skill.

        Args:
            skill: The skill to register.

        Raises:
            SkillAlreadyRegisteredError: If a skill with the same name is already registered.
        """
        name = skill.definition.name
        if name in self._skills:
            raise SkillAlreadyRegisteredError(name)
        self._skills[name] = skill
        cat = skill.definition.category
        self._categories.setdefault(cat, []).append(name)
        logger.debug("skill_registered", name=name, category=cat)

    def register_tool(self, tool: ToolProtocol) -> None:
        """Wrap *tool* as a :class:`~lexigram.ai.skills.base.ToolSkillAdapter` and register it.

        Args:
            tool: Any object satisfying ToolProtocol.
        """
        from lexigram.ai.skills.base import ToolSkillAdapter

        self.register(ToolSkillAdapter(tool))

    def get(self, name: str) -> SkillProtocol | None:
        """Return the skill registered under *name*, or ``None``.

        Args:
            name: Skill name to look up.

        Returns:
            The skill or None if not found.
        """
        return self._skills.get(name)

    def list_skills(
        self,
        category: str | None = None,
        permissions: list[str] | None = None,
    ) -> list[SkillDefinition]:
        """List registered skill definitions with optional filters.

        Args:
            category: Return only skills in this category.
            permissions: Return only skills whose required permissions are a
                subset of the supplied permission set.

        Returns:
            Matching skill definitions.
        """
        skills = list(self._skills.values())

        if category is not None:
            names_in_cat = set(self._categories.get(category, []))
            skills = [s for s in skills if s.definition.name in names_in_cat]

        if permissions is not None:
            user_perms = set(permissions)
            skills = [
                s for s in skills if set(s.definition.permissions).issubset(user_perms)
            ]

        return [s.definition for s in skills]

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI function-calling compatible schemas for all skills.

        Returns:
            List of schema dicts in OpenAI ``tools`` format.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": s.definition.name,
                    "description": s.definition.description,
                    "parameters": s.definition.parameters_schema,
                },
            }
            for s in self._skills.values()
        ]

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills


__all__ = ["SkillRegistry"]
