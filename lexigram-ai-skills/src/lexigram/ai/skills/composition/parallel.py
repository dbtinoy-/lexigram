"""ParallelSkills — fan-out concurrent skill execution."""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.contracts.ai.skills import SkillError, SkillResult
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Ok, Result

logger = get_logger(__name__)


class ParallelSkills:
    """Execute multiple skills concurrently and aggregate their outputs.

    All skills receive the same *params*.  Errors from individual skills do
    not abort the fan-out; they are collected and returned as part of the
    aggregated output dict under an ``"_errors"`` key.

    Example::

        parallel = ParallelSkills(["sentiment_analysis", "entity_extraction"])
        result = await parallel.execute(executor, {"text": "Hello world"})
        combined = result.unwrap().output
        # combined == {"sentiment_analysis": {...}, "entity_extraction": {...}}
    """

    def __init__(self, skill_names: list[str]) -> None:
        """Initialise with the skills to run in parallel.

        Args:
            skill_names: Names of skills to execute concurrently.
        """
        self._skill_names = list(skill_names)

    async def execute(
        self,
        executor: Any,
        params: dict[str, Any],
    ) -> Result[SkillResult, SkillError]:
        """Run all skills concurrently and aggregate results.

        Args:
            executor: SkillExecutorProtocol instance.
            params: Input parameters forwarded to every skill.

        Returns:
            A SkillResult whose ``output`` is a dict mapping each skill name
            to its output (or an error string if that skill failed).
        """
        tasks = [executor.execute(name, params) for name in self._skill_names]
        results: list[Result[SkillResult, SkillError]] = await asyncio.gather(*tasks)

        combined: dict[str, Any] = {}
        errors: dict[str, str] = {}

        for name, result in zip(self._skill_names, results, strict=False):
            if result.is_ok():
                combined[name] = result.unwrap().output
            else:
                errors[name] = str(result.unwrap_err())
                logger.warning("parallel_skill_error", skill=name, error=errors[name])

        if errors:
            combined["_errors"] = errors

        return Ok(
            SkillResult(
                skill_name="parallel",
                success=True,
                output=combined,
            )
        )
