"""SkillChain — sequential skill execution pipeline."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.skills import SkillError, SkillResult
from lexigram.result import Err, Result


class SkillChain:
    """Execute skills sequentially, piping each output into the next input.

    Each step is a ``(skill_name, output_mapping)`` tuple where
    *output_mapping* maps keys from the previous output dict to parameter
    names for the next skill.  An empty mapping passes all keys unchanged.

    Example::

        chain = SkillChain([
            ("web_search", {"results": "documents"}),
            ("text_summarize", {}),
        ])
        result = await chain.execute(executor, {"query": "AI trends 2026"})
    """

    def __init__(self, steps: list[tuple[str, dict[str, str]]]) -> None:
        """Initialise the chain with its steps.

        Args:
            steps: List of ``(skill_name, output_to_input_mapping)`` tuples.
        """
        self._steps = steps

    async def execute(
        self,
        executor: Any,
        initial_params: dict[str, Any],
    ) -> Result[SkillResult, SkillError]:
        """Execute the chain from *initial_params*.

        Args:
            executor: SkillExecutorProtocol instance used to run each step.
            initial_params: Parameters passed to the first skill.

        Returns:
            Result from the final step, or the first error encountered.
        """
        current_params = dict(initial_params)
        result: Result[SkillResult, SkillError] | None = None

        for skill_name, mapping in self._steps:
            result = await executor.execute(skill_name, current_params)
            if result.is_err():
                return result
            output = result.unwrap().output or {}
            if isinstance(output, dict):
                current_params = {}
                for k, v in output.items():
                    if k is not None:
                        current_params[mapping.get(k, k)] = v  # type: ignore[index]
            else:
                current_params = {"output": output}

        if result is None:
            return Err(SkillError("Empty chain"))
        return result
