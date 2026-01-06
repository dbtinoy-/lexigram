"""SkillPipeline — data transformation pipeline."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.skills import SkillError, SkillResult
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Ok, Result

logger = get_logger(__name__)


class SkillPipeline:
    """Apply a sequence of skills as transformation stages to the same payload.

    Unlike :class:`SkillChain` which passes the *output* of one skill as the
    *input* of the next, a pipeline enriches a single mutable context dict;
    each stage may read from and write to that shared context.

    Example::

        pipeline = SkillPipeline()
        pipeline.add_stage("normalise_text", output_key="clean")
        pipeline.add_stage("extract_entities", output_key="entities")
        result = await pipeline.execute(executor, {"raw_text": "..."})
        # result.unwrap().output == {"raw_text": ..., "clean": ..., "entities": ...}
    """

    def __init__(self) -> None:
        """Initialise an empty pipeline."""
        self._stages: list[tuple[str, str | None]] = []

    def add_stage(self, skill_name: str, output_key: str | None = None) -> None:
        """Append a stage to the pipeline.

        Args:
            skill_name: Skill to invoke at this stage.
            output_key: If given, the skill's output is stored in the shared
                context under this key.  If ``None`` the output dict is merged
                into the context (ignored for non-dict outputs).
        """
        self._stages.append((skill_name, output_key))

    async def execute(
        self,
        executor: Any,
        initial_context: dict[str, Any],
    ) -> Result[SkillResult, SkillError]:
        """Run the pipeline.

        Args:
            executor: SkillExecutorProtocol instance.
            initial_context: Shared context passed to (and enriched by) each stage.

        Returns:
            A SkillResult whose ``output`` is the final enriched context, or the
            first error encountered.
        """
        context = dict(initial_context)
        skill_name = ""

        for skill_name, output_key in self._stages:
            result = await executor.execute(skill_name, context)
            if result.is_err():
                return result

            stage_output = result.unwrap().output
            if output_key is not None:
                context[output_key] = stage_output
            elif isinstance(stage_output, dict):
                context.update(stage_output)

        return Ok(
            SkillResult(
                skill_name=skill_name or "pipeline",
                success=True,
                output=context,
            )
        )
