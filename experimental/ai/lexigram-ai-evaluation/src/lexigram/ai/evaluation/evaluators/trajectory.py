"""Agent trajectory evaluator."""

from __future__ import annotations

from typing import Any

from lexigram.ai.evaluation.evaluators.base import BaseEvaluator
from lexigram.contracts.ai.evaluation import (
    EvaluationResult,
    EvaluationScoreType,
    EvaluatorProtocol,
)
from lexigram.contracts.ai.exceptions import EvaluationError
from lexigram.logging import get_logger
from lexigram.result import Ok, Result

logger = get_logger(__name__)


class TrajectoryEvaluator(BaseEvaluator, EvaluatorProtocol):
    """Agent trajectory fidelity evaluation.

    Evaluates whether an agent's execution trajectory follows the
    expected path and reaches the expected final state.
    """

    def __init__(self) -> None:
        super().__init__(EvaluationScoreType.TRAJECTORY_FIDELITY)

    @property
    def name(self) -> str:
        return "trajectory"

    async def evaluate(
        self,
        input: str,
        output: str,
        reference: str,
    ) -> Result[EvaluationResult, Exception]:
        details: dict[str, Any] = {}

        try:
            from lexigram.serialization import loads as json_loads

            output_trajectory = json_loads(output)
            reference_trajectory = json_loads(reference)
        except (ValueError, EvaluationError) as e:
            return Ok(
                self._create_result(
                    0.0,
                    "Invalid trajectory format: expected JSON",
                    {"error": "invalid_json"},
                )
            )

        steps_score = self._evaluate_steps(
            output_trajectory.get("steps", []),
            reference_trajectory.get("steps", []),
        )
        final_state_score = self._evaluate_final_state(
            output_trajectory.get("final_state", {}),
            reference_trajectory.get("final_state", {}),
        )

        score = (steps_score + final_state_score) / 2.0

        details = {
            "steps_score": steps_score,
            "final_state_score": final_state_score,
            "output_steps": len(output_trajectory.get("steps", [])),
            "reference_steps": len(reference_trajectory.get("steps", [])),
        }

        feedback = f"Trajectory fidelity: {score:.2f}"

        return Ok(self._create_result(score, feedback, details))

    def _evaluate_steps(
        self,
        output_steps: list[dict[str, Any]],
        reference_steps: list[dict[str, Any]],
    ) -> float:
        if not reference_steps:
            return 1.0 if output_steps else 0.0

        correct = 0
        for i, ref_step in enumerate(reference_steps):
            if i < len(output_steps):
                out_step = output_steps[i]
                if self._step_matches(out_step, ref_step):
                    correct += 1

        return correct / len(reference_steps)

    def _step_matches(
        self,
        output_step: dict[str, Any],
        reference_step: dict[str, Any],
    ) -> bool:
        action_match = output_step.get("action") == reference_step.get("action")
        if not action_match:
            return False

        if "tool" in reference_step:
            return output_step.get("tool") == reference_step.get("tool")

        return True

    def _evaluate_final_state(
        self,
        output_state: dict[str, Any],
        reference_state: dict[str, Any],
    ) -> float:
        if not reference_state:
            return 1.0

        matches = 0
        total = len(reference_state)

        for key, expected_value in reference_state.items():
            if key in output_state:
                if output_state[key] == expected_value:
                    matches += 1

        return matches / total if total > 0 else 0.0


__all__ = ["TrajectoryEvaluator"]
