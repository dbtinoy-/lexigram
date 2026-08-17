"""WebSearchSkill — stub web search via HTTPClientProtocol."""

from __future__ import annotations

from typing import Any

from lexigram.ai.skills.base import AbstractSkill
from lexigram.contracts.ai.skills import SkillDefinition, SkillError, SkillResult
from lexigram.result import Ok, Result


class WebSearchSkill(AbstractSkill):
    """Search the web and return result snippets.

    This is a stub implementation.  Integrate a real search API
    (e.g. Brave, Bing, SerpAPI) by overriding :meth:`execute`.

    Example output::

        {
          "query": "AI trends 2026",
          "results": [],
          "stub": true
        }
    """

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the web_search skill.
        """
        return SkillDefinition(
            name="web_search",
            description=(
                "Search the web for the given query and return relevant result "
                "snippets. (Stub — integrate a real search API for production use.)"
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Defaults to 5.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            category="web",
            permissions=["web.search"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Return an empty result set (stub).

        Args:
            **kwargs: Accepts ``query`` (str) and ``max_results`` (int).

        Returns:
            Ok stub result with empty ``results`` list and ``stub=True``.
        """
        query: str = kwargs.get("query", "")
        return Ok(
            SkillResult(
                skill_name="web_search",
                success=True,
                output={"query": query, "results": [], "stub": True},
            )
        )
