"""Skills executor service using Result pattern."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import SkillError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class SkillExecutorWithResultPattern:
    """Skills executor using Result pattern."""

    async def execute(self, skill_name: str, params: dict) -> Result[dict, SkillError]:
        """Execute a skill."""
        try:
            if not skill_name:
                return Err(SkillError("Skill name cannot be empty"))
            result = {"skill": skill_name, "params": params, "output": "executed"}
            logger.info("skill_executed", skill=skill_name)
            return Ok(result)
        except Exception as e:  # noqa: BLE001  # skill execution can raise any exception; surfaced as Err
            logger.error("skill_execution_failed: %s", e)
            return Err(SkillError(f"Skill execution failed: {e}"))


__all__ = ["SkillExecutorWithResultPattern"]
