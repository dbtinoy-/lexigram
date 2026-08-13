"""SkillRouter — conditional dispatch to skills based on input-matching rules."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from lexigram.ai.skills.exceptions import SkillRoutingError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.skills import SkillError, SkillResult

logger = get_logger(__name__)


Condition = Callable[[dict[str, Any]], bool]


class SkillRouter:
    """Route an input to one of several skills depending on runtime conditions.

    Routes are evaluated in registration order; the first match wins.
    An optional *fallback* skill name is used when no route matches.

    Example::

        router = SkillRouter(fallback="default_handler")
        router.add_route(
            skill_name="premium_search",
            condition=lambda p: p.get("tier") == "premium",
        )
        router.add_route(
            skill_name="basic_search",
            condition=lambda p: True,        # catch-all
        )
        result = await router.execute(executor, {"query": "...", "tier": "free"})
    """

    def __init__(self, fallback: str | None = None) -> None:
        """Initialise the router.

        Args:
            fallback: Skill name to use when no route matches.  If ``None``
                and no route matches, the execution returns an error.
        """
        self._routes: list[tuple[Condition, str]] = []
        self._fallback = fallback

    def add_route(self, skill_name: str, condition: Condition) -> None:
        """Register a route.

        Args:
            skill_name: Name of the skill to invoke if *condition* returns True.
            condition: Callable receiving the input ``dict`` returning ``bool``.
        """
        self._routes.append((condition, skill_name))

    async def execute(
        self,
        executor: Any,
        params: dict[str, Any],
    ) -> Result[SkillResult, SkillError]:
        """Dispatch *params* to the first matching skill.

        Args:
            executor: SkillExecutorProtocol instance.
            params: Input parameters used both for condition evaluation and
                forwarded to the resolved skill.

        Returns:
            Result from the matched skill, or a SkillRoutingError when no
            route matches and no fallback is configured.
        """
        for condition, skill_name in self._routes:
            try:
                matched = condition(params)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "skill_router_condition_error",
                    skill=skill_name,
                    error=str(exc),
                )
                continue
            if matched:
                logger.debug("skill_router_matched", skill=skill_name)
                return await executor.execute(skill_name, params)

        if self._fallback:
            logger.debug("skill_router_fallback", skill=self._fallback)
            return await executor.execute(self._fallback, params)

        return Err(
            SkillRoutingError(f"No route matched for params: {list(params.keys())}")
        )
