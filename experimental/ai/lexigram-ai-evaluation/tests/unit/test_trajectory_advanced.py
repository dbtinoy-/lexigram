"""Advanced tests for TrajectoryEvaluator."""

from __future__ import annotations

import json

import pytest

from lexigram.ai.evaluation.evaluators.trajectory import TrajectoryEvaluator


class TestTrajectoryEvaluatorAdvanced:
    """Advanced tests for TrajectoryEvaluator."""

    @pytest.fixture
    def evaluator(self) -> TrajectoryEvaluator:
        return TrajectoryEvaluator()

    @pytest.mark.asyncio
    async def test_perfect_trajectory_match(self, evaluator: TrajectoryEvaluator) -> None:
        output = json.dumps({
            "steps": [{"action": "search", "tool": "web"}],
            "final_state": {"status": "complete"},
        })
        reference = json.dumps({
            "steps": [{"action": "search", "tool": "web"}],
            "final_state": {"status": "complete"},
        })
        result = await evaluator.evaluate("query", output, reference)
        assert result.is_ok()
        assert result.unwrap().score == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_no_match_trajectory(self, evaluator: TrajectoryEvaluator) -> None:
        output = json.dumps({
            "steps": [{"action": "search"}],
            "final_state": {"status": "error"},
        })
        reference = json.dumps({
            "steps": [{"action": "calculate"}],
            "final_state": {"status": "complete"},
        })
        result = await evaluator.evaluate("query", output, reference)
        assert result.is_ok()
        assert result.unwrap().score < 1.0

    @pytest.mark.asyncio
    async def test_invalid_json_output(self, evaluator: TrajectoryEvaluator) -> None:
        result = await evaluator.evaluate("query", "not json", '{"steps": []}')
        assert result.is_ok()
        assert result.unwrap().score == 0.0
        assert "invalid_json" in result.unwrap().metrics.get("error", "")

    @pytest.mark.asyncio
    async def test_invalid_json_reference(self, evaluator: TrajectoryEvaluator) -> None:
        result = await evaluator.evaluate("query", '{"steps": []}', "not json")
        assert result.is_ok()
        assert result.unwrap().score == 0.0

    @pytest.mark.asyncio
    async def test_empty_steps(self, evaluator: TrajectoryEvaluator) -> None:
        output = json.dumps({"steps": [], "final_state": {}})
        reference = json.dumps({"steps": [], "final_state": {}})
        result = await evaluator.evaluate("query", output, reference)
        assert result.is_ok()
        assert result.unwrap().score == 0.5

    @pytest.mark.asyncio
    async def test_empty_reference_steps_with_output(self, evaluator: TrajectoryEvaluator) -> None:
        output = json.dumps({"steps": [{"action": "search"}], "final_state": {}})
        reference = json.dumps({"steps": [], "final_state": {}})
        result = await evaluator.evaluate("query", output, reference)
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_empty_reference_final_state(self, evaluator: TrajectoryEvaluator) -> None:
        output = json.dumps({"steps": [], "final_state": {"key": "val"}})
        reference = json.dumps({"steps": [], "final_state": {}})
        result = await evaluator.evaluate("query", output, reference)
        assert result.unwrap().score == 0.5

    @pytest.mark.asyncio
    async def test_partial_step_match(self, evaluator: TrajectoryEvaluator) -> None:
        output = json.dumps({
            "steps": [{"action": "search"}, {"action": "calculate"}],
            "final_state": {},
        })
        reference = json.dumps({
            "steps": [{"action": "search"}, {"action": "summarize"}],
            "final_state": {},
        })
        result = await evaluator.evaluate("query", output, reference)
        assert result.unwrap().score == 0.75

    def test_name_property(self, evaluator: TrajectoryEvaluator) -> None:
        assert evaluator.name == "trajectory"
