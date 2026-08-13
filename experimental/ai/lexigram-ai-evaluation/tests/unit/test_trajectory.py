"""Tests for TrajectoryEvaluator."""

from __future__ import annotations

import json

import pytest

from lexigram.ai.evaluation.evaluators.trajectory import TrajectoryEvaluator
from lexigram.contracts.ai.evaluation import EvaluationScoreType


def _json(data: object) -> str:
    return json.dumps(data)


class TestTrajectoryEvaluator:
    """Tests for agent trajectory fidelity evaluation."""

    def test_name_returns_trajectory(self) -> None:
        assert TrajectoryEvaluator().name == "trajectory"

    def test_score_type_is_trajectory_fidelity(self) -> None:
        assert TrajectoryEvaluator()._score_type == EvaluationScoreType.TRAJECTORY_FIDELITY

    @pytest.mark.asyncio
    async def test_invalid_json_returns_zero_score(self) -> None:
        evaluator = TrajectoryEvaluator()
        result = await evaluator.evaluate("input", "not-json", "also-not-json")
        assert result.is_ok()
        assert result.unwrap().score == 0.0
        assert result.unwrap().metrics.get("error") == "invalid_json"

    @pytest.mark.asyncio
    async def test_perfect_trajectory_match(self) -> None:
        traj = {"steps": [{"action": "search", "tool": "web"}], "final_state": {"done": True}}
        evaluator = TrajectoryEvaluator()
        result = await evaluator.evaluate("q", _json(traj), _json(traj))
        assert result.is_ok()
        assert result.unwrap().score == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_no_steps_match_returns_zero(self) -> None:
        output = {"steps": [{"action": "read"}], "final_state": {}}
        reference = {"steps": [{"action": "write"}], "final_state": {}}
        evaluator = TrajectoryEvaluator()
        result = await evaluator.evaluate("q", _json(output), _json(reference))
        assert result.is_ok()
        assert result.unwrap().score < 1.0

    @pytest.mark.asyncio
    async def test_partial_steps_match(self) -> None:
        output = {"steps": [{"action": "a"}, {"action": "b"}], "final_state": {}}
        reference = {"steps": [{"action": "a"}, {"action": "c"}], "final_state": {}}
        evaluator = TrajectoryEvaluator()
        result = await evaluator.evaluate("q", _json(output), _json(reference))
        assert result.is_ok()
        er = result.unwrap()
        assert 0.0 < er.score < 1.0

    @pytest.mark.asyncio
    async def test_final_state_mismatch_reduces_score(self) -> None:
        traj = {"steps": [], "final_state": {"status": "done"}}
        wrong = {"steps": [], "final_state": {"status": "pending"}}
        evaluator = TrajectoryEvaluator()
        result = await evaluator.evaluate("q", _json(wrong), _json(traj))
        assert result.is_ok()
        assert result.unwrap().score < 1.0

    @pytest.mark.asyncio
    async def test_empty_reference_steps_with_no_output_scores_half(self) -> None:
        # steps_score=0.0 (no ref steps, no output steps), final_state_score=1.0 (no ref state) → avg=0.5
        output = {"steps": [], "final_state": {}}
        reference = {"steps": [], "final_state": {}}
        evaluator = TrajectoryEvaluator()
        result = await evaluator.evaluate("q", _json(output), _json(reference))
        assert result.is_ok()
        er = result.unwrap()
        assert er.score == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_details_contain_step_counts(self) -> None:
        output = {"steps": [{"action": "x"}, {"action": "y"}], "final_state": {}}
        reference = {"steps": [{"action": "x"}], "final_state": {}}
        evaluator = TrajectoryEvaluator()
        result = await evaluator.evaluate("q", _json(output), _json(reference))
        assert result.is_ok()
        details = result.unwrap().metrics
        assert details["output_steps"] == 2
        assert details["reference_steps"] == 1

    def test_step_matches_action_and_tool(self) -> None:
        evaluator = TrajectoryEvaluator()
        assert evaluator._step_matches(
            {"action": "call", "tool": "api"},
            {"action": "call", "tool": "api"},
        )
        assert not evaluator._step_matches(
            {"action": "call", "tool": "db"},
            {"action": "call", "tool": "api"},
        )

    def test_evaluate_steps_empty_reference_with_output_returns_one(self) -> None:
        evaluator = TrajectoryEvaluator()
        assert evaluator._evaluate_steps([{"action": "x"}], []) == 1.0

    def test_evaluate_final_state_empty_reference(self) -> None:
        evaluator = TrajectoryEvaluator()
        assert evaluator._evaluate_final_state({"k": "v"}, {}) == 1.0
