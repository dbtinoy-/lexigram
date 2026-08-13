"""ConditionalSkill — dispatches to one of two skills based on a runtime condition."""

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


class ConditionalSkill:
    """Execute one of two skills based on a runtime condition.

    Unlike :class:`~lexigram.ai.skills.composition.router.SkillRouter`, which
    evaluates an ordered list of routes, ``ConditionalSkill`` models a simple
    if/else branch: one skill is chosen when the condition is truthy, an
    optional second skill when it is falsy.

    Example::

        skill = ConditionalSkill(
            condition=lambda p: p.get("premium", False),
            if_true="premium_search",
            if_false="basic_search",
        )
        result = await skill.execute(executor, {"query": "...", "premium": True})

    When *if_false* is omitted and the condition evaluates to ``False``, an
    :class:`~lexigram.ai.skills.exceptions.SkillRoutingError` is returned
    wrapped in ``Err``.
    """

    def __init__(
        self,
        condition: Condition,
        if_true: str,
        if_false: str | None = None,
    ) -> None:
        """Initialise the conditional skill.

        Args:
            condition: Callable receiving the input ``dict`` returning ``bool``.
            if_true: Skill name to execute when *condition* returns truthy.
            if_false: Skill name to execute when *condition* returns falsy.
                If ``None`` and the condition is falsy, an error is returned.
        """
        self._condition = condition
        self._if_true = if_true
        self._if_false = if_false

    async def execute(
        self,
        executor: Any,
        params: dict[str, Any],
    ) -> Result[SkillResult, SkillError]:
        """Execute the chosen skill based on the evaluated condition.

        Args:
            executor: SkillExecutorProtocol instance used to run the resolved skill.
            params: Input parameters that are passed to the resolved skill and
                also forwarded to the condition callable.

        Returns:
            ``Ok(SkillResult)`` from the chosen skill on success.
            ``Err(SkillError)`` when the condition evaluation raises or when the
            condition is falsy and no *if_false* skill is configured.
        """
        try:
            matched = bool(self._condition(params))
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            logger.warning(
                "conditional_skill_condition_error",
                if_true=self._if_true,
                if_false=self._if_false,
                error=str(exc),
            )
            return Err(SkillRoutingError(f"Condition evaluation failed: {exc}"))

        if matched:
            logger.debug(
                "conditional_skill_branch", branch="if_true", skill=self._if_true
            )
            return await executor.execute(self._if_true, params)

        if self._if_false is not None:
            logger.debug(
                "conditional_skill_branch", branch="if_false", skill=self._if_false
            )
            return await executor.execute(self._if_false, params)

        return Err(
            SkillRoutingError(
                f"Condition was False and no if_false skill is configured "
                f"(if_true='{self._if_true}')"
            )
        )
